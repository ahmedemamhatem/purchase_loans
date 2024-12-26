import frappe
from frappe import _
from frappe.model.document import Document
from purchase_loans.purchase_loans.tasks import create_purchase_loan_ledger

class PurchaseLoanRepayment(Document):
    def on_cancel(self):
        # Fetch all Journal Entries linked to this Purchase Loan Repayment
        """
        Cancels all journal entries linked to this Purchase Loan Repayment and updates the linked Purchase Loan Request.

        Fetches all Journal Entries linked to this Purchase Loan Repayment and triggers cancel for each one.
        This ensures that the Purchase Loan Request is properly updated and that the repayment amount is subtracted from the outstanding amount.
        """
        journal_entries = frappe.get_all(
            "Journal Entry",
            filters={"custom_purchase_loan_repayment": self.name},
            pluck="name"
        )
        
        # Trigger cancel for each Journal Entry
        for je in journal_entries:
            journal_entry_doc = frappe.get_doc("Journal Entry", je)
            if journal_entry_doc.docstatus == 1:  # Ensure the document is submitted
                journal_entry_doc.cancel()
                    
    def on_submit(self):
        """Creates journal entries upon submission for expenses and invoices."""
        self._validate_repayment_amount()
  
        # Create journal entry for other expenses if applicable
        if self.total_other_expenses > 0:
            self._create_journal_entry_for_expenses()

        # Create journal entry for invoices if there are rows in purchase_loan_repayment_invoices
        if self.purchase_loan_repayment_invoices:
            self._create_journal_entry_for_invoices()


    def _create_journal_entry_for_expenses(self):
        """Creates a journal entry for other expenses in the loan repayment."""

        purchase_loan_request_doc = frappe.get_doc("Purchase Loan Request", self.purchase_loan_request)
        currency = purchase_loan_request_doc.currency
        exchange_rate = purchase_loan_request_doc.exchange_rate

        payment_amount_in_currency = self.total_other_expenses * exchange_rate
        ledger_amount = payment_amount_in_currency
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Purchase Loan Settlement Expense",
            "posting_date": frappe.utils.nowdate(),
            "custom_purchase_loan_request": self.purchase_loan_request,
            "custom_purchase_loan_repayment": self.name,
            "company": self.company,
            "multi_currency": 1,
            "user_remark": _("Repayment made for Purchase Loan Request: {}").format(self.purchase_loan_request),
            "accounts": [
                {
                    "account": self.default_account,
                    "party_type": "Employee",
                    "party": self.employee,
                    "credit_in_account_currency": payment_amount_in_currency
                }
            ]
        })

        # Add debit entries for each row in `loan_repayment_other_expenses`
        for row in self.loan_repayment_other_expenses:
            journal_entry.append("accounts", {
                "account": row.account,
                "account_currency": currency,
                "exchange_rate": exchange_rate,
                "debit": row.amount * exchange_rate,
                "debit_in_account_currency": row.amount
            })

        # Insert and submit the journal entry in one go
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        create_purchase_loan_ledger(journal_entry, ledger_amount)
        self.db_update()

    def _create_journal_entry_for_invoices(self):
        """Creates journal entries for loan repayment invoices and handles exchange differences."""
        # Initialize lists for journal entries
        journal_entries = []
        exchange_difference_entries = []

        # Fetch loan request details
        purchase_loan_request_doc = frappe.get_doc("Purchase Loan Request", self.purchase_loan_request)
        currency = purchase_loan_request_doc.currency
        exchange_rate = purchase_loan_request_doc.exchange_rate

        # Fetch default_currency
        company_currency = frappe.db.get_value(
            "Company", filters={"name": purchase_loan_request_doc.company}, fieldname="default_currency"
        )
        if not company_currency:
            frappe.throw(
                _("Default currency is not set for the company {0}. Please configure it in the Company settings.")
                .format(purchase_loan_request_doc.company)
            )

        # Fetch exchange_gain_loss_account
        exchange_gain_loss_account = frappe.db.get_value(
            "Company", purchase_loan_request_doc.company, "exchange_gain_loss_account"
        )
        if not exchange_gain_loss_account:
            frappe.throw(
                _("Exchange Gain or Loss Account is not set for the company {0}. Please configure it in the Company settings.")
                .format(purchase_loan_request_doc.company)
            )



        for row in self.purchase_loan_repayment_invoices:
            # Fetch party and invoice details
            party_account = row.party_account
            party_currency = row.party_currency
            purchase_invoice = frappe.get_doc("Purchase Invoice", row.purchase_invoice)
            purchase_invoice_currency = purchase_invoice.currency
            purchase_invoice_exchange_rate = purchase_invoice.conversion_rate

            if party_currency != purchase_invoice_currency and party_currency == company_currency:
                # Calculate exchange differences for this case
                party_amount_in_currency = row.outstanding_amount / purchase_invoice_exchange_rate
                amount_in_loan_currency = party_amount_in_currency * exchange_rate
                exchange_difference = amount_in_loan_currency - row.outstanding_amount 
                amount_in_company_currency = row.outstanding_amount
                ledger_amount =  amount_in_loan_currency
            elif party_currency == purchase_invoice_currency and party_currency != company_currency:
                # Calculate exchange differences for another case
                party_amount_in_currency = row.outstanding_amount
                amount_in_loan_currency = row.outstanding_amount * exchange_rate
                amount_in_company_currency = row.outstanding_amount * purchase_invoice_exchange_rate
                exchange_difference = amount_in_loan_currency - amount_in_company_currency
                ledger_amount =  amount_in_loan_currency
            else:
                # No exchange difference case
                party_amount_in_currency = row.outstanding_amount
                amount_in_loan_currency = row.outstanding_amount
                exchange_difference = 0
                amount_in_company_currency = row.outstanding_amount
                ledger_amount =  row.outstanding_amount

            # Create main journal entry
            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Purchase Loan Settlement Invoice",
                "posting_date": frappe.utils.nowdate(),
                "custom_purchase_loan_request": self.purchase_loan_request,
                "custom_purchase_loan_repayment": self.name,
                "company": self.company,
                "multi_currency": 1,
                "custom_row_name": row.purchase_invoice,
                "user_remark": _("Repayment made for Purchase Loan Request: {}").format(self.purchase_loan_request),
                "accounts": [
                    {
                        "account": self.default_account,
                        "party_type": "Employee",
                        "party": self.employee,
                        "credit_in_account_currency": amount_in_company_currency,
                        "credit": amount_in_company_currency,
                        "reference_type": "Purchase Loan Request",
                        "reference_name": self.purchase_loan_request
                    },
                    {
                        "account": purchase_invoice.credit_to,
                        "party_type": "Supplier",
                        "party": purchase_invoice.supplier,
                        "account_currency": party_currency,
                        "exchange_rate": purchase_invoice_exchange_rate,
                        "debit_in_account_currency": party_amount_in_currency,
                        "debit": amount_in_company_currency,
                        "against_voucher_type": "Purchase Invoice",
                        "against_voucher": row.purchase_invoice,
                        "reference_type": "Purchase Loan Request",
                        "reference_name": self.purchase_loan_request
                    }
                ]
            })
            journal_entries.append(journal_entry)

            # Handle exchange difference if present
            if exchange_difference != 0:
                exchange_difference_entry = frappe.get_doc({
                    "doctype": "Journal Entry",
                    "voucher_type": "Exchange Gain Or Loss",
                    "posting_date": frappe.utils.nowdate(),
                    "custom_purchase_loan_request": self.purchase_loan_request,
                    "custom_purchase_loan_repayment": self.name,
                    "company": self.company,
                    "multi_currency": 1,
                    "user_remark": _("Exchange Difference Adjustment for Purchase Loan Request: {}").format(self.purchase_loan_request),
                    "accounts": [
                        {
                            "account": exchange_gain_loss_account,
                            "debit_in_account_currency" if exchange_difference > 0 else "credit_in_account_currency": abs(exchange_difference),
                            "debit" if exchange_difference > 0 else "credit": abs(exchange_difference),
                            "reference_type": "Purchase Loan Request",
                            "reference_name": self.purchase_loan_request
                        },
                        {
                            "account": self.default_account,
                            "credit_in_account_currency" if exchange_difference > 0 else "debit_in_account_currency": abs(exchange_difference),
                            "credit" if exchange_difference > 0 else "debit": abs(exchange_difference),
                            "reference_type": "Purchase Loan Request",
                            "reference_name": self.purchase_loan_request
                        }
                    ]
                })
                exchange_difference_entries.append(exchange_difference_entry)

            # Mark invoice as paid
            purchase_invoice.db_set("status", "Paid")
            purchase_invoice.db_set("outstanding_amount", 0)

        # Insert and submit journal entries
        for journal_entry in journal_entries:
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            create_purchase_loan_ledger(journal_entry, ledger_amount)

        for exchange_difference_entry in exchange_difference_entries:
            exchange_difference_entry.insert(ignore_permissions=True)
            exchange_difference_entry.submit()

        # Update loan repayment document
        self.db_update()



    def validate(self):
        """Validates duplicate entries and repayment constraints."""
        self._validate_duplicate_entries()
        self._sum_outstanding_and_expense_amounts()
        self._validate_currency()
        

    def _validate_duplicate_entries(self):
        """Check for duplicate entries in invoices and expenses tables."""
        # Validate duplicates in 'purchase_loan_repayment_invoices'
        invoice_ids = set()
        for row in self.purchase_loan_repayment_invoices:
            if row.purchase_invoice in invoice_ids:
                frappe.throw(_("Invoice '{0}' has already been added.".format(row.purchase_invoice)))
            invoice_ids.add(row.purchase_invoice)
        
        # Validate duplicates in 'loan_repayment_other_expenses'
        other_expenses = set()
        for row in self.loan_repayment_other_expenses:
            if row.other_expenses in other_expenses:
                frappe.throw(_("Expense Type '{0}' has already been added.".format(row.other_expenses)))
            other_expenses.add(row.other_expenses)

    def _sum_outstanding_and_expense_amounts(self):
        """Calculate and set total outstanding and other expenses."""
        self.total_invoices = sum((row.outstanding_amount or 0) for row in self.purchase_loan_repayment_invoices)
        self.total_other_expenses = sum((row.amount or 0) for row in self.loan_repayment_other_expenses)
        self.total_repayment_amount = self.total_invoices + self.total_other_expenses

    def _validate_repayment_amount(self):
        """Ensure repayment does not exceed outstanding loan amount."""
        
        if self.total_repayment_amount <= 0:
            frappe.throw(_("Repayment amount must be greater than zero."))

        # Fetch company record and check the custom setting
        company_record = frappe.get_doc("Company", self.company)
        custom_allow_repayment_beyond_loan_amount = company_record.custom_allow_repayment_beyond_loan_amount

        # Check if repayment exceeds outstanding amount and handle based on company setting
        if self.total_repayment_amount > self.outstanding_amount and custom_allow_repayment_beyond_loan_amount == "No":
            frappe.throw(_("Repayment amount cannot exceed the outstanding loan amount."))

    def _validate_currency(self):
        currency = self.loan_currency
        if self.loan_repayment_other_expenses:
            for row in self.loan_repayment_other_expenses:
                if row.currency != currency:
                    frappe.throw(_("Currency ({}) does not match the loan request currency ({})").format(row.currency, currency))
            
        if self.purchase_loan_repayment_invoices:
            for row in self.purchase_loan_repayment_invoices:
                if row.currency != currency:
                    frappe.throw(_("Currency ({}) does not match the loan request currency ({})").format(row.currency, currency))
            

