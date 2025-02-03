frappe.query_reports["Purchase Loan Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -12),
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
            "fieldname": "currency",
            "label": __("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "reqd": 0
        },
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 0
        },
        {
            "fieldname": "purchase_loan_request",
            "label": __("Purchase Loan Request"),
            "fieldtype": "Link",
            "options": "Purchase Loan Request",
            "reqd": 0
        },
        {
            "fieldname": "payment_status",
            "label": __("Payment Status"),
            "fieldtype": "MultiSelectList",
            "options": [
                { "value": "Not Paid", "label": __("Not Paid") },
                { "value": "Partial Paid", "label": __("Partial Paid") },
                { "value": "Fully Paid", "label": __("Fully Paid") },
                { "value": "Need Over Payment", "label": __("Need Over Payment") },
                { "value": "Over Payment", "label": __("Over Payment") }
            ],
            "reqd": 0
        },
        {
            "fieldname": "repayment_status",
            "label": __("Repayment Status"),
            "fieldtype": "MultiSelectList",
            "options": [
                { "value": "Not Repaid", "label": __("Not Repaid") },
                { "value": "Partially Repaid", "label": __("Partially Repaid") },
                { "value": "Fully Repaid", "label": __("Fully Repaid") },
                { "value": "Over RePayment", "label": __("Over RePayment") }
            ],
            "reqd": 0
        }
    ]
};
