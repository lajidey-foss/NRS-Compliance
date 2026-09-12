# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt
"""
Handles NRS resource Data sync
    - Hs-code
    - Service-code
"""
import frappe
import requests
from nrs_compliance.nrs_compliance.app import _get_settings, _base_url, _headers


_HS_CODE_EINVOICE = "/api/v1/invoice/resources/hs-codes"
_SERVICE_CODE_EINVOICE = "/api/v1/invoice/resources/services-codes"

# Hs (product)
@frappe.whitelist()
def hs_codes_sync():
    """
    GET => /hs-codes
    """
    settings = _get_settings()
    # nrs_enabled from settings --> work on einvoice enabled from company
    if not settings.nrs_enabled:
        frappe.msgprint("e-Invoice is not enabled.", indicator="orange", alert=True)
        return {"synced": 0}

    resp = requests.get(
        f"{_base_url(settings)}{_HS_CODE_EINVOICE}",
        headers=_headers(settings),
        timeout=60,
    )
    if not resp.ok:
        frappe.throw(f"NRS HS Code sync failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    if isinstance(data, dict):
        items = data.get("data") or data.get("result") or list(data.values())
    else:
        items = data

    count = 0
    for item in items:
        # NRS returns the HS code under the "hscode" key (service codes use "code")
        code = str(item.get("hscode") or item.get("code") or item.get("Code") or "").strip()
        description = str(item.get("description") or item.get("Description") or "").strip()
        if not code:
            continue

        if frappe.db.exists("NRS HS Code", code):
            frappe.db.set_value("NRS HS Code", code, "description", description)
        else:
            frappe.get_doc({
                "doctype": "NRS HS Code",
                "name": code,
                "hs_code": code,
                "description": description,
            }).insert(ignore_permissions=True)
        count += 1

    frappe.db.commit()
    frappe.msgprint(f"Synced {count} HS codes from NRS.", indicator="green", alert=True)
    return {"synced": count}

@frappe.whitelist()
def sync_service_codes():
    """
    GET => /services-codes
    service code from nrs into service code doctype
    """
    settings = _get_settings()
    if not settings.nrs_enabled:
        frappe.msgprint("e-Invoice is not enabled.", indicator="orange", alert=True)
        return {"synced": 0}
    
    resp = requests.get(
        f"{_base_url(settings)}{_SERVICE_CODE_EINVOICE}",
        headers=_headers(settings),
        timeout=60,
    )
    if not resp.ok:
        frappe.throw(f"NRS Service Code sync failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    if isinstance(data, dict):
        items = data.get("data") or data.get("result") or list(data.values())
    else:
        items = data

    count = 0
    for item in items:
        code = str(item.get("code") or item.get("Code") or "").strip()
        description = str(item.get("description") or item.get("Description") or "").strip()
        if not code:
            continue

        if frappe.db.exists("NRS Service Code", code):
            frappe.db.set_value("NRS Service Code", code, "description", description)
        else:
            frappe.get_doc({
                "doctype": "NRS Service Code",
                "name": code,
                "service_code": code,
                "description": description,
            }).insert(ignore_permissions=True)
        count += 1

    frappe.db.commit()
    frappe.msgprint(f"Synced {count} service codes from NRS.", indicator="green", alert=True)
    return {"synced": count}