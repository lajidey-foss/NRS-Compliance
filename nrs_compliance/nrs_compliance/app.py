# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt
"""
Keys, Headers, api calls and more

400/422 from NRS — permanent failure, worked on.
"""
import frappe

_APP_SETTINGS = "NRS Compliance Settings"

class EComplianceError(Exception):
    pass

class EComplianceValidationError(EComplianceError):
    pass

#Settings
def _get_settings(company_name=None):
    # Fetch app-level settings
    app_settings = frappe.get_cached_doc(_APP_SETTINGS)

    # Fetch user company data (default company if none provided)
    if not company_name:
        company_name = frappe.db.get_single_value("Global Defaults", "default_company")
    company = frappe.get_cached_doc("Company", company_name)

    # Merge into a single dict
    # get all needed key pairs from app settings and company nrs tab
    combined = {
        "nrs_enabled": app_settings.nrs_enabled,
        "company_name": company.company_name,
        "nrs_service_id": company.nrs_service_id,
        "nrs_business_id": company.nrs_business_id
    }

    return combined
# Base url
def _base_url(settings) -> str:
    if settings.prod_environment:
        return (settings.base_url_production or "https://api.einvoice.firs.gov.ng").rstrip("/")
    return (settings.base_url_sandbox or "https://eivc-k6z6d.ondigitalocean.app").rstrip("/")

# headers
def _headers(settings) -> dict:
    """
    Auth is permanent API key + secret headers — no token fetch, no Bearer token.
    Every request carries x-api-key and x-api-secret.
    """
    return {
        "x-api-key": settings.get_password("einvoice_api_key"),
        "x-api-secret": settings.get_password("einvoice_api_secret"),
        "Content-Type": "application/json",
    }

def _build_postal_address(
    street: str, city: str, postal_zone: str, country: str,
    state: str = "", lga: str = "",
) -> dict:
    addr = {
        "street_name": street or "",
        "city_name": city or "",
        "postal_zone": postal_zone or "",
        "country": country or "NG",
    }
    if state:
        addr["state"] = state
    if lga:
        addr["lga"] = lga
    return addr

def _build_tax_subtotals(doc, default_vat_rate: float) -> tuple[list[dict], float]:
    """
    Get TaxTotal subtotals
    """
    #. !ISSUE: function to return tax category default to "STANDARD_VAT"

    merged: dict[str, dict] = {} 

    for tax_row in (doc.taxes or []):
        amount = float(tax_row.tax_amount or 0)
        if amount == 0:
            continue
        rate = float(tax_row.rate or 0)
        category = "STANDARD_VAT" # function to get tax_category
        if category in merged:
            merged[category]["tax_amount"] = round(merged[category]["tax_amount"] + amount, 2)
        else:
            merged[category] = {
                "taxable_amount": round(float(doc.net_total), 2),
                "tax_amount": round(amount, 2),
                "tax_category": {"id": category, "percent": rate},
            }

    if not merged:
        # tax rows is null — fall back to configured default
        category ="STANDARD_VAT" # function to get tax_category
        total_vat = round(float(doc.net_total) * (default_vat_rate / 100), 2)
        return [
            {
                "taxable_amount": round(float(doc.net_total), 2),
                "tax_amount": total_vat,
                "tax_category": {"id": category, "percent": default_vat_rate},
            }
        ], total_vat

    subtotals = list(merged.values())
    total_vat = round(sum(s["tax_amount"] for s in subtotals), 2)
    return subtotals, total_vat

# NRS returns transient/server-busy conditions as HTTP 400 with one of these
# phrases. They must be treated as retryable (Auto-Retry), NOT permanent failures.
_TRANSIENT_NRS_MARKERS = (
    "try again later",
    "unable to complete this operation at this time",
    "we are unable to process your request",
    "temporarily unavailable",
    "please try again",
)