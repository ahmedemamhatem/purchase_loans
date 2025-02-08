import frappe
from frappe.utils import nowdate, getdate
from frappe import _  
from purchase_loans.purchase_loans.tasks import copy_attachments_to_target

@frappe.whitelist()
def validate_purchase_receipt(doc, method):
    if doc.items:
        for m in doc.items:
            if m.purchase_order:
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

        if not doc.is_new() and doc.custom_transaction_unique_id:
            copy_attachments_to_target(doc.doctype, doc.name, "Purchase Order")

@frappe.whitelist()
def validate_delivery_note(doc, method):
    if doc.items:
        for m in doc.items:
            if m.sales_order:
                sales_order = frappe.get_doc("Sales Order", m.sales_order)
                
                # Validate Posting Date
                if getdate(doc.posting_date) < getdate(sales_order.transaction_date):
                    frappe.throw(
                        _("Posting Date ({0}) cannot be before Sales Order Date ({1}) for SO {2}")
                        .format(doc.posting_date, sales_order.transaction_date, m.sales_order)
                    )

                if sales_order.custom_transaction_unique_id:
                    doc.custom_transaction_unique_id = sales_order.custom_transaction_unique_id
                    break  

        if not doc.is_new() and doc.custom_transaction_unique_id:
            copy_attachments_to_target(doc.doctype, doc.name, "Sales Order")
