// Copyright (c) 2026, Jide Olayinka [Pivotage] and contributors
// For license information, please see license.txt

frappe.ui.form.on("NRS Compliance Settings", {
	refresh(frm) {
        /**
         * Sync resource:
         *  - hs code
         *  - service code
         */
        if (frm.doc.nrs_enabled) {
            frm.add_custom_button(__("HS-Codes Sync "), () => {
                frappe.confirm(
                    __("Fetching HS product codes from NRS."),
                    () => {
                        frappe.show_alert({ message: __("HS codes Syncing  please wait..."), indicator: "blue" });
                        frappe.call({
                            method: "nrs_compliance.nrs_compliance.doctype.nrs_compliance_settings.sync_hs_codes",
                            callback: r => {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __("Synced {0} HS-codes", [r.message.synced]),
                                        indicator: "green",
                                    });
                                }
                            },
                        });
                    }
                );
            }, __("Get NRS Resources"));
        }
    },
});
