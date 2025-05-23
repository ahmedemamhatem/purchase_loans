import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re



@frappe.whitelist()
def validate_journal_entry(doc, method):
    for x in doc.accounts:
        if x.party_type and x.party:
            if x.party_type == "Employee":
                x.custom_party_full_name = frappe.db.get_value("Employee", x.party, "employee_name") or ""
            elif x.party_type == "Customer":
                x.custom_party_full_name = frappe.db.get_value("Customer", x.party, "customer_name") or ""
            elif x.party_type == "Supplier":
                x.custom_party_full_name = frappe.db.get_value("Supplier", x.party, "supplier_name") or ""
            else:
                x.custom_party_full_name = ""  # Default empty if party_type is not handled



@frappe.whitelist()
def update_purchase_loan_request(purchase_loan_request_name):
    """
    Updates a Purchase Loan Request document with aggregate values from the ledger.

    Given a Purchase Loan Request document name, this function aggregates the total paid and
    total repaid amounts from the ledger and calculates the outstanding and overpaid amounts.
    The Purchase Loan Request document is then updated with the calculated values.

    :param purchase_loan_request_name: The name of the Purchase Loan Request document to update.
    """
    if not purchase_loan_request_name:
        return

    loan_request_doc = frappe.get_doc("Purchase Loan Request", purchase_loan_request_name)

    company_currency = frappe.db.get_value(
        "Company", filters={"name": loan_request_doc.company}, fieldname="default_currency"
    )
    
    if company_currency != loan_request_doc.currency:
        exchange_rate = loan_request_doc.exchange_rate
    else:
        exchange_rate = 1.0

    request_amount = loan_request_doc.request_amount * exchange_rate

    # Aggregate paid and repayment amounts from the ledger
    ledger_totals = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN purchase_loan_payment_type = 'Pay' AND cancelled = 0 THEN amount ELSE 0 END) AS total_paid,
            SUM(CASE WHEN purchase_loan_payment_type = 'RePay' AND cancelled = 0 THEN amount ELSE 0 END) AS total_repaid
        FROM `tabPurchase Loan Ledger`
        WHERE purchase_loan_request = %s
    """, (purchase_loan_request_name), as_dict=True)[0]

    # Ensure totals default to 0 if None
    total_paid = ledger_totals.get('total_paid') or 0
    total_repaid = ledger_totals.get('total_repaid') or 0

    # Calculate overpaid amount
    overpaid_amount = 0.0
    if total_repaid > request_amount:
        overpaid_amount = max(total_repaid - total_paid, 0)

    # Calculate outstanding amounts
    outstanding_from_repayment = max(total_paid - total_repaid, 0)
    outstanding_from_request = max(request_amount - total_paid, 0)
    overpaid_payment_amount = max(total_paid - request_amount, 0)

    # Update the Purchase Loan Request document with calculated values
    frappe.db.sql("""
        UPDATE `tabPurchase Loan Request`
        SET 
            paid_amount_from_request = %s,
            repaid_amount = %s,
            outstanding_amount_from_request = %s,
            outstanding_amount_from_repayment = %s,
            overpaid_payment_amount = %s,
            overpaid_repayment_amount = %s
        WHERE name = %s
    """, (
        total_paid / exchange_rate,
        total_repaid / exchange_rate,
        outstanding_from_request / exchange_rate,
        outstanding_from_repayment / exchange_rate,
        overpaid_payment_amount / exchange_rate,
        overpaid_amount / exchange_rate,
        purchase_loan_request_name
    ))

    # Commit changes to the database
    frappe.db.commit()


@frappe.whitelist()
def cancel_purchase_loan_ledger(doc):
    # Ensure the necessary fields are present
    """
    Cancels a Purchase Loan Ledger entry. This is a whitelisted function called
    by a hook on a custom doctype. It takes a doc object as argument, and
    requires the doc.name to be present. It then gets the Purchase Loan Ledger
    record linked to the doc and updates the cancelled field to 1.
    """
    if not doc.name:
        frappe.throw("Document name is required.")
    
    # Get the Purchase Loan Ledger record linked to the doc
    ledger_entry = frappe.get_all("Purchase Loan Ledger", filters={
        "purchase_loan_request": doc.custom_purchase_loan_request,
        "reference_name": doc.name
    })

    if ledger_entry:
        # Update the cancelled field to 1
        frappe.db.set_value("Purchase Loan Ledger", ledger_entry[0].name, "cancelled", 1)
        
        # Commit the transaction
        frappe.db.commit()

@frappe.whitelist()
def create_purchase_loan_ledger(doc, ledger_amount):
    # Create a new Purchase Loan Ledger entry
    """
    Creates a new entry in the Purchase Loan Ledger based on the provided document.
    Determines the payment type (Pay or RePay) from the voucher type, calculates the
    paid amount, and records the necessary details such as employee, company, and 
    posting date into the ledger. The new ledger entry is then inserted into the database.
    
    Args:
        doc (Document): The document containing details needed for creating the 
        Purchase Loan Ledger entry, including voucher type, custom purchase loan request, 
        employee, company, and posting date.
    """

    loan_request_doc = frappe.get_doc("Purchase Loan Request", doc.custom_purchase_loan_request)
    purchase_loan_payment_type = "Pay" if doc.voucher_type =="Purchase Loan Payment" else "RePay"
    paid_amount = ledger_amount
    ledger_entry = frappe.get_doc({
        "doctype": "Purchase Loan Ledger",
        "purchase_loan_request": loan_request_doc.name,
        "reference_name": doc.name,  
        "purchase_loan_payment_type": purchase_loan_payment_type,
        "employee": loan_request_doc.employee,
        "company": doc.company,
        "posting_date": doc.posting_date,
        "amount": paid_amount
    })

    # Insert the record into the database
    ledger_entry.insert()


@frappe.whitelist()
def update_purchase_loan_request_on_submit(doc, method):
    """
    Called on submit of a Purchase Loan Payment, Settlement Invoice, or Settlement Expense.
    Creates a new Purchase Loan Ledger entry and updates the Purchase Loan Request.
    """
    if doc.custom_purchase_loan_request:

        update_purchase_loan_request(doc.custom_purchase_loan_request)




@frappe.whitelist()
def update_purchase_loan_request(purchase_loan_request_name):
    """
    Updates a Purchase Loan Request document with aggregate values from the ledger.

    Given a Purchase Loan Request document name, this function aggregates the total paid and
    total repaid amounts from the ledger and calculates the outstanding and overpaid amounts.
    The Purchase Loan Request document is then updated with the calculated values.

    :param purchase_loan_request_name: The name of the Purchase Loan Request document to update.
    """
    if not purchase_loan_request_name:
        return

    loan_request_doc = frappe.get_doc("Purchase Loan Request", purchase_loan_request_name)

    company_currency = frappe.db.get_value(
        "Company", filters={"name": loan_request_doc.company}, fieldname="default_currency"
    )
    
    if company_currency != loan_request_doc.currency:
        exchange_rate = loan_request_doc.exchange_rate
    else:
        exchange_rate = 1.0

    request_amount = loan_request_doc.request_amount * exchange_rate

    # Aggregate paid and repayment amounts from the ledger
    ledger_totals = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN purchase_loan_payment_type = 'Pay' AND cancelled = 0 THEN amount ELSE 0 END) AS total_paid,
            SUM(CASE WHEN purchase_loan_payment_type = 'RePay' AND cancelled = 0 THEN amount ELSE 0 END) AS total_repaid
        FROM `tabPurchase Loan Ledger`
        WHERE purchase_loan_request = %s
    """, (purchase_loan_request_name), as_dict=True)[0]

    # Ensure totals default to 0 if None
    total_paid = ledger_totals.get('total_paid') or 0
    total_repaid = ledger_totals.get('total_repaid') or 0

    # Calculate overpaid amount
    overpaid_amount = 0.0
    if total_repaid > request_amount:
        overpaid_amount = max(total_repaid - total_paid, 0)

    # Calculate outstanding amounts
    outstanding_from_repayment = max(total_paid - total_repaid, 0)
    outstanding_from_request = max(request_amount - total_paid, 0)
    overpaid_payment_amount = max(total_paid - request_amount, 0)

    # Update the Purchase Loan Request document with calculated values
    frappe.db.sql("""
        UPDATE `tabPurchase Loan Request`
        SET 
            paid_amount_from_request = %s,
            repaid_amount = %s,
            outstanding_amount_from_request = %s,
            outstanding_amount_from_repayment = %s,
            overpaid_payment_amount = %s,
            overpaid_repayment_amount = %s
        WHERE name = %s
    """, (
        total_paid / exchange_rate,
        total_repaid / exchange_rate,
        outstanding_from_request / exchange_rate,
        outstanding_from_repayment / exchange_rate,
        overpaid_payment_amount / exchange_rate,
        overpaid_amount / exchange_rate,
        purchase_loan_request_name
    ))

    # Commit changes to the database
    frappe.db.commit()


