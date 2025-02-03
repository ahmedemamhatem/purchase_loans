import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re
import logging


@frappe.whitelist()
def set_direct_approver(doc):
    """Fetch and set the direct approver for the Sales Order and share the document if not already shared."""
    if frappe.session.user != doc.owner:
        return

    employee = frappe.db.get_value("Employee", {"user_id": doc.owner}, ["custom_purchase_loan_approver"], as_dict=True)
    
    if not (employee and employee.get("custom_purchase_loan_approver")):
        logging.error(f"No Direct approver found for the Employee: {doc.owner}")
        return
    
    approver_user = employee["custom_purchase_loan_approver"]
    approver_full_name = frappe.db.get_value("User", approver_user, "full_name")

    if not approver_full_name:
        logging.error(f"No full name found for the approver: {approver_user}")
        return


    if not frappe.db.exists("Share", {"doctype": doc.doctype, "docname": doc.name, "user": approver_user}):
        frappe.share.add(doc.doctype, doc.name, approver_user, read=1, write=1, submit=1)


@frappe.whitelist()
def update_old_sales_orders():
    """Batch update all old Sales Orders missing approvers."""
    sales_orders = frappe.get_all("Sales Order", filters={"custom_direct_approver_user": ["is", "not set"]})

    for so in sales_orders:
        doc = frappe.get_doc("Sales Order", so.name)
        set_direct_approver(doc)


@frappe.whitelist()
def validate_sales_order(doc, method):

    if not doc.is_new():
        set_direct_approver(doc)

    # Generate custom transaction unique ID if not set
    if not doc.custom_transaction_unique_id:
        existing_ids = frappe.db.get_all(
            'Sales Order', 
            filters={'custom_transaction_unique_id': ['like', 'SORD-%']},
            fields=['custom_transaction_unique_id']
        )

        # Find the highest numeric part of existing custom_transaction_unique_id
        highest_num = 0
        for record in existing_ids:
            match = re.search(r'SORD-(\d{8})$', record.custom_transaction_unique_id)
            if match:
                num = int(match.group(1))
                highest_num = max(highest_num, num)

        # Increment the highest number found or start with 1 if none found
        new_num = highest_num + 1 if highest_num > 0 else 1

        # Generate and assign new unique ID
        unique_id = f"SORD-{new_num:08d}"
        doc.custom_transaction_unique_id = unique_id



    # Validate each item in the Sales Order
    for item in doc.items:
        # Fetch the company's custom role
        company_record = frappe.get_doc("Company", doc.company)
        required_role = company_record.custom_role

        # Get item details
        is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        is_fixed_asset = frappe.db.get_value("Item", item.item_code, "is_fixed_asset")
        user_roles = frappe.get_roles(frappe.session.user)

        
        # Check role restrictions
        if (is_stock_item == 1 or is_fixed_asset == 1) and required_role in user_roles and frappe.session.user != "Administrator":
            frappe.throw(f"You cannot create orders for stock or fixed asset items for the role '{required_role}'.")

        # If the item is a stock item, check stock availability
        if is_stock_item == 1:
            result = frappe.db.sql("""
                SELECT SUM(actual_qty) as actual_qty, SUM(reserved_qty) as reserved_qty
                FROM `tabBin` 
                WHERE item_code = %s
            """, (item.item_code,))

            total_qty, reserved_qty = result[0] if result else (0, 0)
            available_qty = total_qty - reserved_qty

            # Check if available quantity is less than the ordered quantity
            if available_qty < item.qty:
                frappe.throw(
                    f"Insufficient stock for Item {item.item_code}.<br>"
                    f"<b>Available Quantity:</b> {total_qty} <b>(Available after Reservations: {available_qty}, Reserved: {reserved_qty})</b><br>"
                    f"<b>Ordered Quantity:</b> {item.qty}.<br>"
                    "You can only sell the Available after Reservations."
                )

    # Flag to track if all items are neither stock nor fixed assets
    all_not_stock_or_fixed_asset = True

    # Iterate through all items to check if any are stock or fixed assets
    for item in doc.items:
        is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        is_fixed_asset = frappe.db.get_value("Item", item.item_code, "is_fixed_asset")

        # If any item is a stock item or a fixed asset, mark the flag as False
        if is_stock_item or is_fixed_asset:
            all_not_stock_or_fixed_asset = False
            break  # No need to check further if one item fails

        # Otherwise, mark item as delivered_by_supplier
        item.delivered_by_supplier = 1

    # Set `per_delivered` to 100 if all items are neither stock nor fixed assets
    if all_not_stock_or_fixed_asset:
        doc.per_delivered = 100
