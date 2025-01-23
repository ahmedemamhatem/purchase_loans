import frappe
from frappe.utils import flt, nowdate

def execute(filters=None):
    # Define columns
    columns = get_columns()

    # Get data based on filters
    data = get_data(filters)

    return columns, data

def get_columns():
    return [
       
        {"fieldname": "creator_full_name", "label": "Creator Full Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "customer", "label": "Customer", "fieldtype": "Data", "width": 200},
        {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "qty_with_rate", "label": "Qty with Rate", "fieldtype": "Float", "width": 200},
        {"fieldname": "qty_free", "label": "Qty Free (Rate = 0)", "fieldtype": "Float", "width": 200},
        {"fieldname": "value", "label": "Total Value", "fieldtype": "Currency", "options": "currency", "width": 200},
    ]

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

    if filters.get("customer"):
        conditions.append("so.customer = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters["from_date"]
        values["to_date"] = filters["to_date"]

    condition_str = " AND ".join(conditions) if conditions else "1=1"

    # Query data
    query = f"""
        SELECT
            so.owner AS creator,
            u.full_name AS creator_full_name,
            so.customer AS customer,
            soi.item_code AS item_code,
            soi.item_name AS item_name,
            SUM(CASE WHEN soi.rate > 0 THEN soi.qty ELSE 0 END) AS qty_with_rate,
            SUM(CASE WHEN soi.rate = 0 THEN soi.qty ELSE 0 END) AS qty_free,
            SUM(soi.amount) AS value
        FROM
            `tabSales Order` so
        INNER JOIN
            `tabSales Order Item` soi ON soi.parent = so.name
        LEFT JOIN
            `tabUser` u ON so.owner = u.name
        WHERE
            so.docstatus = 1 AND {condition_str}
        GROUP BY
            so.owner, u.full_name, so.customer, soi.item_code
        ORDER BY
            so.owner, so.customer, soi.item_code
    """
    return frappe.db.sql(query, values, as_dict=True)
