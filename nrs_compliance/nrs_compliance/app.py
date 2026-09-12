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
        "company_name": company.company_name
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