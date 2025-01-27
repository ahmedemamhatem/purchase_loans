import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re

@frappe.whitelist()
def validate_payment_entry(doc, method):
    try:
        # Return early if there are no references
        if not doc.references:
            return
        
        # Initialize variables
        total_allocated_amount = 0
        total_outstanding_amount_net = 0
        custom_transaction_unique_id = None

        # Iterate through each reference
        for ref in doc.references:
            # Fetch the referenced document (e.g., Purchase Invoice or Sales Invoice)
            invoice = frappe.get_doc(ref.reference_doctype, ref.reference_name)
            currency = invoice.currency

            # Determine the account to validate
            account = None
            if ref.reference_doctype == "Purchase Invoice":
                account = invoice.credit_to
            elif ref.reference_doctype == "Sales Invoice":
                account = invoice.debit_to

            # Fetch account currency if the account exists
            if account:
                account_doc = frappe.get_doc("Account", account)
                account_currency = account_doc.account_currency
            else:
                account_currency = None

            # Update total outstanding amount
            total_outstanding_amount = invoice.outstanding_amount

            # Assign the custom_transaction_unique_id if present in the first matched invoice
            if invoice.custom_transaction_unique_id and not custom_transaction_unique_id:
                custom_transaction_unique_id = invoice.custom_transaction_unique_id
                doc.custom_transaction_unique_id = custom_transaction_unique_id

            # Validate currency for "Pay" payment type
            if doc.payment_type == "Pay" and doc.paid_from_account_currency != currency:
                frappe.throw(
                    _("Currency mismatch: The currency of the payment account does not match the currency of the invoice for {0}.")
                    .format(ref.reference_name)
                )

            # Calculate the allocated amount based on the account currency and update the total
            ref.allocated_amount = (
                doc.paid_amount * doc.source_exchange_rate if account_currency != currency else doc.paid_amount
            )
            total_allocated_amount += ref.allocated_amount
            total_outstanding_amount_net += total_outstanding_amount

        # Update the total allocated amount in the Payment Entry
        doc.total_allocated_amount = total_allocated_amount

        # Optional validation to prevent overpayment
        if doc.total_allocated_amount > total_outstanding_amount_net:
            frappe.throw(
                _("Paid amount exceeds the total outstanding amount for the referenced invoices.")
            )

    except Exception as e:
        # Log the error and raise a generic error message
        frappe.log_error(f"Error in Payment Entry {doc.name}: {str(e)}")
