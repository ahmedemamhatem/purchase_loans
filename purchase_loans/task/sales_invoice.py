import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re
from purchase_loans.purchase_loans.tasks import copy_attachments_to_target

@frappe.whitelist()
def validate_sales_invoice(doc, method):
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

        if not doc.is_new() and doc.custom_transaction_unique_id:
            copy_attachments_to_target(doc.doctype, doc.name, "Sales Order")
    except Exception as e:
        # Log and throw any unexpected errors
        frappe.log_error(f"Error assigning custom_transaction_unique_id to Sales Invoice {doc.name}: {str(e)}")
