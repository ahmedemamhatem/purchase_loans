import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re
from purchase_loans.purchase_loans.tasks import copy_attachments_to_target


@frappe.whitelist()
def validate_purchase_invoice(doc, method):
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
        if not doc.is_new() and doc.custom_transaction_unique_id:
            copy_attachments_to_target(doc.doctype, doc.name, "Purchase Order")
    except Exception as e:
        # Log and throw any unexpected errors
        frappe.log_error(f"Error assigning custom_transaction_unique_id to Purchase Invoice {doc.name}: {str(e)}")

