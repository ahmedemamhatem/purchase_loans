import frappe
from frappe import _

def execute(filters=None):
    return get_columns(), get_data(filters)

def get_columns():
    return [
        {"label": _("Purchase Loan Request"), "fieldname": "name", "fieldtype": "Link", "options": "Purchase Loan Request", "width": 250},
        {"label": _("Loan Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "width": 100},
        {"label": _("Payment Status"), "fieldname": "payment_status", "fieldtype": "Data", "width": 150},
        {"label": _("Repayment Status"), "fieldname": "repayment_status", "fieldtype": "Data", "width": 150},
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
        {"label": _("Employee ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": _("Request Amount"), "fieldname": "request_amount", "fieldtype": "Float", "width": 150},
        {"label": _("Paid Amount From Request"), "fieldname": "paid_amount_from_request", "fieldtype": "Float", "width": 250},
        {"label": _("Overpaid Payment Amount"), "fieldname": "overpaid_payment_amount", "fieldtype": "Float", "width": 250},
        {"label": _("Outstanding Amount From Request"), "fieldname": "outstanding_amount_from_request", "fieldtype": "Float", "width": 250},
        {"label": _("Repaid Amount"), "fieldname": "repaid_amount", "fieldtype": "Float", "width": 200},
        {"label": _("Overpaid Repayment Amount"), "fieldname": "overpaid_repayment_amount", "fieldtype": "Float", "width": 250},
        {"label": _("Outstanding Amount From Repayment"), "fieldname": "outstanding_amount_from_repayment", "fieldtype": "Float", "width": 280}
    ]

def get_data(filters):
    meta = frappe.get_meta("Purchase Loan Request")
    has_workflow_state = any(field.fieldname == "workflow_state" for field in meta.fields)

    conditions, values = [], {}
    date_filters = {
        "from_date": "posting_date >= %(from_date)s",
        "to_date": "posting_date <= %(to_date)s",
    }
    conditions.extend([date_filters[key] for key in date_filters if filters.get(key)])
    values.update({key: filters[key] for key in date_filters if filters.get(key)})

    if filters.get("employee"):
        conditions.append("employee = %(employee)s")
        values["employee"] = filters["employee"]

    if filters.get("currency"):
        conditions.append("currency = %(currency)s")
        values["currency"] = filters["currency"]

    if filters.get("purchase_loan_request"):
        conditions.append("name = %(purchase_loan_request)s")
        values["purchase_loan_request"] = filters["purchase_loan_request"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    status_column = "workflow_state" if has_workflow_state else "docstatus"

    query = f"""
        SELECT 
            name, posting_date, employee, employee_name, request_amount, outstanding_amount_from_request, 
            overpaid_repayment_amount, paid_amount_from_request, repaid_amount, outstanding_amount_from_repayment, 
            overpaid_payment_amount, currency,
            {status_column} AS status
        FROM 
            `tabPurchase Loan Request`
        WHERE 
            {where_clause}
        ORDER BY 
            posting_date DESC
    """
    data = frappe.db.sql(query, values, as_dict=True)

    # Compute payment_status and repayment_status dynamically
    filtered_data = []
    for row in data:
        row.payment_status = (
            "Not Paid" if row.paid_amount_from_request == 0 else
            "Partial Paid" if row.outstanding_amount_from_request > 0 else
            "Fully Paid" if row.overpaid_payment_amount <= 0 and row.overpaid_repayment_amount <= 0 and row.outstanding_amount_from_request == 0 else
            "Need Over Payment" if row.repaid_amount > row.paid_amount_from_request else
            "Over Payment" if row.overpaid_payment_amount > 0 else ""
        )

        row.repayment_status = (
            "Not Repaid" if row.repaid_amount == 0 else
            "Partially Repaid" if row.outstanding_amount_from_repayment > 0 else
            "Fully Repaid" if row.overpaid_repayment_amount <= 0 and row.outstanding_amount_from_repayment == 0 else
            "Over RePayment" if row.overpaid_repayment_amount > 0 else ""
        )

        # Apply MultiSelect filters
        selected_payment_statuses = frappe.parse_json(filters.get("payment_status", "[]"))
        selected_repayment_statuses = frappe.parse_json(filters.get("repayment_status", "[]"))

        if selected_payment_statuses and row.payment_status not in selected_payment_statuses:
            continue
        if selected_repayment_statuses and row.repayment_status not in selected_repayment_statuses:
            continue

        filtered_data.append(row)

    return filtered_data
