import frappe
from frappe import throw, _
from frappe.model.document import Document
from frappe.utils import now
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

class PurchaseLoanRequest(Document):
    """
    Represents a request for a purchase loan. This class includes functionality to 
    validate the loan request, check outstanding amounts, and update the loan request 
    after payments and repayments.
    """
    def validate(self):
        """
        Validates the Purchase Loan Request document by calculating the outstanding 
        amounts and ensuring the necessary configurations are in place for processing 
        loan payments.
        """

        
        # Fetch the purchase_loan_account from the Company doctype
        self._fetch_company_configuration()
        

    def _fetch_company_configuration(self):
        """
        Fetches purchase loan account and validates the request amount against company limits.
        """
        company_record = frappe.get_doc("Company", self.company)
        purchase_loan_account = company_record.custom_purchase_loan_account
        maximum_loan_amount = company_record.custom_maximum_loan_amount

        if maximum_loan_amount > 0 and self.request_amount > maximum_loan_amount:
            frappe.throw(_("Requested loan amount ({}) exceeds the maximum allowed amount ({})").format(self.request_amount, maximum_loan_amount))

        if purchase_loan_account:
            self.default_account = purchase_loan_account
        else:
            frappe.throw(_("Purchase Loan Account not set in the Company for {}").format(self.company))



@frappe.whitelist()
def pay_to_employee(loan_request, company, employee, mode_of_payment, payment_amount, payment_date=None):
    """
    Process a payment to an employee for a purchase loan. This function ensures that 
    the payment amount is valid and within the outstanding balance, creates a journal 
    entry for the payment, and updates the Purchase Loan Request document accordingly.
    """
    _check_user_permissions()
    
    # Set default payment date if not provided
    payment_date = payment_date or now()

    # Validate the payment amount
    payment_amount = _validate_payment_amount(payment_amount)

    purchase_loan_request_doc = frappe.get_doc("Purchase Loan Request", loan_request)


    # Ensure mode of payment is provided
    _validate_mode_of_payment(mode_of_payment)

    # Perform the payment transaction
    from_account_id, to_account_id = _get_account_ids(mode_of_payment, purchase_loan_request_doc.company)

    # Create journal entry
    journal_entry = _create_journal_entry(purchase_loan_request_doc, payment_amount, company, employee, from_account_id, to_account_id, payment_date)
    
    return {
        "Paid_amount": payment_amount,
        "message": _("Payment of {} successfully processed.").format(payment_amount)
    }

@frappe.whitelist()
def create_repay_cash(loan_request, company, employee, mode_of_payment, payment_amount, payment_date=None):
    """
    Create a journal entry for repaying cash, update the Purchase Loan Request, and 
    return the repaid cash amount.
    """
    _check_user_permissions()

    # Set default payment date if not provided
    payment_date = payment_date or now()
    
    # Validate the repay amount
    payment_amount = _validate_payment_amount(payment_amount)
    
    purchase_loan_request = frappe.get_doc("Purchase Loan Request", loan_request)


    # Get account IDs for repayment
    from_account, to_account = _get_account_ids(mode_of_payment, company)

    # Create journal entry for repayment
    journal_entry = _create_journal_entry(purchase_loan_request, payment_amount, company, employee, from_account, to_account, payment_date, is_repayment=True)
    
    
    return {
        "repaid_cash_amount": payment_amount,
        "message": _("Repayment of {} successfully processed.").format(payment_amount)
    }

def _check_user_permissions():
    """
    Validates that the user has the necessary roles to perform the action.
    """
    if not any(role in frappe.get_roles() for role in ["Accounts User", "Accounts Manager"]):
        frappe.throw(_("You do not have permission to make this payment."))

def _validate_payment_amount(payment_amount):
    """
    Validates the payment amount.
    """
    try:
        payment_amount = float(payment_amount)
        if payment_amount <= 0:
            frappe.throw(_("Payment amount must be greater than zero."))
    except ValueError:
        frappe.throw(_("Invalid payment amount. Please enter a numeric value."))
    return payment_amount

def _validate_mode_of_payment(mode_of_payment):
    """
    Ensures that the mode of payment is provided.
    """
    if not mode_of_payment:
        frappe.throw(_("Mode of Payment is required to proceed with the submission."))

def _get_account_ids(mode_of_payment, company):
    """
    Fetches account IDs based on the mode of payment and company.
    """
    from_account = frappe.get_doc("Company", company).custom_purchase_loan_account
    to_account = get_bank_cash_account(mode_of_payment=mode_of_payment, company=company)
    to_account_name = to_account.get('account', '')
    if not from_account or not to_account:
        frappe.throw(_("Invalid accounts provided."))

    return from_account, to_account_name

def _create_journal_entry(purchase_loan_request_doc, payment_amount, company, employee, from_account, to_account, payment_date, is_repayment=False):
    """
    Creates a journal entry for the payment or repayment.
    """
    voucher_type = "Purchase Loan Repayment" if is_repayment else "Purchase Loan Payment"
    journal_entry = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": voucher_type,
        "posting_date": payment_date,
        "custom_purchase_loan_request": purchase_loan_request_doc.name,
        "company": company,
        "user_remark": _("Repayment made for Purchase Loan Request: {}").format(purchase_loan_request_doc.name),
        "accounts": [
            {
                "account": from_account,
                "debit_in_account_currency" if is_repayment else "credit_in_account_currency": payment_amount,
                "reference_type": "Purchase Loan Request",  
                "reference_name": purchase_loan_request_doc.name,
                "party_type": "Employee",
                "party": employee
            },
            {
                "account": to_account,
                "credit_in_account_currency" if is_repayment else "debit_in_account_currency": payment_amount,
                "reference_type": "Purchase Loan Request",  
                "reference_name": purchase_loan_request_doc.name
            }
        ]
    })
    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()
    return journal_entry


