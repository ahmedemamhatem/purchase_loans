import frappe
from frappe import throw, _
from frappe.model.document import Document
from frappe.utils import now
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from purchase_loans.purchase_loans.tasks import update_purchase_loan_request, create_purchase_loan_ledger
from erpnext.setup.utils import get_exchange_rate

class PurchaseLoanRequest(Document):
    """
    Represents a request for a purchase loan. This class includes functionality to 
    validate the loan request, check outstanding amounts, and update the loan request 
    after payments and repayments.
    """
    def on_submit(self):
        """
        Called when the Purchase Loan Request document is submitted. This method updates
        the Purchase Loan Request with the latest aggregate values from the ledger by 
        invoking the `update_purchase_loan_request` function.
        """

        update_purchase_loan_request(self.name)
        
    def after_insert(self):
        if not self.exchange_rate or self.exchange_rate in {0, 1}:
            self.exchange_rate = get_conversion_rate(self)

    def before_validate(self):
        try:
            self.direct_approver = frappe.get_value("Employee", self.employee, "custom_purchase_loan_approver")
        except frappe.DoesNotExistError:
            pass
        

    def validate(self):
        """
        Validates the Purchase Loan Request document by calculating the outstanding 
        amounts and ensuring the necessary configurations are in place for processing 
        loan payments.
        """
        # Fetch the purchase_loan_account from the Company doctype
        self._fetch_company_configuration()

        currency = self.has_value_changed("currency")
        if currency:
            self.exchange_rate = get_conversion_rate(self)
        
        if not self.direct_approver:
            frappe.throw(_("A Purchase Loan Approver is not set in the Employee Profile. Please update the profile with an approver. If you lack the necessary access, kindly refer this matter to the HR team for assistance."))


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
def copy_attachments_to_target(target_doctype, target_docname, source_doctype, source_name):
    """
    Copies all attachments from a source doctype to a target doctype based on a shared Transaction Unique ID.
    Before inserting, it checks if the file is already attached to the target document.

    Args:
        target_doctype (str): The target doctype to attach files to (e.g., "Purchase Invoice").
        target_docname (str): The target document name to attach files to.
        source_doctype (str): The source doctype to fetch attachments from (e.g., "Purchase Order").
        source_name (str): The source document name.

    Raises:
        frappe.ValidationError: If the source document or attachments are not found.
    """
    try:
        # Fetch the target document
        target_doc = frappe.get_doc(target_doctype, target_docname)

        # Find the source documents with the same Transaction Unique ID
        source_docs = frappe.get_all(
            source_doctype,
            filters={"name": source_name},
            fields=["name"]
        )

        if not source_docs:
            frappe.throw(
                _(f"No {source_doctype} found with the name: {source_name}")
            )

        # Fetch the first matching source document (adjust if multiple matches are expected)
        source_docname = source_docs[0].get("name")

        # Get all attachments linked to the source document
        attachments = frappe.get_all(
            "File",
            filters={"attached_to_doctype": source_doctype, "attached_to_name": source_docname},
            fields=["file_url", "file_name"]
        )

        if not attachments:
            frappe.msgprint(_(f"No attachments found in the related {source_doctype}: {source_docname}"))
            return

        # Attach files to the target document
        for attachment in attachments:
            # Check if the file is already attached to the target document
            existing_attachment = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": target_doctype,
                    "attached_to_name": target_docname,
                    "file_url": attachment["file_url"],
                    "file_name": attachment["file_name"]
                },
                fields=["name"]
            )

            if existing_attachment:
                
                continue  # Skip if file is already attached

            # If file is not attached, add it
            frappe.get_doc({
                "doctype": "File",
                "file_url": attachment["file_url"],
                "file_name": attachment["file_name"],
                "attached_to_doctype": target_doctype,
                "attached_to_name": target_docname
            }).insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Error in copying attachments: {str(e)}")
        frappe.throw(_("An error occurred while copying attachments."))


@frappe.whitelist()
def get_conversion_rate(self):
    company = self.company 
    currency = self.currency
    posting_date = self.posting_date
    # Fetch the company currency
    company_currency = frappe.db.get_value(
        "Company", filters={"name": company}, fieldname="default_currency"
    )
    
    # Fetch the exchange rate
    conversion_rate = get_exchange_rate(currency, company_currency, transaction_date=posting_date)
    
    return conversion_rate or 1


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
    company_record = frappe.get_doc("Company", purchase_loan_request_doc.company)
    custom_allow_payment_beyond_loan_amount = company_record.custom_allow_payment_beyond_loan_amount

    currency = purchase_loan_request_doc.currency 

    # Ensure the payment amount is within the outstanding balance
    if custom_allow_payment_beyond_loan_amount == "No" :
        if payment_amount > (purchase_loan_request_doc.outstanding_amount_from_request + purchase_loan_request_doc.overpaid_repayment_amount):
            frappe.throw(_("Payment amount cannot exceed the outstanding loan amount."))

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
    payment_date = payment_date or now()
    payment_amount = _validate_payment_amount(payment_amount)
    purchase_loan_request = frappe.get_doc("Purchase Loan Request", loan_request)
    company_record = frappe.get_doc("Company", purchase_loan_request.company)

    if company_record.custom_allow_repayment_beyond_loan_amount == "No" :
        if payment_amount > purchase_loan_request.outstanding_amount_from_repayment:
            frappe.throw(_("Repayment amount cannot exceed the outstanding loan amount."))

    _validate_mode_of_payment(mode_of_payment)

    from_account, to_account = _get_account_ids(mode_of_payment, company)
    
    journal_entry = _create_journal_entry(
        purchase_loan_request, payment_amount, company, employee, from_account, to_account, payment_date, is_repayment=True
    )

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

    currency = purchase_loan_request_doc.currency
    exchange_rate = purchase_loan_request_doc.exchange_rate

    account_currency = frappe.db.get_value(
        "Account", filters={"name": to_account}, fieldname="account_currency"
    )
    if account_currency and account_currency != currency:
        frappe.throw(_("Account currency ({}) does not match the loan request currency ({})").format(account_currency, currency))

    payment_amount_in_currency = payment_amount * exchange_rate
    ledger_amount = payment_amount_in_currency
    voucher_type = "Purchase Loan Repayment" if is_repayment else "Purchase Loan Payment"
    journal_entry = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": voucher_type,
        "posting_date": payment_date,
        "custom_purchase_loan_request": purchase_loan_request_doc.name,
        "company": company,
        "multi_currency": 1,
        "user_remark": _("Repayment made for Purchase Loan Request: {}").format(purchase_loan_request_doc.name),
        "accounts": [
            {
                "account": from_account,
                "credit_in_account_currency" if is_repayment else "debit_in_account_currency": payment_amount_in_currency,
                "reference_type": "Purchase Loan Request",  
                "reference_name": purchase_loan_request_doc.name,
                "party_type": "Employee",
                "party": employee
            },
            {
                "account": to_account,
                "account_currency": currency,
                "exchange_rate": exchange_rate,
                "debit_in_account_currency" if is_repayment else "credit_in_account_currency": payment_amount,
                "credit" if is_repayment else "debit": payment_amount_in_currency,
                "reference_type": "Purchase Loan Request",  
                "reference_name": purchase_loan_request_doc.name
            }
        ]
    })
    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()

    copy_attachments_to_target("Journal Entry", journal_entry.name, purchase_loan_request_doc.doctype, purchase_loan_request_doc.name)

    create_purchase_loan_ledger(journal_entry, ledger_amount)
    return journal_entry


