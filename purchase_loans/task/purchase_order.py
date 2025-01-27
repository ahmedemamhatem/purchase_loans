import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re



@frappe.whitelist()
def validate_purchase_order(doc, method):
    # Check if all items have consistent `is_stock_item` and `is_fixed_asset` values
    first_item = doc.items[0]
    first_is_stock_item = frappe.db.get_value("Item", first_item.item_code, "is_stock_item")
    first_is_fixed_asset = frappe.db.get_value("Item", first_item.item_code, "is_fixed_asset")

    # Fetch the company's custom role
    company_record = frappe.get_doc("Company", doc.company)
    required_role = company_record.custom_role

    for item in doc.items:
        is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        is_fixed_asset = frappe.db.get_value("Item", item.item_code, "is_fixed_asset")

        user_roles = frappe.get_roles(frappe.session.user)

        if (is_stock_item == 1 or is_fixed_asset == 1) and required_role in user_roles and frappe.session.user != "Administrator":
            frappe.throw("You cannot create orders for stock or fixed asset items.")

        # If the current item's properties don't match the first item's properties, throw an error
        if is_stock_item != first_is_stock_item or is_fixed_asset != first_is_fixed_asset:
            frappe.throw(
                "All items in the Purchase Order must have consistent values for 'Stock Item'  properties."
            )

    # Generate a unique ID for the Purchase Order
    if not doc.custom_transaction_unique_id:
        # Query the existing Purchase Orders to find the highest unique ID
        existing_ids = frappe.db.get_all('Purchase Order', filters={'custom_transaction_unique_id': ['like', 'PORD-%']}, fields=['custom_transaction_unique_id'])

        # Extract the numerical part and find the highest number
        highest_num = 0
        for record in existing_ids:
            match = re.search(r'PORD-(\d{8})$', record.custom_transaction_unique_id)  # Match 8-digit numbers only
            if match:
                num = int(match.group(1))
                if num > highest_num:
                    highest_num = num

        # Increment the highest number found or start with 1 if none found
        new_num = highest_num + 1 if highest_num > 0 else 1

        # Generate the unique ID with the new number
        unique_id = f"PORD-{new_num:08d}"  # Padded to ensure 8 digits

        # Set the generated ID to the custom field
        doc.custom_transaction_unique_id = unique_id

    # Flag to track if all items are not stock or fixed assets
    all_not_stock_or_fixed_asset = True

    # Iterate through all items
    for item in doc.items:
        is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        is_fixed_asset = frappe.db.get_value("Item", item.item_code, "is_fixed_asset")
        
        # If any item is a stock item or a fixed asset, set the flag to False
        if is_stock_item or is_fixed_asset:
            all_not_stock_or_fixed_asset = False
            break  # No need to check further if one fails

        # Otherwise, mark delivered_by_supplier
        item.delivered_by_supplier = 1

    # Set doc.per_received to 100 if all items are not stock or fixed assets
    if all_not_stock_or_fixed_asset:
        doc.per_received = 100
