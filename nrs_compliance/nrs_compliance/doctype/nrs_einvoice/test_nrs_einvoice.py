# Copyright (c) 2026, Jide Olayinka [Pivotage] and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nrs_compliance.utils.nrs_einvoice import _update_einvoice


class TestNRSEInvoice(FrappeTestCase):
	@patch("nrs_compliance.utils.nrs_einvoice.frappe.db.commit")
	@patch("nrs_compliance.utils.nrs_einvoice.frappe.db.set_value")
	@patch("nrs_compliance.utils.nrs_einvoice._attach_qr_code")
	def test_qr_image_url_is_copied_to_sales_invoice(
		self, attach_qr_code, set_value, _commit
	):
		doc = frappe._dict(name="NRS-SINV-TEST", sales_invoice="SINV-TEST")
		doc.save = Mock()
		attach_qr_code.side_effect = lambda invoice, _qr_data: setattr(
			invoice, "encrypted_qr_code", "/files/qr.png"
		)

		_update_einvoice(doc, {}, {}, "Submitted", "", qr_data="qr-payload")

		set_value.assert_called_once_with(
			"Sales Invoice", "SINV-TEST", "nrs_irn_qrcode", "/files/qr.png"
		)

	@patch("nrs_compliance.utils.nrs_einvoice.frappe.db.commit")
	@patch("nrs_compliance.utils.nrs_einvoice.frappe.db.set_value")
	def test_missing_qr_image_does_not_update_sales_invoice(self, set_value, _commit):
		doc = frappe._dict(name="NRS-SINV-TEST", sales_invoice="SINV-TEST")
		doc.save = Mock()

		_update_einvoice(doc, {}, {}, "Pending", "")

		set_value.assert_not_called()
