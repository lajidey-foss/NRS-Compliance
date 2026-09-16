# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re

_HS_CODE_RE = re.compile(r"^\d{4}\.\d{2}$")

def fields_compliances(doc, method=None):
    """enforce nrs compliance on validateion """
    nrs_confirmed = {"Submitted", "Cleared", "Cancelled"}
    if doc.get("nrs_status") in nrs_confirmed:
        return

    if doc.get("nrs_skip_einvoice"):
        doc.nrs_skip_einvoice = "Not Required"
        return

    buyer_tin = frappe.db.get_value("Customer", doc.customer, "nrs_tin") or ""
    settings = _get_settings_if_enabled(doc.company)

    if not settings:
        doc.nrs_status = "Not Required"
        return
    if not buyer_tin:
        doc.nrs_status = "Not Required"
    else:
        doc.nrs_status = "Pending"

def nrs_submit_compliance(doc, method=None):
    """
    Validate nrs payload for a comprehensive list of missing and faulty fields that causes rejection
    """
    if doc.get("nrs_skip_einvoice") or doc.get("nrs_status") == "Not Required":
        return

    settings = _get_settings_if_enabled(doc.company)
    if not settings or not settings.get("nrs_einvoice_enabled"):
        return

    _validate_nrs_readiness(doc, settings)

def _get_settings_if_enabled(company):
    from nrs_compliance.nrs_compliance.app import _get_settings
    try:
        settings = _get_settings(company)
        return settings if settings.get("nrs_einvoice_enabled") else None
    except Exception:
        return None

def _validate_nrs_readiness(doc, settings):
    """
    get all required field issues and raise a single, actionable error before it filter throught to nrs server

    """
    issues = []

    # - Seller [ie owner of the system]
    company = frappe.db.get_value(
        "Company", doc.company,
        ["nrs_tin", "nrs_email", "nrs_phone_number", "nrs_business_information"], as_dict=True,
    ) or frappe._dict()
    tin = (company.nrs_tin or "").strip()
    if not tin:
        issues.append(_("Company TIN (Company → NRS Details Tab, or Compliance Settings)"))
    elif not tin.replace("-", "").isdigit():
        issues.append(_("Company TIN must be numeric (got '{0}')").format(tin))
    if not (company.nrs_email or "").strip():
        issues.append(_("Company Email"))
    if not (company.nrs_phone_number or "").strip().startswith("+"):
        issues.append(_("Company Phone — must start with + and country code (e.g. +234…)"))
    if len((company.nrs_business_information or "").strip()) < 5:
        issues.append(_("Company Description — at least 5 characters"))

    # ─ Buyer (Customer) — required for B2B (buyer has a TIN) 
    cust = frappe.db.get_value(
        "Customer", doc.customer, ["email_id", "mobile_no", "nrs_tin"], as_dict=True,
    ) or frappe._dict()
    """ if cust.nrs_tin:
        if not (cust.email_id or "").strip():
            issues.append(_("Customer Email"))
        if not (cust.mobile_no or "").strip().startswith("+"):
            issues.append(_("Customer Mobile — must start with + (set via the customer's primary Contact)")) """
    if cust.nrs_tin and not (cust.email_id or "").strip():
        issues.append(_("Customer Email"))

    if cust.nrs_tin and not (cust.mobile_no or "").strip().startswith("+"):
        issues.append(
        _("Customer Mobile — must start with + "
          "(set via the customer's primary Contact)")
    )

    # ─ Items 
    for row in doc.items:
        codes = frappe.db.get_value(
            "Item", row.item_code, ["nrs_hs_code", "nrs_service_code"], as_dict=True,
        ) or frappe._dict()
        hs = (codes.nrs_hs_code or "").strip()
        svc = (codes.nrs_service_code or "").strip()
        # Each line is classified as a GOOD (HS code → hsn_code) or a SERVICE
        # (ISIC code → isic_code). Exactly one is required.
        if not hs and not svc:
            issues.append(_("Item {0}: set an NRS HS Code (for goods) or ISIC Service Code "
                            "(for services).").format(row.item_code))
        elif hs and svc:
            issues.append(_("Item {0}: set EITHER an HS Code (goods) OR a Service Code "
                            "(services), not both.").format(row.item_code))
        elif hs and not _HS_CODE_RE.match(hs):
            issues.append(_("Item {0}: HS Code must be in 0000.00 format (got '{1}')").format(row.item_code, hs))

    if issues:
        frappe.throw(
            _("This invoice cannot be sent to NRS — please complete the following:")
            + "<ul>" + "".join(f"<li>{i}</li>" for i in issues) + "</ul>"
            + _("(Or tick 'Skip NRS e-Invoice' on this invoice to opt out.)"),
            title=_("NRS eInvoice — Missing Information"),
        )

def on_sales_invoice_submit(doc, method=None):
    """
    Enqueue submission when a Sales Invoice is submitted.
    """
    
    settings = _get_settings_if_enabled(doc.company)
    if not settings or not settings.get("nrs_einvoice_enabled") or not settings.get("nrs_einvoice_auto_submit"):
        return

    from nrs_compliance.utils.nrs_einvoice import submit_invoice_enqueued
    
    submit_invoice_enqueued(doc.name)

