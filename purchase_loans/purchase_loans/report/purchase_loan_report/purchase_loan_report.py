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
        {"label": _("Outstanding Amount From Request"), "fieldname": "outstanding_amount_from_request", "fieldtype": "Float", "width": 250},
        {"label": _("Overpaid Repayment Amount"), "fieldname": "overpaid_repayment_amount", "fieldtype": "Float", "width": 250},
        {"label": _("Repaid Amount"), "fieldname": "repaid_amount", "fieldtype": "Float", "width": 200},
        {"label": _("Outstanding Amount From Repayment"), "fieldname": "outstanding_amount_from_repayment", "fieldtype": "Float", "width": 280}
    ]

def get_data(filters):
    conditions = []
    values = {}

    # Filter by date range
    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    # Filter by employee
    if filters.get("employee"):
        conditions.append("employee = %(employee)s")
        values["employee"] = filters["employee"]

    # Filter by type
    if filters.get("type"):
        if filters["type"] == "Not Paid":
            conditions.append("outstanding_amount_from_repayment > 0")
        elif filters["type"] == "Paid":
            conditions.append("outstanding_amount_from_repayment = 0")

    # Construct the WHERE clause
    where_clause = " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT 
            posting_date, employee, employee_name, request_amount, outstanding_amount_from_request, overpaid_repayment_amount,
            paid_amount_from_request, repaid_amount, outstanding_amount_from_repayment
        FROM 
            `tabPurchase Loan Request`
        WHERE 
            1=1
            {" AND " + where_clause if where_clause else ""}
        ORDER BY 
            posting_date DESC
    """
    
    # Fetch the data
    data = frappe.db.sql(query, values, as_dict=True)
    return data