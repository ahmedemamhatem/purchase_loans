import frappe
from frappe.utils import getdate
from frappe import _
from purchase_loans.purchase_loans.tasks import copy_attachments_to_target

@frappe.whitelist()
def validate_sales_invoice(doc, method):
    if doc.items:
        for m in doc.items:
            # Ensure that sales_order is present
            if m.sales_order:
                # Fetch the Sales Order document
                sales_order = frappe.get_doc("Sales Order", m.sales_order)

                # Validate Posting Date
                if getdate(doc.posting_date) < getdate(sales_order.transaction_date):
                    frappe.throw(
                        _("Sales Invoice Date ({0}) cannot be before Sales Order Date ({1}) for Sales Order {2}.")
                        .format(doc.posting_date, sales_order.transaction_date, m.sales_order)
                    )

                # Check if custom_transaction_unique_id exists in the Sales Order
                if sales_order.custom_transaction_unique_id:
                    # Assign the ID from the Sales Order to the Sales Invoice
                    doc.custom_transaction_unique_id = sales_order.custom_transaction_unique_id
                    break  # Stop the loop as it's assumed to be unique
                else:
                    # Optionally, notify if the ID is missing on the Sales Order
                    frappe.msgprint(
                        _("Custom Transaction Unique ID not found on Sales Order: {0}").format(m.sales_order)
                    )

    if not doc.is_new() and doc.custom_transaction_unique_id:
        copy_attachments_to_target(doc.doctype, doc.name, "Sales Order")
