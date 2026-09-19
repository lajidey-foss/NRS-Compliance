# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

import json
import re
from typing import Any

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

from nrs_compliance.nrs_compliance.app import (
    EComplianceError,
    EComplianceValidationError,
    _TRANSIENT_NRS_MARKERS,
    _base_url,
    _build_postal_address,
    _build_tax_subtotals,
    _get_settings,
    _headers,
)

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
_REQUEST_TIMEOUT = 15  # seconds
_RETRY_COUNT = 2
_RETRY_DELAY = 2  # seconds
_MAX_RETRIES = 3
_TIMEOUT_SHORT = 30
_TIMEOUT_LONG = 60


# ─ IRN
# Get service ID from session company [from sales invoice]

def generate_irn(invoice_name: str, settings=None) -> str:
    """
    Include company in attribute.
    FIRS IRN template: {InvoiceNumber}-{ServiceID}-{YYYYMMDD}

    Note:
      InvoiceNumber — alphanumeric only (stripped of hyphens and slashes)

    Example: INV251200001-15KJ72IS-20251227
    """
    if settings is None:
        settings = _get_settings()

    service_id = (settings.get("nrs_service_id") or "").strip()
    if not service_id:
        frappe.throw(
            _(
                "NRS Service ID is not configured in Nigeria Compliance Settings. "
                "Set the 8-character Service ID from your NRS dashboard."
            )
        )

    # Strip all non-alphanumeric characters — NRS rejects hyphens, slashes, spaces.
    invoice_number = re.sub(r"[^A-Za-z0-9]", "", invoice_name)
    posting_date = frappe.db.get_value("Sales Invoice", invoice_name, "posting_date")
    date_str = (
        str(posting_date).replace("-", "")
        if posting_date
        else now_datetime().strftime("%Y%m%d")
    )
    return f"{invoice_number}-{service_id}-{date_str}"


# ─ eInvoice schema payload builder

