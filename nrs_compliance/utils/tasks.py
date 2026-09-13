# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """
    occurs after installing app
    """
    create_nrs_custom_fields()
    set_default_compliance_settings()
    frappe.db.commit()

def after_migrate():
    """ include function to remove obsolete custom fields """
    create_nrs_custom_fields()
    set_default_compliance_settings() # toggle on for developer testing
    frappe.db.commit()


def create_nrs_custom_fields():
    """ coming to you """
    custom_fields = _get_nrs_custom_fields()

    create_custom_fields(custom_fields, ignore_validate=True)

def _get_nrs_custom_fields():
    """
    return: company, customer, item, sales invoice, salesinvoice item, ...
    """
    return {
        "Company": [
            {
                "fieldname": "nrs_details_tab",
                "label": "NRS Details",
                "fieldtype": "Tab Break",
                "insert_after": "dashboard_tab",
            },
            {
                "fieldname": "nrs_information_section",
                "label": "NRS Business Information",
                "fieldtype": "Section Break",
                "insert_after": "nrs_details_tab",
            },
            {
                "bold": 1,
                "fieldname": "nrs_business_information",
                "fieldtype": "Data",
                "label": "NRS Business Information",
                "insert_after": "nrs_information_section",
            },
            {
                "fieldname": "nrs_phone_number",
                "fieldtype": "Data",
                "label": "Phone Number",
                "insert_after": "nrs_business_information",
            },
            {
                "fieldname": "nrs_col_break_i",
                "fieldtype": "Column Break",
                "insert_after": "nrs_phone_number",
            },
            {
                "bold": 1,
                "fieldname": "nrs_tin",
                "fieldtype": "Data",
                "label": "TIN (Tax Identificatio Number)",
                "insert_after": "nrs_col_break_i",
            },
            {
                "bold": 1,
                "fieldname": "nrs_email",
                "fieldtype": "Data",
                "label": "NRS Email",
                "insert_after": "nrs_tin",
            },
            {
                "fieldname": "nrs_col_break_ii",
                "fieldtype": "Column Break",
                "insert_after": "nrs_email",
            },
            {
                "fieldname": "nrs_einvoice_enabled",
                "fieldtype": "Check",
                "label": "NRS Enable EInvoice",
                "insert_after": "nrs_col_break_ii",
            },
            {
                "fieldname": "nrs_business_description",
                "fieldtype": "Small Text",
                "label": "Business Description",
                "insert_after": "nrs_einvoice_enabled",
            },
            {
                "fieldname": "nrs_intergration_section",
                "label": "NRS API Integration",
                "fieldtype": "Section Break",
                "insert_after": "nrs_business_description",
                "collapsible": 1,
            },
            {
                "bold": 1,
                "fieldname": "nrs_entity_id",
                "fieldtype": "Data",
                "label": "NRS Entity ID",
                "insert_after": "nrs_intergration_section",
            },
            {
                "fieldname": "nrs_business_id",
                "fieldtype": "Data",
                "label": "NRS Business ID",
                "insert_after": "nrs_entity_id",
            },
            {
                "fieldname": "nrs_col_break_iii",
                "fieldtype": "Column Break",
                "insert_after": "nrs_business_id",
            },
            {
                "bold": 1,
                "fieldname": "nrs_api_key",
                "fieldtype": "Password",
                "label": "NRS API KEY",
                "insert_after": "nrs_col_break_iii",
            },
            {
                "bold": 1,
                "fieldname": "nrs_client_secret",
                "fieldtype": "Password",
                "label": "NRS Client Secret",
                "insert_after": "nrs_api_key",
            },
            {
                "fieldname": "nrs_col_break_iv",
                "fieldtype": "Column Break",
                "insert_after": "nrs_client_secret",
            },
            {
                "fieldname": "nrs_service_id",
                "fieldtype": "Data",
                "label": "NRS Service ID",
                "insert_after": "nrs_col_break_iv",
            },
            {
                "fieldname": "nrs_process_key",
                "fieldtype": "Button",
                "label": "Process Key",
                "insert_after": "nrs_service_id",
                "hidden": 1,
            },
            {
                "fieldname": "nrs_details_section",
                "label": "NRS More Details",
                "fieldtype": "Section Break",
                "insert_after": "nrs_process_key",
                "collapsible": 1,
            },
            {
                "fieldname": "nrs_rc_number",
                "label": "RC Number (CAC)",
                "fieldtype": "Data",
                "insert_after": "nrs_details_section",
                "description": "Corporate Affairs Commission registration number",
            },
            {
                "fieldname": "nrs_vat_number",
                "label": "VAT Registration Number",
                "fieldtype": "Data",
                "insert_after": "nrs_rc_number",
            },
            {
                "fieldname": "nrs_col_break_v",
                "fieldtype": "Column Break",
                "insert_after": "nrs_vat_number",
            },
            {
                "fieldname": "nrs_registered_state",
                "label": "FIRS Registered State",
                "fieldtype": "Select",
                "insert_after": "nrs_col_break_v",
                "options": _NRS_STATES,
            },
            {
                "fieldname": "nrs_sirs_code",
                "label": "FIRS State Code",
                "fieldtype": "Data",
                "insert_after": "nrs_registered_state",
            },
            {
                "fieldname": "nrs_col_break_vi",
                "fieldtype": "Column Break",
                "insert_after": "nrs_sirs_code",
            },
            {
                "fieldname": "nrs_itf_liable",
                "label": "FIRS ITF Liable",
                "fieldtype": "Check",
                "insert_after": "nrs_col_break_vi",
                "default": "1",
            },
            {
                "fieldname": "nrs_address_section",
                "label": "NRS Postal Address",
                "fieldtype": "Section Break",
                "insert_after": "nrs_itf_liable",
                "collapsible": 1,
            },
            {
                "fieldname": "nrs_address",
                "label": "Street Address",
                "fieldtype": "Data",
                "insert_after": "nrs_address_section",
            },
            {
                "fieldname": "nrs_city",
                "label": "City",
                "fieldtype": "Data",
                "insert_after": "nrs_address",
            },
            {
                "fieldname": "nrs_col_break_vii",
                "fieldtype": "Column Break",
                "insert_after": "nrs_city",
            },
            {
                "fieldname": "ng_postal_code",
                "label": "Postal Code",
                "fieldtype": "Data",
                "insert_after": "nrs_col_break_vii",
            },
            {
                "fieldname": "nrs_state",
                "label": "State",
                "fieldtype": "Select",
                "insert_after": "ng_postal_code",
                "options": _NRS_STATES,
            },
            {
                "fieldname": "nrs_col_break_viii",
                "fieldtype": "Column Break",
                "insert_after": "nrs_state",
            },
            {
                "fieldname": "nrs_lga",
                "label": "Local Government Area",
                "fieldtype": "Data",
                "insert_after": "nrs_col_break_viii",
            },
            {
                "fieldname": "nrs_crypto_section",
                "label": "Cryptographic Keys (QR Code Signing)",
                "fieldtype": "Section Break",
                "insert_after": "nrs_lga",
            },
            {
                "fieldname": "nrs_public_key",
                "fieldtype": "Small Text",
                "label": "Public Key (base64)",
                "insert_after": "nrs_crypto_section",
            },
            {
                "fieldname": "nrs_col_break_ix",
                "fieldtype": "Column Break",
                "insert_after": "nrs_public_key",
            },
            {
                "fieldname": "nrs_certificate",
                "fieldtype": "Small Text",
                "label": "Certificate (base64)",
                "insert_after": "nrs_col_break_ix",
            },

        ],
        # ── Customer ─────────────────────────────────────────────────────────
        "Customer": [

            {
                "fieldname": "nrs_details_tab",
                "label": "NRS Data",
                "fieldtype": "Tab Break",
                "insert_after": "portal_users",
            },
            {
                "fieldname": "nrs_information_section",
                "label": "NRS Business Information",
                "fieldtype": "Section Break",
                "insert_after": "nrs_details_tab",            
            },
            {
                "fieldname": "nrs_tin",
                "label": "TIN",
                "fieldtype": "Data",
                "insert_after": "nrs_information_section",
                "description": "For B2B NRS e-invoicing",
            },
            {
                "fieldname": "nrs_rc_number",
                "label": "RC Number",
                "fieldtype": "Data",
                "insert_after": "nrs_tin",
                "description": "For B2C NRS e-invoicing",
            },
            {
                "fieldname": "nrs_invoice_kind",
                "label": "Invoice Kind",
                "fieldtype": "Select",
                "options": "\nB2C\nB2B\nB2G",
                "insert_after": "nrs_rc_number",
                "description": "NRS invoice classification. if TIN set as B2B, otherwise B2C.",
            },
            {
                "fieldname": "nrs_state",
                "label": "State",
                "fieldtype": "Select",
                "insert_after": "nrs_invoice_kind",
                "options": _NRS_STATES,
            },
            {
                "fieldname": "nrs_lga",
                "label": "Local Government Area",
                "fieldtype": "Data",
                "insert_after": "nrs_state",
            },
        ],
        # ── Item ──────────────────────────────────────────────────────────────
        "Item": [
            {
                "fieldname": "nrs_tem_type",
                "label": "NRS Item Type",
                "fieldtype": "Select",
                "options": "\nProduct\nService",
                "insert_after": "stock_uom",
            },
            {
                "fieldname": "nrs_hs_code",
                "label": "HS Code",
                "fieldtype": "Link",
                "options": "NRS HS Code",
                "insert_after": "nrs_tem_type",
                "depends_on": "eval: doc.nrs_tem_type == 'Product'",
                "description": "NRS Harmonized System product code — required for product item in e-invoices",
            },
            {
                "fieldname": "nrs_service_code",
                "label": "Service Code",
                "fieldtype": "Link",
                "options": "NRS Service Code",
                "insert_after": "nrs_hs_code",
                "depends_on": "eval: doc.nrs_tem_type == 'Service'",
                "description": "NRS service code — required for service items in e-invoices",
            },
        ],
        # ── Sales Invoice ─────────────────────────────────────────────────────
        "Sales Invoice": [
            {
                "fieldname": "nrs_section",
                "label": "NRS E-Invoice",
                "fieldtype": "Section Break",
                "insert_after": "remarks",
                "collapsible": 1,
            },
            {
                "fieldname": "nrs_irn",
                "label": "IRN",
                "fieldtype": "Data",
                "insert_after": "nrs_section",
                "read_only": 0,
                "description": "Invoice Reference Number from NRS MBS",
            },
            {
                "fieldname": "nrs_csid",
                "label": "CSID",
                "fieldtype": "Data",
                "insert_after": "nrs_irn",
                "read_only": 0,
                "description": "Cryptographic Stamp Identifier from NRS",
            },
            {
                "fieldname": "nrs_status",
                "label": "NRS Status",
                "fieldtype": "Select",
                "insert_after": "nrs_csid",
                "options": "Not Required\nPending\nSubmitted\nCleared\nAuto-Retry\nFailed\nCancelled",
                "default": "Not Required",
                "read_only": 1,
            },
            {
                "fieldname": "nrs_skip_einvoice",
                "label": "Skip NRS E-Invoice",
                "fieldtype": "Check",
                "insert_after": "nrs_status",
                "description": "When checked, this invoice is excluded from NRS e-invoicing. "
                               "Use for internal transfers, adjustments, or invoices not subject to fiscalization.",
            },
            {
                "fieldname": "nrs_payment_means",
                "label": "NRS Payment Means",
                "fieldtype": "Select",
                "insert_after": "nrs_skip_einvoice",
                "options": (
                    "\nCash\nCheque\nBank Transfer\nNEFT\nRTGS"
                    "\nDirect Debit\nCredit Card\nDebit Card"
                ),
                "description": (
                    "Override the NRS payment means code on this invoice. "
                    "Leave blank to auto-detect from Mode of Payment."
                ),
            },
        ],
    }

# ── Reference data ─────────────────────────────────────────────────────────

_NRS_STATES = (
    "\nAbia\nAdamawa\nAkwa Ibom\nAnambra\nBauchi\nBayelsa\nBenue\nBorno"
    "\nCross River\nDelta\nEbonyi\nEdo\nEkiti\nEnugu\nFCT\nGombe\nImo"
    "\nJigawa\nKaduna\nKano\nKatsina\nKebbi\nKogi\nKwara\nLagos\nNasarawa"
    "\nNiger\nOgun\nOndo\nOsun\nOyo\nPlateau\nRivers\nSokoto\nTaraba"
    "\nYobe\nZamfara"
)

def set_default_compliance_settings():
    """ quick fill """
    doc = frappe.get_single("NRS Compliance Settings")
    if doc.base_url_sandbox or doc.base_url_production :
        return
    
    doc = frappe.new_doc("NRS Compliance Settings")
    doc.base_url_sandbox = "https://eivc-k6z6d.ondigitalocean.app"
    doc.base_url_production = "https://api.einvoice.firs.gov.ng"
    doc.default_vat_rate = 7.5 
    doc.prn_template = "{{invoice_id(e.g:INV00XXX)}}-{{service-id}}-{{YYYYMMDD(e.g:20251219)}}"
    #... add more default fields
    doc.insert(ignore_permissions=True)

def before_uninstall():
    """ Remove custom fields set by this app"""
    custom_fields = _get_nrs_custom_fields()
    all_fieldnames = []
    for doctype, fields in custom_fields.items():
        for f in fields:
            all_fieldnames.append(f["fieldname"])
        frappe.db.delete(
            "Custom Field",
            {"dt": doctype, "fieldname": ["in", [f["fieldname"] for f in fields]]},
        )
    frappe.db.commit()