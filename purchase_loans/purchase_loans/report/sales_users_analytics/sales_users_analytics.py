import frappe
from frappe.utils import flt

def execute(filters=None):
    # Define columns based on filters
    columns = get_columns(filters)

    # Get data based on filters
    data = get_data(filters)

    return columns, data

def get_columns(filters):
    columns = [
        {"fieldname": "creator_full_name", "label": "Creator Full Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "qty_with_rate", "label": "Qty with Rate", "fieldtype": "Float", "width": 200},
        {"fieldname": "qty_free", "label": "Qty Free (Rate = 0)", "fieldtype": "Float", "width": 200},
        {"fieldname": "value", "label": "Total Value", "fieldtype": "Currency", "options": "currency", "width": 200},
    ]

    # Dynamically add columns based on grouping filters
    if filters.get("group_by_customer"):
        columns.insert(1, {"fieldname": "customer", "label": "Customer", "fieldtype": "Data", "width": 200})

    if filters.get("group_by_item"):
        columns.insert(1, {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Link", "options": "Item", "width": 200})
        columns.insert(2, {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "width": 200})

    return columns

def get_data(filters):
    conditions = []
    values = {}

    # Add filter conditions
    if filters.get("creator"):
        conditions.append("so.owner = %(creator)s")
        values["creator"] = filters["creator"]

    if filters.get("item_code"):
        conditions.append("soi.item_code = %(item_code)s")
        values["item_code"] = filters["item_code"]

    if filters.get("customer") and filters.get("group_by_customer"):
        conditions.append("so.customer = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters["from_date"]
        values["to_date"] = filters["to_date"]

    condition_str = " AND ".join(conditions) if conditions else "1=1"

    # Determine the GROUP BY clause dynamically
    group_by_fields = ["so.owner", "u.full_name"]
    if filters.get("group_by_customer"):
        group_by_fields.append("so.customer")
    if filters.get("group_by_item"):
        group_by_fields.append("soi.item_code")
        group_by_fields.append("soi.item_name")

    group_by_clause = ", ".join(group_by_fields)

    # Select fields dynamically based on grouping filters
    select_fields = [
        "so.owner AS creator",
        "u.full_name AS creator_full_name",
    ]
    if filters.get("group_by_customer"):
        select_fields.append("so.customer AS customer")
    if filters.get("group_by_item"):
        select_fields.append("soi.item_code AS item_code")
        select_fields.append("soi.item_name AS item_name")

    select_fields.extend([
        "SUM(CASE WHEN soi.rate > 0 THEN soi.qty ELSE 0 END) AS qty_with_rate",
        "SUM(CASE WHEN soi.rate = 0 THEN soi.qty ELSE 0 END) AS qty_free",
        "SUM(soi.amount) AS value"
    ])

    select_clause = ", ".join(select_fields)

    # Query data
    query = f"""
        SELECT
            {select_clause}
        FROM
            `tabSales Order` so
        INNER JOIN
            `tabSales Order Item` soi ON soi.parent = so.name
        LEFT JOIN
            `tabUser` u ON so.owner = u.name
        WHERE
            so.docstatus = 1 AND {condition_str}
        GROUP BY
            {group_by_clause}
        ORDER BY
            so.owner, soi.item_code
    """
    return frappe.db.sql(query, values, as_dict=True)
