# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date, nowdate
from typing import Any
from nrs_compliance.nrs_compliance.app import EComplianceError, _get_settings,_build_postal_address,_build_tax_subtotals, _base_url, _headers
import requests

_VALIDATE_IRN = "/api/v1/invoice/irn/validate"
_VALIDATE_INVOICE_DATA = "/api/v1/invoice/validate"
_SIGN_INVOICE_SCHEMA = "/api/v1/invoice/sign"
_AUTH_PATH = "/api/v1/utilities/authenticate"
_UPDATE_EINVOICE = "/api/v1/invoice/update"
_DOWNLOAD_INVOICE = "/api/v1/invoice/download"
_CONFIRM_INVOICE = "/api/v1/invoice/confirm"
_SEARCH_INVOICE = "/api/v1/invoice"
_LOOKUP_INVOICE = "/api/v1/invoice/transmit/lookup"
_TRANSMIT_INVOICE = "/api/v1/invoice/transmit"
_REQUEST_TIMEOUT = 15 # seconds 
_RETRY_COUNT = 2 
_RETRY_DELAY = 2 # seconds
_MAX_RETRIES = 3
_TIMEOUT_SHORT = 30
_TIMEOUT_LONG = 60

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

# ─ eInvoice schema payload builder 

def build_invoice_payload(sales_invoice: str, irn: str) -> dict[str, Any]:
    """
    Build UBL BIS Billing 3.0 JSON payload for POST => /validate
    and POST=> /sign
    """
    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    settings = _get_settings(doc.company)

    # _payment_code

    # ─ Business IDs
    business_id = (
        settings.get("nrs_business_id")
        or ""
    )
    seller_tin = (
        settings.get("nrs_tin")
        or ""
    )
    buyer_tin = frappe.db.get_value("Customer", doc.customer, "nrs_tin") or ""
    if not buyer_tin:
        rc_number = frappe.db.get_value("Customer", doc.customer, "nrs_rc_number") or ""
        if rc_number:
            buyer_tin = f"RN-{rc_number}"


    # ─ Invoice kind (B2C / B2B / B2G)
    #  is TIN not null.
    customer_kind = frappe.db.get_value("Customer", doc.customer, "nrs_invoice_kind") or ""
    if customer_kind in ("B2B", "B2C", "B2G"):
        invoice_kind = customer_kind
    elif buyer_tin:
        invoice_kind = "B2B"
    else:
        invoice_kind = "B2C"

    # ─ Billing reference (credit notes / debit notes)
    # Link back to the original invoice's IRN so NRS can reverse its VAT entry.
    is_return = bool(doc.get("is_return"))
    is_debit_note = bool(doc.get("is_debit_note"))
    billing_reference = None
    if is_return or is_debit_note:
        original_invoice = doc.get("return_against") or doc.get("amended_from") or ""
        if original_invoice:
            original_irn, original_date = frappe.db.get_value(
                "Sales Invoice", original_invoice, ["nrs_irn", "posting_date"]
            ) or ("", "")
            if original_irn:
                billing_reference = [{"irn": original_irn, "issue_date": str(original_date)}]


    # ─ Invoice type
    #. !ISSUE: function to return invoice type code default to 381
    invoice_type_code = "381"

    # ─ Addresses 
    company_fields = frappe.db.get_value(
        "Company", doc.company,
        ["nrs_address", "nrs_city", "nrs_postal_code", "nrs_state", "nrs_lga",
         "nrs_email", "nrs_phone_number", "nrs_business_description"],
        as_dict=True,
    ) or {}

    seller_address = _build_postal_address(
        company_fields.get("nrs_address") or "",
        company_fields.get("nrs_city") or "",
        company_fields.get("nrs_postal_code") or "",
        "NG",
        state=company_fields.get("nrs_state") or "",
        lga=company_fields.get("nrs_lga") or "",
    )
    customer_fields = frappe.db.get_value(
        "Customer", doc.customer,
        ["nrs_state", "nrs_lga"],
        as_dict=True,
    ) or {}

    # Resolve the linked Address document to get the actual street text
    customer_address_name = doc.get("customer_address") or ""
    addr_street, addr_city, addr_postal = "", "", ""
    if customer_address_name:
        addr = frappe.db.get_value(
            "Address", customer_address_name,
            ["address_line1", "city", "pincode"],
            as_dict=True,
        ) or {}
        addr_street = addr.get("address_line1") or ""
        addr_city = addr.get("city") or ""
        addr_postal = addr.get("pincode") or ""


    buyer_address = _build_postal_address(
        addr_street,
        addr_city,
        addr_postal,
        "NG",
        state=customer_fields.get("nrs_state") or "",
        lga=customer_fields.get("nrs_lga") or "",
    )

    # ─ Tax — read actual ERPNext tax lines, fall back to settings default 
    vat_rate = float(settings.einvoice_default_vat_rate or 7.5)
    tax_subtotals, total_vat = _build_tax_subtotals(doc, vat_rate)

    # ─ Payment means 
    #. !ISSUE: function to return payment means code or get default from settings
    payment_means_code = "97" #functon to get payment means
    due_date = str(doc.due_date) if doc.get("due_date") else str(doc.posting_date)

    # ─ Line items 
    invoice_lines = []
    total_line_extension = 0.0

    # Batch-fetch all item NRS fields to avoid N+1 queries
    item_codes = [row.item_code for row in doc.items]
    item_fields_map: dict[str, dict] = {}
    if item_codes:
        for item_row in frappe.get_all(
            "Item", filters={"name": ("in", item_codes)},
            fields=["name", "nrs_hs_code", "nrs_service_code"],
        ):
            item_fields_map[item_row.name] = item_row

    for row in doc.items:
        net = float(row.net_amount)
        total_line_extension += net

        item_f = item_fields_map.get(row.item_code, {})
        hs_code = (item_f.get("nrs_hs_code") or "").strip()
        service_code = (item_f.get("nrs_service_code") or "").strip()

        # NRS UOM [qty code]
        #. !ISSUE: function to return quantity code [uom] or set default EA 
        quantity_code = "EA" #function to get quantity code

        line = {
            "invoiced_quantity": float(row.qty),
            "line_extension_amount": net,
            "item": {
                "name": row.item_name or row.item_code,
                "description": row.description or row.item_name or "",
                "sellers_item_identification": row.item_code,
            },
            "price": {
                "price_amount": float(row.rate),
                "base_quantity": 1,
                "price_unit": quantity_code,
            },
        }

        # NRS line classification (per NRS Support): GOODS use hsn_code +
        # product_category; SERVICES use isic_code + service_category. The two
        # pairs are mutually exclusive on a line. The "category" is the code's
        # description. before_submit_ng guarantees one code is present.
        if hs_code:
            line["hsn_code"] = hs_code
            line["product_category"] = (
                frappe.db.get_value("NRS HS Code", hs_code, "description")
                or row.item_group or "General"
            )
        elif service_code:
            line["isic_code"] = service_code
            line["service_category"] = (
                frappe.db.get_value("NRS Service Code", service_code, "description")
                or row.item_group or "General"
            )
        else:
            # Unclassified — before_submit_ng should have blocked this; emit an
            # empty hsn_code so NRS returns a clear, actionable rejection.
            line["hsn_code"] = ""
            line["product_category"] = row.item_group or "General"

        invoice_lines.append(line)

    tax_exclusive = round(float(doc.net_total), 2)
    tax_inclusive = round(float(doc.grand_total), 2)
    payable_amount = round(float(doc.outstanding_amount or doc.grand_total), 2)

    # ─ Allowance / charge (invoice-level discount) 
    allowance_charges = []
    if float(doc.get("additional_discount_amount") or 0) > 0:
        allowance_charges.append({
            "charge_indicator": False,
            "amount": round(float(doc.additional_discount_amount), 2),
        })

    payload: dict[str, Any] = {
        # ─ Invoice header 
        "business_id": business_id,
        "irn": irn,
        "issue_date": str(doc.posting_date),
        "due_date": due_date,
        "issue_time": now_datetime().strftime("%H:%M:%S"),
        "invoice_type_code": invoice_type_code,
        "invoice_kind": invoice_kind,
        "integrator_service_id": settings.einvoice_integrator_service_id or "00000",
        "payment_status": "PENDING",
        "document_currency_code": doc.currency or "NGN",
        "tax_currency_code": "NGN",

        # ─ Buyer reference / order reference 
        **({"buyer_reference": doc.po_no} if doc.get("po_no") else {}),
        **({"order_reference": doc.po_no} if doc.get("po_no") else {}),

        # ─ Note (invoice remarks) 
        **({"note": doc.terms[:500]} if doc.get("terms") else {}),

        # ─ Billing reference (credit notes / debit notes) 
        **({"billing_reference": billing_reference} if billing_reference else {}),

        # ─ Supplier 
        "accounting_supplier_party": {
            "party_name": doc.company,
            "tin": seller_tin,
            "email": company_fields.get("nrs_email") or "",
            "telephone": company_fields.get("nrs_phone_number") or "",
            "business_description": company_fields.get("nrs_business_description") or "",
            "postal_address": seller_address,
        },

        # ─ Customer 
        # email_id, mobile_no
        "accounting_customer_party": {
            "party_name": doc.customer_name,
            "tin": buyer_tin,
            "email": frappe.db.get_value("Customer", doc.customer, "email_id") or "",
            "telephone": frappe.db.get_value("Customer", doc.customer, "mobile_no") or "",
            "postal_address": buyer_address,
        },

        # ─ Payment 
        "payment_means": [
            {
                "payment_means_code": payment_means_code,
                "payment_due_date": due_date,
            }
        ],
        "payment_terms_note": doc.payment_terms_template or "",

        # ─ Allowances (invoice-level discounts) 
        **({"allowance_charge": allowance_charges} if allowance_charges else {}),

        # ─ Tax 
        "tax_total": [
            {
                "tax_amount": total_vat,
                "tax_subtotal": tax_subtotals,
            }
        ],

        # ─ Totals 
        "legal_monetary_total": {
            "line_extension_amount": round(total_line_extension, 2),
            "tax_exclusive_amount": tax_exclusive,
            "tax_inclusive_amount": tax_inclusive,
            "payable_amount": payable_amount,
        },

        # ─ Lines 
        "invoice_line": invoice_lines,
    }
    return payload

# ─ IRN Save[Draft] NRS Validation

def validate_irn(irn: str, invoice_reference: str, business_id: str) -> dict[str, Any]:
    """
    POST=> /validate
    Validates that the generated IRN is unique and correctly formatted before submission.
    """
    settings = _get_settings()
    resp = requests.post(
        f"{_base_url(settings)}{_VALIDATE_IRN}",
        json={
            "invoice_reference": invoice_reference,
            "business_id": business_id,
            "irn": irn,
        },
        headers=_headers(settings),
        timeout=_TIMEOUT_SHORT,
    )
    if not resp.ok:
        raise EComplianceError(f"IRN validation failed [{resp.status_code}]: {resp.text}")
    return resp.json() if resp.content else {}