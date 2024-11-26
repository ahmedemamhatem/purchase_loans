import frappe
from frappe import _

def update_purchase_loan_request_on_cancel(doc, method):
    if doc.custom_purchase_loan_request:
        # Initialize total values for later adjustment
        total_invoices = 0.0
        total_other_expenses = 0.0

        # Fetch the associated Purchase Loan Repayment document
        purchase_loan_repayment = None
        if doc.voucher_type in ["Purchase Loan Settlement Invoice", "Purchase Loan Settlement Expense"]:
            purchase_loan_repayment = frappe.get_doc("Purchase Loan Repayment", doc.custom_purchase_loan_repayment)

        # Fetch the linked Purchase Loan Request document
        purchase_loan_request = frappe.get_doc("Purchase Loan Request", doc.custom_purchase_loan_request)
        adjustment_amount = doc.total_debit or doc.total_credit  # Determine the amount to adjust

        if doc.voucher_type == "Purchase Loan Settlement Invoice":
            # Adjust outstanding and repaid amounts
            purchase_loan_request.repaid_amount -= adjustment_amount
            purchase_loan_request.outstanding_amount_from_repayment += adjustment_amount

            # Update invoices to "Overdue" and reset outstanding amounts
            for row in purchase_loan_repayment.purchase_loan_repayment_invoices:
                frappe.db.set_value("Purchase Invoice", row.purchase_invoice, {
                    "status": "Overdue",
                    "outstanding_amount": row.outstanding_amount
                })
                total_invoices += row.outstanding_amount  # Sum invoice outstanding amounts for adjustment

            # Clear the `purchase_loan_repayment_invoices` table and reset total
            purchase_loan_repayment.purchase_loan_repayment_invoices = []
            purchase_loan_repayment.total_invoices = 0
            frappe.msgprint(_("Cleared Purchase Loan Repayment Invoices table for settlement invoice cancellation."))

        elif doc.voucher_type == "Purchase Loan Settlement Expense":
            # Adjust outstanding and repaid amounts
            purchase_loan_request.repaid_amount -= adjustment_amount
            purchase_loan_request.outstanding_amount_from_repayment += adjustment_amount

            # Sum and clear other expenses
            total_other_expenses = sum(row.amount for row in purchase_loan_repayment.loan_repayment_other_expenses)
            
            # Clear the `loan_repayment_other_expenses` table and reset total
            purchase_loan_repayment.loan_repayment_other_expenses = []
            purchase_loan_repayment.total_other_expenses = 0
            frappe.msgprint(_("Cleared Loan Repayment Other Expenses table for settlement expense cancellation."))

        # Adjust fields for other voucher types
        if doc.voucher_type == "Purchase Loan Repayment":
            purchase_loan_request.repaid_amount -= adjustment_amount
            purchase_loan_request.outstanding_amount_from_repayment += adjustment_amount
            frappe.msgprint(_("Adjusted repaid amount and outstanding repayment for Purchase Loan Repayment."))
        
        elif doc.voucher_type == "Purchase Loan Payment":
            purchase_loan_request.paid_amount_from_request -= adjustment_amount
            purchase_loan_request.outstanding_amount_from_request += adjustment_amount
            purchase_loan_request.outstanding_amount_from_repayment -= adjustment_amount
            frappe.msgprint(_("Adjusted paid amount and outstanding amount from request for Purchase Loan Payment."))

        if purchase_loan_repayment:
            # Adjust total_repayment_amount by subtracting the combined totals
            purchase_loan_repayment.total_repayment_amount -= (total_invoices + total_other_expenses)

            # Save changes to the Purchase Loan Repayment document
            purchase_loan_repayment.save(ignore_permissions=True)
            purchase_loan_repayment.reload()

        # Save changes to the Purchase Loan Request document
        purchase_loan_request.save(ignore_permissions=True)
        purchase_loan_request.reload()

        # Final success message
        frappe.msgprint(_("Purchase Loan Request '{0}' updated successfully.").format(purchase_loan_request.name))
