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
                        frappe.show_alert({ message: __("HS codes Syncing please wait..."), indicator: "blue" });
                        frappe.call({
                            method: "nrs_compliance.utils.resources.hs_codes_sync",
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

            frm.add_custom_button(__("Service-Codes Sync"), () => {
				frappe.confirm(
					__("Fetching Service codes from NRS."),
					() => {
						frappe.show_alert({ message: __("Service codes Syncing please wait..."), indicator: "blue" });
						frappe.call({
							method: "nrs_compliance.utils.resources.sync_service_codes",
							callback: r => {
								if (r.message) {
									frappe.show_alert({
										message: __("Synced {0} service codes", [r.message.synced]),
										indicator: "green",
									});
								}
							},
						});
					}
				);
			}, __("Get NRS Resources"));
        }
        /** Test Mode toggle */
        // Inject the CSS styling to turn checkboxes into iOS/Material sliding toggles
        const styleId = "frappe-custom-toggle-style";
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.innerHTML = `
                /* Targets the specific outer wrapper of your check field */
                [data-fieldname="env_switcher"] .data-row {
                    display: flex;
                    align-items: center;
                }
                
                /* Hide the native browser checkbox layout entirely */
                [data-fieldname="env_switcher"] input[type="checkbox"] {
                    position: relative;
                    width: 44px !important;
                    height: 22px !important;
                    appearance: none;
                    background: #e4e7eb;
                    border-radius: 999px;
                    border: none !important;
                    outline: none;
                    cursor: pointer;
                    transition: background 0.3s ease;
                }

                /* Change background color when the switch is toggled ON */
                [data-fieldname="env_switcher"] input[type="checkbox"]:checked {
                    background: #2b6cb0; /* Change to your preferred brand theme color */
                }

                /* Create the circular sliding switch knob */
                [data-fieldname="env_switcher"] input[type="checkbox"]::before {
                    content: '';
                    position: absolute;
                    width: 18px;
                    height: 18px;
                    border-radius: 50%;
                    top: 2px;
                    left: 2px;
                    background: #ffffff;
                    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.2);
                    transition: transform 0.3s ease;
                }

                /* Slide the knob to the right when active */
                [data-fieldname="env_switcher"] input[type="checkbox"]:checked::before {
                    transform: translateX(22px);
                }

                /* Proper spacing adjustments for the field label alongside the toggle box */
                [data-fieldname="env_switcher"] .label-area {
                    margin-left: 10px;
                    font-size: 13px;
                    cursor: pointer;
                    display: inline-block;
                }
            `;
            document.head.appendChild(style);
        }
    },
});
