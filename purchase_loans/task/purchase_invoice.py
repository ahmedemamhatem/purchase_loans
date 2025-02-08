import frappe
from frappe.utils import getdate
from frappe import _
from purchase_loans.purchase_loans.tasks import copy_attachments_to_target

@frappe.whitelist()
def validate_purchase_invoice(doc, method):
    if doc.items:
        for m in doc.items:
            # Ensure that purchase_order is present
            if m.purchase_order:
                # Fetch the Purchase Order document
                purchase_order = frappe.get_doc("Purchase Order", m.purchase_order)

                # Validate Posting Date
                if getdate(doc.posting_date) < getdate(purchase_order.transaction_date):
                    frappe.throw(
                        _("Purchase Invoice Date ({0}) cannot be before Purchase Order Date ({1}) for Purchase Order {2}.")
                        .format(doc.posting_date, purchase_order.transaction_date, m.purchase_order)
                    )

                # Check if custom_transaction_unique_id exists in the Purchase Order
                if purchase_order.custom_transaction_unique_id:
                    # Assign the ID from the Purchase Order to the Purchase Invoice
                    doc.custom_transaction_unique_id = purchase_order.custom_transaction_unique_id
                    break  # Stop the loop as it's assumed to be unique
                else:
                    # Optionally, notify if the ID is missing on the Purchase Order
                    frappe.msgprint(
                        _("Custom Transaction Unique ID not found on Purchase Order: {0}").format(m.purchase_order)
                    )

    if not doc.is_new() and doc.custom_transaction_unique_id:
        copy_attachments_to_target(doc.doctype, doc.name, "Purchase Order")
