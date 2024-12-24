// Copyright (c) 2024, Ahmed Emam and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Loan Report"] = {
	"filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 0
        },
        {
            "fieldname": "type",
            "label": __("Type"),
            "fieldtype": "Select",
            "options": "All\nPaid\nNot Paid",
            "reqd": 0
        }
    ]
};