def build_invoice_payload(sales_invoice: str, irn: str) -> dict[str, Any]:
    """
    Build UBL BIS Billing 3.0 JSON payload for POST => /validate
    and POST=> /sign
    """
    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    settings = _get_settings(doc.company)
    from nrs_compliance.utils.resources import get_quantity_code

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
                billing_reference = [{"nrs_irn": original_irn, "issue_date": str(original_date)}]

    # ─ Invoice type
    # !TODO: Move this into a helper that resolves the correct invoice type code.
    invoice_type_code = "381"

    # ─ Addresses
    company_fields = frappe.db.get_value(
        "Company",
        doc.company,
        [
            "nrs_address",
            "nrs_city",
            "nrs_postal_code",
            "nrs_state",
            "nrs_lga",
            "nrs_email",
            "nrs_phone_number",
            "nrs_business_description",
        ],
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
        "Customer", doc.customer, ["nrs_state", "nrs_lga"], as_dict=True
    ) or {}

    # Resolve the linked Address document to get the actual street text.
    customer_address_name = doc.get("customer_address") or ""
    addr_street, addr_city, addr_postal = "", "", ""
    if customer_address_name:
        addr = frappe.db.get_value(
            "Address",
            customer_address_name,
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

    # ─ Tax — read actual ERPNext tax lines, fall back to settings default.
    vat_rate = float(settings.get("einvoice_default_vat_rate") or 7.5)
    tax_subtotals, total_vat = _build_tax_subtotals(doc, vat_rate)

    # ─ Payment means
    # TODO: Build this from a helper instead of a hard-coded default.
    payment_means_code = "97" # Others / unknown payment mode (code)
    due_date = str(doc.due_date) if doc.get("due_date") else str(doc.posting_date)

    # ─ Line items
    invoice_lines = []
    total_line_extension = 0.0

    # Batch-fetch all item NRS fields to avoid N+1 queries.
    item_codes = [row.item_code for row in doc.items]
    item_fields_map: dict[str, dict] = {}
    if item_codes:
        for item_row in frappe.get_all(
            "Item",
            filters={"name": ("in", item_codes)},
            fields=["name", "nrs_hs_code", "nrs_service_code"],
        ):
            item_fields_map[item_row.name] = item_row

    for row in doc.items:
        net = float(row.net_amount)
        total_line_extension += net

        item_f = item_fields_map.get(row.item_code, {})
        hs_code = (item_f.get("nrs_hs_code") or "").strip()
        service_code = (item_f.get("nrs_service_code") or "").strip()

        quantity_code = get_quantity_code(row.uom or "" )

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

        if hs_code:
            line["hsn_code"] = hs_code
            line["product_category"] = (
                frappe.db.get_value("NRS HS Code", hs_code, "description")
                or row.item_group
                or "General"
            )
        elif service_code:
            line["isic_code"] = service_code
            line["service_category"] = (
                frappe.db.get_value("NRS Service Code", service_code, "description")
                or row.item_group
                or "General"
            )
        else:
            line["hsn_code"] = ""
            line["product_category"] = row.item_group or "General"

        invoice_lines.append(line)

    tax_exclusive = round(float(doc.net_total), 2)
    tax_inclusive = round(float(doc.grand_total), 2)
    payable_amount = round(float(doc.outstanding_amount or doc.grand_total), 2)

    # ─ Allowance / charge (invoice-level discount)
    allowance_charges = []
    if float(doc.get("additional_discount_amount") or 0) > 0:
        allowance_charges.append(
            {
                "charge_indicator": False,
                "amount": round(float(doc.additional_discount_amount), 2),
            }
        )

    # !TODO"integrator_service_id": settings.get("einvoice_integrator_service_id") or "00000",
    payload: dict[str, Any] = {
        # ─ Invoice header
        "business_id": business_id,
        "irn": irn,
        "issue_date": str(doc.posting_date),
        "due_date": due_date,
        "issue_time": now_datetime().strftime("%H:%M:%S"),
        "invoice_type_code": invoice_type_code,
        "invoice_kind": invoice_kind,
        "integrator_service_id": "00000",
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

def validate_irn(
    irn: str, invoice_reference: str, business_id: str, company_name: str | None = None
) -> dict[str, Any]:
    """Validate the generated IRN is unique and correctly formatted before submission."""
    settings = _get_settings(company_name)
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


# ─ Submission

def submit_invoice_enqueued(sales_invoice: str) -> dict:
    """Queue the submission for background processing."""
    
    company_name = frappe.db.get_value("Sales Invoice", sales_invoice, "company")
    settings = _get_settings(company_name)
    if not settings.get("nrs_einvoice_enabled"):
        return {}

    frappe.enqueue(
        "nrs_compliance.utils.nrs_einvoice.submit_invoice",
        queue="long",
        timeout=180,
        enqueue_after_commit=True,
        sales_invoice=sales_invoice,
    )
    return {"queued": True}


def submit_invoice(sales_invoice: str) -> dict[str, Any]:
    """
    Submission process:
      1. Generate IRN
      2. Validate schema against NRS
      3. Submit valid payload and sign invoice
    """
    company_name = frappe.db.get_value("Sales Invoice", sales_invoice, "company")
    settings = _get_settings(company_name)

    if not settings.get("nrs_einvoice_enabled"):
        return {}

    einvoice_doc = _get_or_create_einvoice(sales_invoice)
    if einvoice_doc.status == "Cleared":
        return {}

    max_retries = einvoice_doc.max_retries or _MAX_RETRIES
    if (einvoice_doc.retry_count or 0) >= max_retries:
        _update_einvoice(
            einvoice_doc,
            {},
            {},
            "Failed",
            f"Automatic retries exhausted ({max_retries}). Needs manual review — "
            "use the Nigeria → Submit to NRS button to retry.",
            irn=einvoice_doc.irn,
        )
        frappe.log_error(
            f"Max retries reached for Sales Invoice {sales_invoice}",
            "NRS e-Invoice",
        )
        return {}

    actual_buyer_tin = frappe.db.get_value(
        "Customer",
        frappe.db.get_value("Sales Invoice", sales_invoice, "customer"),
        "nrs_tin",
    ) or ""

    if settings.get("einvoice_b2b_only") and not actual_buyer_tin:
        return {}

    try:
        irn = einvoice_doc.irn or generate_irn(sales_invoice, settings)
        payload = build_invoice_payload(sales_invoice, irn)

        # Step 1: validate
        validate_resp = requests.post(
            f"{_base_url(settings)}{_VALIDATE_INVOICE_DATA}",
            json=payload,
            headers=_headers(settings),
            timeout=_TIMEOUT_LONG,
        )

        if validate_resp.status_code in (400, 422):
            if _is_transient_nrs_error(validate_resp.text):
                _update_einvoice(
                    einvoice_doc,
                    payload,
                    {},
                    "Auto-Retry",
                    f"NRS temporarily unavailable (validate), will retry: {validate_resp.text}",
                    irn=irn,
                )
                _flag_retry_pending(company_name)
                return {}
            _update_einvoice(
                einvoice_doc,
                payload,
                {},
                "Failed",
                f"Validation error: {validate_resp.text}",
                irn=irn,
            )
            raise EComplianceValidationError(
                f"NRS validation error [{validate_resp.status_code}]: {validate_resp.text}"
            )

        if not validate_resp.ok:
            _update_einvoice(
                einvoice_doc,
                payload,
                {},
                "Auto-Retry",
                f"Validate step error: {validate_resp.text}",
                irn=irn,
            )
            _flag_retry_pending(company_name)
            return {}

        # Step 2: sign
        sign_resp = requests.post(
            f"{_base_url(settings)}{_SIGN_INVOICE_SCHEMA}",
            json=payload,
            headers=_headers(settings),
            timeout=_TIMEOUT_LONG,
        )

        if sign_resp.status_code in (400, 422):
            if _is_transient_nrs_error(sign_resp.text):
                _update_einvoice(
                    einvoice_doc,
                    payload,
                    {},
                    "Auto-Retry",
                    f"NRS temporarily unavailable (sign), will retry: {sign_resp.text}",
                    irn=irn,
                )
                _flag_retry_pending(company_name)
                return {}
            _update_einvoice(
                einvoice_doc,
                payload,
                {},
                "Failed",
                f"Sign error: {sign_resp.text}",
                irn=irn,
            )
            raise EComplianceValidationError(
                f"NRS sign error [{sign_resp.status_code}]: {sign_resp.text}"
            )

        if not sign_resp.ok:
            _update_einvoice(
                einvoice_doc,
                payload,
                {},
                "Auto-Retry",
                f"Sign step error: {sign_resp.text}",
                irn=irn,
            )
            _flag_retry_pending(company_name)
            return {}

        result = sign_resp.json() if sign_resp.content else {}
        csid = result.get("csid") or result.get("CSID") or ""

        qr_data = (
            result.get("qrCode")
            or result.get("QRCode")
            or result.get("qr_code")
            or ""
        )
        if not qr_data:
            from nrs_compliance.nrs_compliance.controllers.api import generate_invoice_qr_data

            qr_data = generate_invoice_qr_data(irn, settings)

        _update_einvoice(
            einvoice_doc,
            payload,
            result,
            "Submitted",
            "",
            irn=irn,
            csid=csid,
            qr_data=qr_data,
        )

        frappe.db.set_value(
            "Sales Invoice",
            sales_invoice,
            {
                "nrs_irn": irn,
                "nrs_csid": csid,
                "nrs_status": "Submitted",
                "nrs_encrypted_qrcode" : qr_data,
            },
        )
        return result

    except (EComplianceValidationError, EComplianceError):
        raise
    except Exception as e:
        _update_einvoice(einvoice_doc, {}, {}, "Auto-Retry", str(e))
        _flag_retry_pending(company_name)
        frappe.log_error(frappe.get_traceback(), "NRS e-Invoice Submission")


def _get_or_create_einvoice(sales_invoice: str):
    name = frappe.db.get_value("NRS EInvoice", {"sales_invoice": sales_invoice}, "name")
    if name:
        return frappe.get_doc("NRS EInvoice", name)

    inv = frappe.get_doc("Sales Invoice", sales_invoice)
    customer_kind = frappe.db.get_value("Customer", inv.customer, "nrs_invoice_kind") or ""
    buyer_tin = frappe.db.get_value("Customer", inv.customer, "nrs_tin") or ""

    if customer_kind in ("B2B", "B2C", "B2G"):
        invoice_kind = customer_kind
    elif buyer_tin:
        invoice_kind = "B2B"
    else:
        invoice_kind = "B2C"

    doc = frappe.new_doc("NRS EInvoice")
    doc.sales_invoice = sales_invoice
    doc.status = "Pending"
    doc.invoice_type = invoice_kind
    doc.invoice_code = sales_invoice
    doc.invoice_date = inv.posting_date
    doc.seller_tin = frappe.db.get_value("Company", inv.company, "nrs_tin") or ""
    doc.buyer_tin = frappe.db.get_value("Customer", inv.customer, "nrs_tin") or ""
    doc.total_excluding_vat = inv.net_total
    doc.grand_total = inv.grand_total
    doc.max_retries = _MAX_RETRIES
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def _update_einvoice(
    doc,
    payload: dict,
    response: dict,
    status: str,
    error: str,
    irn: str = "",
    csid: str = "",
    qr_data: str = "",
):
    doc.status = status
    if irn:
        doc.irn = irn
    if csid:
        doc.csid = csid
    doc.payload_schema = json.dumps(payload, indent=2, default=str)
    doc.api_response = json.dumps(response, indent=2, default=str)
    doc.error_message = error

    if status in ("Failed", "Auto-Retry"):
        doc.retry_count = (doc.retry_count or 0) + 1
        doc.last_retry_at = now_datetime()

    if status == "Submitted":
        doc.submitted_at = now_datetime()
        # Read computed VAT from the payload we sent — NRS sign response does not echo this back
        try:
            doc.vat_amount = (
                payload.get("tax_total", [{}])[0].get("tax_amount")
                or response.get("totalVAT")
                or response.get("total_vat")
                or 0
            )
        except (IndexError, TypeError):
            doc.vat_amount = 0

    if status == "Cleared":
        doc.cleared_at = now_datetime()

    if qr_data:
        _attach_qr_code(doc, qr_data)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

def _is_transient_nrs_error(text: str) -> bool:
    """Return True when the NRS 400/422 response is a transient retry condition."""
    t = (text or "").lower()
    return any(marker in t for marker in _TRANSIENT_NRS_MARKERS)


def _flag_retry_pending(company_name: str | None = None):
    # Do not commit here — caller is responsible for transaction boundaries

    # move it to company level
    settings = _get_settings(company_name)
    
    frappe.db.set_value("Company", settings.get("name"), "is_retry_einvoice_pending", 1)

# - Move block to app.py
def _attach_qr_code(einvoice_doc, qr_data: str):
    """Generate a QR code PNG from qr_data and attach it to the e-invoice."""
    try:
        import base64
        import io

        import qrcode

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=12,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"QC_{einvoice_doc.name}.png",
            "content": base64.b64encode(buf.read()).decode(),
            "decode": True,
            "is_private": 0,
            "attached_to_doctype": "NRS EInvoice",
            "attached_to_name": einvoice_doc.name,
            "attached_to_field": "encrypted_qr_code",
        })
        file_doc.insert(ignore_permissions=True)
        einvoice_doc.encrypted_qr_code = file_doc.file_url
    except ImportError:
        # qrcode missing — cannot render barcode; log and leave qr_code empty
        frappe.log_error(
            "qrcode package not installed — invoice will have no NRS barcode. Run: pip install qrcode",
            "NRS QR Code Generation",
        )
        einvoice_doc.qr_code = ""
    except Exception as e:
        frappe.log_error(str(e), "NRS QR Code Generation")
        einvoice_doc.qr_code = ""


