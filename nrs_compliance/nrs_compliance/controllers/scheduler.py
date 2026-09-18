# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, now_datetime
from nrs_compliance.nrs_compliance.app import _get_settings

def retry_unflag_einvoices():
    """
    retry every 5 minutes
    """

    try:
        #settings = frappe.get_cached_doc("NRS Compliance Settings")
        settings = _get_settings()
    except Exception:
        return

    if not settings.get("nrs_einvoice_enabled") or not settings.get("is_retry_einvoice_pending"):
        return

    frappe.db.set_value("Company",settings.get("company"),"is_retry_einvoice_pending", 0, update_modified=False)

    pending = frappe.get_all(
        "NRS EInvoice",
        filters={
            "status": "Auto-Retry",
            "creation": [">=", add_days(now_datetime(), -3)],
        },
        fields=["name", "sales_invoice", "retry_count", "max_retries"],
    )

    for record in pending:
        max_r = record.max_retries or 3
        if (record.retry_count or 0) >= max_r:
            frappe.db.set_value("NRS EInvoice", record.name, "status", "Failed")
            frappe.db.set_value("Sales Invoice", record.sales_invoice, "nrs_status", "Failed")

            frappe.db.commit()
            # check for escalate
            _notify_einvoice_failed(record.sales_invoice)
            continue

        # put in consideration for slow network as nrs server will be slow
        frappe.enqueue(
            "nrs_compliance.utils.nrs_einvoice.submit_invoice",
            queue="default",
            timeout=180,
            job_name=f"einvoice_retry_{record.name}",
            now=False,
            sales_invoice=record.sales_invoice,
        )


def _notify_einvoice_failed(sales_invoice: str):
    """Create a system notification when an einvoice permanently fails."""
    try:
        accounts_managers = frappe.get_all(
            "Has Role",
            filters={"role": "Accounts Manager", "parenttype": "User"},
            pluck="parent",
            ignore_permissions=True,
        )
        if not accounts_managers:
            accounts_managers = ["Administrator"]

        subject = _("NRS Invoice Signing Failed: {0}").format(sales_invoice)
        body = _(
            "The NRS e-invoice for Sales Invoice {0} has permanently failed after maximum "
            "retries. Please open the Nigeria E-Invoice record and resolve manually."
        ).format(sales_invoice)

        for user in accounts_managers[:5]:  # cap at 5 recipients
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": subject,
                "email_content": body,
                "for_user": user,
                "type": "Alert",
                "document_type": "Sales Invoice",
                "document_name": sales_invoice,
            }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "NRS EInvoice Failure Notification")
