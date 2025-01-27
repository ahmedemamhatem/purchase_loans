# Copyright (c) 2025, Ahmed Emam and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Asset Name", "fieldname": "asset_name", "fieldtype": "Data", "width": 200},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Asset Category", "fieldname": "asset_category", "fieldtype": "Link", "options": "Asset Category", "width": 150},
        {"label": "Asset Status", "fieldname": "status", "fieldtype": "Select", "width": 150},
        {"label": "Purchase Date", "fieldname": "purchase_date", "fieldtype": "Date", "width": 150},
        {"label": "Available-for-use Date", "fieldname": "available_for_use_date", "fieldtype": "Date", "width": 150},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 200},
        {"label": "Custodian (Full Name)", "fieldname": "custodian_full_name", "fieldtype": "Data", "width": 200},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 200},
        {"label": "Asset Value", "fieldname": "gross_purchase_amount", "fieldtype": "Currency", "width": 150},
        {"label": "Additional Asset Cost", "fieldname": "additional_asset_cost", "fieldtype": "Currency", "width": 150},
        {"label": "Total Asset Cost", "fieldname": "total_asset_cost", "fieldtype": "Currency", "width": 150},
        
    ]


def get_data(filters):
    conditions = ""

    if filters.get("location"):
        conditions += " AND location = %(location)s"
    if filters.get("custodian"):
        conditions += " AND custodian = %(custodian)s"
    if filters.get("department"):
        conditions += " AND department = %(department)s"
    if filters.get("asset_category"):
        conditions += " AND asset_category = %(asset_category)s"

    query = f"""
        SELECT
            a.asset_name,
            a.item_name,
            a.asset_category,
            a.status,
            a.purchase_date,
            a.available_for_use_date,
            a.location,
            e.employee_name AS custodian_full_name,
            a.department,
            a.additional_asset_cost,
            a.total_asset_cost AS total_asset_cost,
            a.gross_purchase_amount
        FROM
            `tabAsset` a
        LEFT JOIN
            `tabEmployee` e ON a.custodian = e.name
        WHERE
            1=1 {conditions}
    """
    return frappe.db.sql(query, filters, as_dict=True)
