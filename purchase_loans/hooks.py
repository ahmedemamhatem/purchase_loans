app_name = "purchase_loans"
app_title = "Purchase Loans"
app_publisher = "Ahmed Emam"
app_description = "purchase-loans"
app_email = "ahmedemamhatem@gmail.com"
app_license = "mit"

# Apps
# ------------------

fixtures = [
    {"dt": "Custom Field"},
    {"dt": "Property Setter"}
    ]

doc_events = {
    "Journal Entry": {
        "on_cancel": "purchase_loans.purchase_loans.tasks.update_purchase_loan_request_on_cancel",
        "on_submit": "purchase_loans.purchase_loans.tasks.update_purchase_loan_request_on_submit"
    }
}

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "purchase_loans",
# 		"logo": "/assets/purchase_loans/logo.png",
# 		"title": "Purchase Loans",
# 		"route": "/purchase_loans",
# 		"has_permission": "purchase_loans.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/purchase_loans/css/purchase_loans.css"
# app_include_js = "/assets/purchase_loans/js/purchase_loans.js"

# include js, css files in header of web template
# web_include_css = "/assets/purchase_loans/css/purchase_loans.css"
# web_include_js = "/assets/purchase_loans/js/purchase_loans.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "purchase_loans/public/scss/website"

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
# app_include_icons = "purchase_loans/public/icons.svg"

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
# 	"methods": "purchase_loans.utils.jinja_methods",
# 	"filters": "purchase_loans.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "purchase_loans.install.before_install"
# after_install = "purchase_loans.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "purchase_loans.uninstall.before_uninstall"
# after_uninstall = "purchase_loans.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "purchase_loans.utils.before_app_install"
# after_app_install = "purchase_loans.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "purchase_loans.utils.before_app_uninstall"
# after_app_uninstall = "purchase_loans.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "purchase_loans.notifications.get_notification_config"

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

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"purchase_loans.tasks.all"
# 	],
# 	"daily": [
# 		"purchase_loans.tasks.daily"
# 	],
# 	"hourly": [
# 		"purchase_loans.tasks.hourly"
# 	],
# 	"weekly": [
# 		"purchase_loans.tasks.weekly"
# 	],
# 	"monthly": [
# 		"purchase_loans.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "purchase_loans.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "purchase_loans.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "purchase_loans.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["purchase_loans.utils.before_request"]
# after_request = ["purchase_loans.utils.after_request"]

# Job Events
# ----------
# before_job = ["purchase_loans.utils.before_job"]
# after_job = ["purchase_loans.utils.after_job"]

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
# 	"purchase_loans.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

