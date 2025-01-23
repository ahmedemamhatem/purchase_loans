// Copyright (c) 2025, Ahmed Emam and contributors
// For license information, please see license.txt

// frappe.query_reports["Sales Users Analytics"] = {
// 	"filters": [

// 	]
// };

frappe.query_reports["Sales Users Analytics"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -30), // Default: Last 30 days
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(), // Default: Today's date
            reqd: 1
        },
		{
            fieldname: "creator",
            label: __("Creator"),
            fieldtype: "Link",
            options: "User",
            default: frappe.session.user, // Set default to the current logged-in user (optional)
            reqd: 0
        },
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            reqd: 0
        }
    ]
};
