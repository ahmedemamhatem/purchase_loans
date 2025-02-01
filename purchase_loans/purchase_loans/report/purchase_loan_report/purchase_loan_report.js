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
            "fieldtype": "Select",
            "options": [
                "",
                "Not Paid",
                "Partial Paid",
                "Fully Paid",
                "Need Over Payment",
                "Over Payment"
            ],
            "reqd": 0
        },
        {
            "fieldname": "repayment_status",
            "label": __("Repayment Status"),
            "fieldtype": "Select",
            "options": [
                "",
                "Not Repaid",
                "Partially Repaid",
                "Fully Repaid",
                "Over RePayment"
            ],
            "reqd": 0
        }
    ]
};