@frappe.whitelist()
def update_purchase_loan_request_on_cancel(doc, method):
    """
    Called on cancel of a Purchase Loan Payment, Settlement Invoice, or Settlement Expense.
    Cancels the associated Purchase Loan Ledger entry and updates the Purchase Loan Request.
    If the cancelled document is a Purchase Loan Settlement Invoice, it sets the associated Purchase Invoice to "Overdue"
    and resets the outstanding amount. If it is a Purchase Loan Settlement Expense, it clears the Loan Repayment Other Expenses
    table and resets the total. In both cases, it adjusts the total_repayment_amount in the Purchase Loan Repayment document.
    """
    if doc.custom_purchase_loan_request:
        cancel_purchase_loan_ledger(doc)
        # Fetch the linked Purchase Loan Request document
        purchase_loan_request = frappe.get_doc("Purchase Loan Request", doc.custom_purchase_loan_request)
        total_invoices = 0.0
        total_other_expenses = 0.0
        # Fetch the associated Purchase Loan Repayment document
        purchase_loan_repayment = None
        if doc.voucher_type in ["Purchase Loan Settlement Invoice", "Purchase Loan Settlement Expense"]:
            purchase_loan_repayment = frappe.get_doc("Purchase Loan Repayment", doc.custom_purchase_loan_repayment)
            total_invoices = purchase_loan_repayment.total_invoices

            if doc.voucher_type == "Purchase Loan Settlement Invoice":
                # Adjust outstanding and repaid amounts
                purchase_loan_repayment_invoice_name = frappe.db.get_value(
                        "Purchase Loan Repayment Invoices",
                        filters={"purchase_invoice": doc.custom_row_name},
                        fieldname="name"
                    )
                if purchase_loan_repayment_invoice_name:
                    # Fetch the document for further processing
                    purchase_loan_repayment_invoice = frappe.get_doc(
                        "Purchase Loan Repayment Invoices",
                        purchase_loan_repayment_invoice_name
                    )
                    purchase_invoice = purchase_loan_repayment_invoice.purchase_invoice
                    outstanding_amount = purchase_loan_repayment_invoice.outstanding_amount
                    # Update invoices to "Overdue" and reset outstanding amounts
                    frappe.db.set_value("Purchase Invoice", doc.custom_row_name, {
                        "status": "Overdue",
                        "outstanding_amount": outstanding_amount
                    })
                    total_invoices -= outstanding_amount
                    purchase_loan_repayment.total_invoices = total_invoices
                    

            elif doc.voucher_type == "Purchase Loan Settlement Expense":
                # Sum and clear other expenses
                total_other_expenses = sum(row.amount for row in purchase_loan_repayment.loan_repayment_other_expenses)
                
                # Clear the `loan_repayment_other_expenses` table and reset total
                purchase_loan_repayment.loan_repayment_other_expenses = []
                purchase_loan_repayment.total_other_expenses = 0
                
                frappe.msgprint(_("Cleared Loan Repayment Other Expenses table for settlement expense cancellation."))

            # Adjust total_repayment_amount by subtracting the combined totals
            purchase_loan_repayment.total_repayment_amount -= (total_invoices + total_other_expenses)

            # Save changes to the Purchase Loan Repayment document
            purchase_loan_repayment.save(ignore_permissions=True)
            purchase_loan_repayment.reload()


        update_purchase_loan_request(doc.custom_purchase_loan_request)
        # Final success message
        frappe.msgprint(_("Purchase Loan Request '{0}' updated successfully.").format(purchase_loan_request.name))
