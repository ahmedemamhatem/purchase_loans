frappe.query_reports["Sales Users Analytics"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "creator",
            label: __("Creator"),
            fieldtype: "Link",
            options: "User",
        },
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "group_by_customer",
            label: __("Group by Customer"),
            fieldtype: "Check",
            default: 0, // Default is unchecked
        },
        {
            fieldname: "group_by_item",
            label: __("Group by Item"),
            fieldtype: "Check",
            default: 0, // Default is unchecked
        },
    ],
};
