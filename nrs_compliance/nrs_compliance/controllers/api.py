# Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
# For license information, please see license.txt

from __future__ import annotations

import base64
import json
import time

import frappe
from nrs_compliance.nrs_compliance.app import _get_settings


def generate_invoice_qr_data(irn: str, settings=None) -> str:
    """
    Generate the base64-encoded encrypted QR payload for a signed invoice.

    Returns empty string if crypto keys are not configured — callers should
    skip QR rendering in that case rather than raising.

    Args:
        irn:      The full IRN string (e.g. SINV202400001-94ND90NR-20240611)
        settings: Nigeria Compliance Settings doc (fetched if not provided)

    Returns:
        Base64 string suitable for rendering as a QR code image, or "".
    """
    if settings is None:
        #from nrs_compliance.nrs_compliance.app import _get_settings  
        settings = _get_settings()

    pub_key_b64 = (settings.get("nrs_public_key") or "").strip()
    certificate = (settings.get("nrs_certificate") or "").strip()

    if not pub_key_b64:
        return ""

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        frappe.log_error(
            "cryptography package not installed — cannot generate NRS QR code. "
            "Run: pip install cryptography",
            "NRS Invoice Signing",
        )
        return ""

    try:
        unix_ts = int(time.time())
        payload = json.dumps(
            {"irn": f"{irn}.{unix_ts}", "certificate": certificate},
            separators=(",", ":"),
        ).encode()

        pub_key_pem = base64.b64decode(pub_key_b64)
        public_key = serialization.load_pem_public_key(pub_key_pem, backend=default_backend())
        encrypted = public_key.encrypt(payload, padding.PKCS1v15())
        return base64.b64encode(encrypted).decode()

    except ValueError as e:
        frappe.log_error(
            f"NRS QR encryption failed for IRN {irn}: {e}. "
            f"If 'data too large', the certificate exceeds RSA PKCS#1 v1.5 capacity "
            f"(245B on a 2048-bit key) — use hybrid encryption. If 'Unable to load PEM', "
            f"the configured public key is invalid.",
            "NRS Invoice QR Generation",
        )
        return ""
    except Exception as e:
        frappe.log_error(str(e), "NRS Invoice QR Generation")
        return ""
