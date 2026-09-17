app_name = "nrs_compliance"
app_title = "NRS Compliance"
app_publisher = "Jide Olayinka [Pivotage]"
app_description = "NRS Compliance App"
app_email = "dev@pivotage.io"
app_license = "mit"

# Apps
# ------------------

# required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "nrs_compliance",
# 		"logo": "/assets/nrs_compliance/logo.png",
# 		"title": "NRS Compliance",
# 		"route": "/nrs_compliance",
# 		"has_permission": "nrs_compliance.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/nrs_compliance/css/nrs_compliance.css"
# app_include_js = "/assets/nrs_compliance/js/nrs_compliance.js"

# include js, css files in header of web template
# web_include_css = "/assets/nrs_compliance/css/nrs_compliance.css"
# web_include_js = "/assets/nrs_compliance/js/nrs_compliance.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "nrs_compliance/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "nrs_compliance/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "nrs_compliance.utils.jinja_methods",
# 	"filters": "nrs_compliance.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "nrs_compliance.utils.tasks.after_install"
after_migrate = "nrs_compliance.utils.tasks.after_migrate"
# before_install = "nrs_compliance.install.before_install"

# Uninstallation
# ------------

# before_uninstall = "nrs_compliance.uninstall.before_uninstall"
# after_uninstall = "nrs_compliance.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "nrs_compliance.utils.before_app_install"
# after_app_install = "nrs_compliance.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "nrs_compliance.utils.before_app_uninstall"
# after_app_uninstall = "nrs_compliance.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "nrs_compliance.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["nrs_compliance.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events
#"on_update": "nrs_compliance.nrs_compliance.overrides.service.nrs_submit_compliance",
#"on_submit": "nrs_compliance.nrs_compliance.overrides.service.on_sales_invoice_submit",

doc_events = {
	"Sales Invoice": {
		"validate": "nrs_compliance.nrs_compliance.overrides.service.fields_compliances",
		"before_submit": "nrs_compliance.nrs_compliance.overrides.service.nrs_submit_compliance",
        "on_submit": "nrs_compliance.nrs_compliance.overrides.service.on_sales_invoice_submit",
		
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		# Every 5 min: retry Auto-Retry e-invoices
        "*/5 * * * *": [
            "nrs_compliance.nrs_compliance.controllers.scheduler.retry_unflag_einvoices",
        ],
	},
	#  "daily": [
	# 	"nrs_compliance.tasks.daily"
	# ],
	# "hourly": [
	# 	"nrs_compliance.tasks.hourly"
	# ],
	# "weekly": [
	# 	"nrs_compliance.tasks.weekly"
	# ], 
	
}

# Testing
# -------

# before_tests = "nrs_compliance.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "nrs_compliance.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "nrs_compliance.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["nrs_compliance.utils.before_request"]
# after_request = ["nrs_compliance.utils.after_request"]

# Job Events
# ----------
# before_job = ["nrs_compliance.utils.before_job"]
# after_job = ["nrs_compliance.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"nrs_compliance.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

