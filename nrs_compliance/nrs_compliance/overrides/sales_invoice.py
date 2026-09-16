# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class NrsSalesInvoiceMixin:
    @frappe.whitelist()
    def generate_einvoice(self) -> dict:
        """
        case where do not create einvoice was set
        Admin or Audit manually need to create it
        """
        from nrs_compliance.utils.nrs_einvoice import submit_invoice_enqueued

        if self.docstatus !=1:
            frappe.throw(_("Only submitted sales Invoices can be sent for sign on NRS"))

        existing = frappe.db.get_value(
            "NRS EInvoice", {"sales_invoice": self.name}, ["name", "status"], as_dict=True
        )
        if existing and existing.status in ("Submitted", "Cleared"):
            frappe.throw(
                _("This invoice already has an eInvoice with status: {0}").format(existing.status)
            )
        return submit_invoice_enqueued(self.name)

class NrsSalesInvoice(NrsSalesInvoiceMixin, SalesInvoice):
    pass

