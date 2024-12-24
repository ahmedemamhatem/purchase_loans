import frappe
from frappe import _

def execute(filters=None):
    return get_columns(), get_data(filters)

def get_columns():
    return [
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
    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT 
            posting_date, employee, employee_name, request_amount, outstanding_amount_from_request, overpaid_repayment_amount,
            paid_amount_from_request, repaid_amount, outstanding_amount_from_repayment, overpaid_payment_amount
        FROM 
            `tabPurchase Loan Request`
        WHERE 
            {where_clause}
        ORDER BY 
            posting_date DESC
    """
    
    # Fetch the data
    return frappe.db.sql(query, values, as_dict=True)
