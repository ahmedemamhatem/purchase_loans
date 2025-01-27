import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re


@frappe.whitelist()
def validate_purchase_receipt(doc, method):
    try:
        if doc.items:
            for m in doc.items:
                # Ensure that purchase_order is present
                if m.purchase_order:
                    # Fetch the Purchase Order document
                    purchase_order = frappe.get_doc("Purchase Order", m.purchase_order)
                    
                    # Check if custom_transaction_unique_id exists in the Purchase Order
                    if purchase_order.custom_transaction_unique_id:
                        # Assign the ID from the Purchase Order to the Purchase Invoice
                        doc.custom_transaction_unique_id = purchase_order.custom_transaction_unique_id
                        break  # Once we set the ID, we can stop the loop as it's assumed to be unique
                    else:
                        # Optionally, handle the case where there is no ID on the Purchase Order
                        frappe.msgprint(_("Custom Transaction Unique ID not found on Purchase Order: {0}".format(m.purchase_order)))
        
    except Exception as e:
        # Log and throw any unexpected errors
        frappe.log_error(f"Error assigning custom_transaction_unique_id to Purchase Invoice {doc.name}: {str(e)}")



@frappe.whitelist()
def validate_delivery_note(doc, method):
    try:
        if doc.items:
            for m in doc.items:
                # Ensure that sales_order is present
                if m.sales_order:
                    # Fetch the Sales Order document
                    sales_order = frappe.get_doc("Sales Order", m.sales_order)
                    
                    # Check if custom_transaction_unique_id exists in the Sales Order
                    if sales_order.custom_transaction_unique_id:
                        # Assign the ID from the Sales Order to the Sales Invoice
                        doc.custom_transaction_unique_id = sales_order.custom_transaction_unique_id
                        break  # Once we set the ID, we can stop the loop as it's assumed to be unique
                    else:
                        # Optionally, handle the case where there is no ID on the Sales Order
                        frappe.msgprint(_("Custom Transaction Unique ID not found on Sales Order: {0}".format(m.sales_order))) 
    except Exception as e:
        # Log and throw any unexpected errors
        frappe.log_error(f"Error assigning custom_transaction_unique_id to Sales Invoice {doc.name}: {str(e)}")
