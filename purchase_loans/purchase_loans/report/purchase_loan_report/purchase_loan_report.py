import frappe
from frappe import _

def execute(filters=None):
    return get_columns(), get_data(filters)

def get_columns():
    return [
        {"label": _("Purchase Loan Request"), "fieldname": "name", "fieldtype": "Link", "options": "Purchase Loan Request", "width": 150},
        {"label": _("Loan Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": _("Payment Status"), "fieldname": "payment_status", "fieldtype": "Data", "width": 150},
        {"label": _("RePayment Status"), "fieldname": "repayment_status", "fieldtype": "Data", "width": 150},
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
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
    # Check if the `workflow_state` field exists in the `Purchase Loan Request` doctype
    meta = frappe.get_meta("Purchase Loan Request")
    has_workflow_state = hasattr(meta, "fields") and any(field.fieldname == "workflow_state" for field in meta.fields)

    conditions = []
    values = {}

    # Add conditions based on filters
    date_filters = {
        "from_date": "posting_date >= %(from_date)s",
        "to_date": "posting_date <= %(to_date)s",
    }
    for key, condition in date_filters.items():
        if filters.get(key):
            conditions.append(condition)
            values[key] = filters[key]

    if filters.get("employee"):
        conditions.append("employee = %(employee)s")
        values["employee"] = filters["employee"]

    type_condition = {
        "Not Paid": "outstanding_amount_from_repayment > 0",
        "Paid": "outstanding_amount_from_repayment = 0",
    }
    if filters.get("type") in type_condition:
        conditions.append(type_condition[filters["type"]])

    # Construct the WHERE clause
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Include `workflow_state` if it exists, otherwise fallback to `docstatus`
    status_column = "workflow_state" if has_workflow_state else "docstatus"

    # Query with status conversion logic
    query = f"""
        SELECT 
            name, posting_date, employee, employee_name, request_amount, outstanding_amount_from_request, 
            overpaid_repayment_amount, paid_amount_from_request, repaid_amount, outstanding_amount_from_repayment, 
            overpaid_payment_amount,
            {status_column} AS status
        FROM 
            `tabPurchase Loan Request`
        WHERE 
            {where_clause}
        ORDER BY 
            posting_date DESC
    """
    
    # Fetch the data
    data = frappe.db.sql(query, values, as_dict=True)

    # Add custom logic for payment_status and repayment_status
    for row in data:
        # Determine payment_status
        if row.paid_amount_from_request == 0:
            row.payment_status = _("Not Paid")
        elif row.paid_amount_from_request > 0 and row.outstanding_amount_from_request > 0:
            row.payment_status = _("Partial Paid")
        elif row.outstanding_amount_from_request == 0 and row.overpaid_payment_amount <= 0:
            row.payment_status = _("Fully Paid")
        elif row.overpaid_payment_amount > 0:
            row.payment_status = _("Over Payment")

        # Determine repayment_status
        if row.repaid_amount == 0:
            row.repayment_status = _("Not Repaid")
        elif row.repaid_amount > 0 and row.outstanding_amount_from_repayment > 0:
            row.repayment_status = _("Partially Repaid")
        elif row.outstanding_amount_from_repayment == 0 and row.overpaid_repayment_amount <= 0:
            row.repayment_status = _("Fully Repaid")
        elif row.overpaid_repayment_amount > 0:
            row.repayment_status = _("Over RePayment")

    return data
