import frappe
from frappe import _
from frappe.model.document import Document
from purchase_loans.purchase_loans.tasks import create_purchase_loan_ledger
import logging


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
        if not self.is_new():

            self._set_direct_approver()

        # Create journal entry for other expenses if applicable
        if self.total_other_expenses > 0:
            self._create_journal_entry_for_expenses()

        # Create journal entry for invoices if there are rows in purchase_loan_repayment_invoices
        if self.purchase_loan_repayment_invoices:
            self._create_journal_entry_for_invoices()

    @frappe.whitelist()
    def _set_direct_approver(self):
        """Fetch and set the direct approver for the Purchase Order and share the document if not already shared."""
        if not self.direct_approver:
            return

        if not frappe.db.exists("DocShare", {"doctype": self.doctype, "docname": self.name, "user": self.direct_approver}):
            frappe.share.add(self.doctype, self.name, self.direct_approver, read=1, write=1, submit=1)

    @frappe.whitelist()
    def _copy_attachments_to_target(self, target_doctype, target_docname, source_doctype, source_name):
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
        purchase_loan_request_doc.reload()
        self._copy_attachments_to_target("Journal Entry", journal_entry.name, self.doctype, self.name)

        

    def _create_journal_entry_for_invoices(self):
        """Creates journal entries for loan repayment invoices and handles exchange differences efficiently."""
        
        journal_entries, exchange_difference_entries = [], []

        # Fetch loan request details
        purchase_loan_request = frappe.get_doc("Purchase Loan Request", self.purchase_loan_request)
        company = purchase_loan_request.company
        currency, exchange_rate = purchase_loan_request.currency, purchase_loan_request.exchange_rate

        # Fetch company default currency and exchange gain/loss account
        company_details = frappe.db.get_value(
            "Company", company, ["default_currency", "exchange_gain_loss_account"], as_dict=True
        )

        if not company_details.default_currency:
            frappe.throw(_("Default currency is not set for the company {0}. Please configure it in Company settings.")
                        .format(company))

        if not company_details.exchange_gain_loss_account:
            frappe.throw(_("Exchange Gain or Loss Account is not set for the company {0}. Please configure it in Company settings.")
                        .format(company))

        for row in self.purchase_loan_repayment_invoices:
            purchase_invoice = frappe.get_doc("Purchase Invoice", row.purchase_invoice)
            purchase_invoice_currency = purchase_invoice.currency
            purchase_invoice_exchange_rate = purchase_invoice.conversion_rate

            # Calculate repayment amounts and exchange difference
            amount_to_supplier = row.outstanding_amount * purchase_invoice_exchange_rate
            amount_from_loan = row.outstanding_amount * exchange_rate
            exchange_difference = amount_from_loan - amount_to_supplier

            # Create main journal entry
            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Purchase Loan Settlement Invoice",
                "posting_date": frappe.utils.nowdate(),
                "custom_purchase_loan_request": self.purchase_loan_request,
                "custom_purchase_loan_repayment": self.name,
                "company": company,
                "multi_currency": 1,
                "custom_row_name": row.purchase_invoice,
                "user_remark": _("Repayment for Purchase Loan Request: {0}").format(self.purchase_loan_request),
                "accounts": [
                    {
                        "account": self.default_account,
                        "party_type": "Employee",
                        "party": self.employee,
                        "credit_in_account_currency": amount_to_supplier,
                        "credit": amount_to_supplier,
                        "reference_type": "Purchase Loan Request",
                        "reference_name": self.purchase_loan_request
                    },
                    {
                        "account": purchase_invoice.credit_to,
                        "party_type": "Supplier",
                        "party": purchase_invoice.supplier,
                        "account_currency": purchase_invoice_currency,
                        "exchange_rate": purchase_invoice_exchange_rate,
                        "debit_in_account_currency": amount_to_supplier,
                        "debit": amount_to_supplier / purchase_invoice_exchange_rate,
                        "against_voucher_type": "Purchase Invoice",
                        "against_voucher": row.purchase_invoice,
                        "reference_type": "Purchase Loan Request",
                        "reference_name": self.purchase_loan_request
                    }
                ]
            })
            journal_entries.append(journal_entry)

            # Handle exchange difference if applicable
            if exchange_difference:
                exchange_difference_entry = frappe.get_doc({
                    "doctype": "Journal Entry",
                    "voucher_type": "Exchange Gain Or Loss",
                    "posting_date": frappe.utils.nowdate(),
                    "custom_purchase_loan_request": self.purchase_loan_request,
                    "custom_purchase_loan_repayment": self.name,
                    "company": company,
                    "multi_currency": 1,
                    "user_remark": _("Exchange Difference Adjustment for Purchase Loan Request: {0}").format(self.purchase_loan_request),
                    "accounts": [
                        {
                            "account": company_details.exchange_gain_loss_account,
                            "debit_in_account_currency" if exchange_difference > 0 else "credit_in_account_currency": abs(exchange_difference),
                            "debit" if exchange_difference > 0 else "credit": abs(exchange_difference),
                            "reference_type": "Purchase Loan Request",
                            "reference_name": self.purchase_loan_request
                        },
                        {
                            "account": self.default_account,
                            "party_type": "Employee",
                            "party": self.employee,
                            "credit_in_account_currency" if exchange_difference > 0 else "debit_in_account_currency": abs(exchange_difference),
                            "credit" if exchange_difference > 0 else "debit": abs(exchange_difference),
                            "reference_type": "Purchase Loan Request",
                            "reference_name": self.purchase_loan_request
                        }
                    ]
                })
                exchange_difference_entries.append(exchange_difference_entry)

            # Mark invoice as paid in bulk update
            purchase_invoice.db_set({"status": "Paid", "outstanding_amount": 0})

        # Insert and submit all journal entries in bulk
        for journal_entry in journal_entries:
            journal_entry.insert(ignore_permissions=True)
            journal_entry.submit()
            create_purchase_loan_ledger(journal_entry, amount_from_loan)
            self._copy_attachments_to_target("Journal Entry", journal_entry.name, self.doctype, self.name)

        for exchange_difference_entry in exchange_difference_entries:
            exchange_difference_entry.insert(ignore_permissions=True)
            exchange_difference_entry.submit()
            self._copy_attachments_to_target("Journal Entry", exchange_difference_entry.name, self.doctype, self.name)

        # Update loan repayment document
        self.db_update()
        purchase_loan_request.reload()



    def validate(self):
        
        """Validates duplicate entries and repayment constraints."""

        self._validate_duplicate_entries()
        for row in self.purchase_loan_repayment_invoices:
            # Fetch party and invoice details
            party_account = row.party_account
            party_currency = row.party_currency
            purchase_invoice = frappe.get_doc("Purchase Invoice", row.purchase_invoice)
            purchase_invoice_currency = purchase_invoice.currency
            purchase_invoice_exchange_rate = purchase_invoice.conversion_rate
            if party_currency != purchase_invoice_currency :
                row.outstanding_amount = purchase_invoice.outstanding_amount / purchase_invoice_exchange_rate

        self._sum_outstanding_and_expense_amounts()
        self._validate_currency()

        
        """Updates the Purchase Loan Repayment document with amounts from the linked Purchase Loan Request."""
        purchase_loan_request = frappe.get_doc("Purchase Loan Request", self.purchase_loan_request, fields=["request_amount", "outstanding_amount_from_repayment"])
        self.loan_amount = purchase_loan_request.request_amount
        self.outstanding_amount = purchase_loan_request.outstanding_amount_from_repayment
        outstanding_diff = (self.outstanding_amount or 0.0) - (self.total_repayment_amount or 0.0)
        self.outstanding_from_loan = max(outstanding_diff, 0)
        self.overpayment = abs(outstanding_diff) if outstanding_diff < 0 else 0


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
            

