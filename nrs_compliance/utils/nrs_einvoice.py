# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date, nowdate
from nrs_compliance.nrs_compliance.app import _get_settings

# ─ IRN
#. get serivice id from session company [from sales invoice]

def generate_irn(invoice_name: str, settings=None) -> str:
    """
    include company in attribute
    FIRS IRN template: {InvoiceNumber}-{ServiceID}-{YYYYMMDD}

    Note:
      InvoiceNumber — alphanumeric only (stripped all hyphens and slashes)

    Example: INV251200001-15KJ72IS-20251227
    """
    if settings is None:
        settings = _get_settings()

    service_id = (settings.nrs_service_id or "").strip()
    if not service_id:
        frappe.throw(_("NRS Service ID is not configured in Nigeria Compliance Settings. "
                       "Set the 8-character Service ID from your NRS dashboard."))

    # Strip all non-alphanumeric characters — NRS rejects hyphens, slashes, spaces
    import re
    invoice_number = re.sub(r"[^A-Za-z0-9]", "", invoice_name)
    # Use the invoice's posting date — not today — so backdated invoices have matching IRNs
    posting_date = frappe.db.get_value("Sales Invoice", invoice_name, "posting_date")
    date_str = str(posting_date).replace("-", "") if posting_date else now_datetime().strftime("%Y%m%d")
    return f"{invoice_number}-{service_id}-{date_str}"