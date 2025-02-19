import frappe
from frappe.utils import nowdate, getdate
from frappe import _  
from purchase_loans.purchase_loans.tasks import copy_attachments_to_target

@frappe.whitelist()
def validate_purchase_receipt(doc, method):
    """
    Validate that the posting_date of a Purchase Receipt is not before the transaction_date of its linked Purchase Order.
    Also assigns the custom_transaction_unique_id from the Purchase Order to the Purchase Receipt.
    """
    if doc.items:
        for m in doc.items:
            if not m.purchase_order:
                continue  # Skip if purchase_order is not set
            
            try:
                purchase_order = frappe.get_doc("Purchase Order", m.purchase_order)
                
                # Validate Posting Date
                if getdate(doc.posting_date) < getdate(purchase_order.transaction_date):
                    frappe.throw(
                        _("Posting Date ({0}) cannot be before Purchase Order Date ({1}) for PO {2}")
                        .format(doc.posting_date, purchase_order.transaction_date, m.purchase_order)
                    )

                if purchase_order.custom_transaction_unique_id:
                    doc.custom_transaction_unique_id = purchase_order.custom_transaction_unique_id
                    break  
            except Exception as e:
                frappe.log_error(f"Error fetching Purchase Order {m.purchase_order}: {str(e)}")
                pass  # Continue processing other items

        try:
            if not doc.is_new() and doc.custom_transaction_unique_id:
                copy_attachments_to_target(doc.doctype, doc.name, "Purchase Order")
        except Exception as e:
            frappe.log_error(f"Error copying attachments for Purchase Receipt {doc.name}: {str(e)}")
            pass



@frappe.whitelist()
def validate_delivery_note(doc, method):
    """
    Validate Delivery Note dates against linked Sales Order dates.

    Ensures that the posting date of a Delivery Note is not before the transaction date of its linked Sales Order.
    Also assigns the custom_transaction_unique_id from the Sales Order to the Delivery Note.
    """
    if doc.items:
        for m in doc.items:
            if not m.against_sales_order:
                continue  # Skip if against_sales_order is not set
            
            try:
                against_sales_order = frappe.get_doc("Sales Order", m.against_sales_order)
                
                # Validate Posting Date
                if getdate(doc.posting_date) < getdate(against_sales_order.transaction_date):
                    frappe.throw(
                        _("Posting Date ({0}) cannot be before Sales Order Date ({1}) for SO {2}")
                        .format(doc.posting_date, against_sales_order.transaction_date, m.against_sales_order)
                    )

                if against_sales_order.custom_transaction_unique_id:
                    doc.custom_transaction_unique_id = against_sales_order.custom_transaction_unique_id
                    break  
            except Exception as e:
                frappe.log_error(f"Error fetching Sales Order {m.against_sales_order}: {str(e)}")
                pass  # Continue processing other items

        try:
            if not doc.is_new() and doc.custom_transaction_unique_id:
                copy_attachments_to_target(doc.doctype, doc.name, "Sales Order")
        except Exception as e:
            frappe.log_error(f"Error copying attachments for Delivery Note {doc.name}: {str(e)}")
            pass
