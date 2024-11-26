import frappe
from frappe import _
from frappe.model.document import Document

class PurchaseLoanRepayment(Document):
	
	def on_submit(self):
		"""Creates journal entries upon submission for expenses and invoices."""
		self._validate_repayment_amount()
  
		# Create journal entry for other expenses if applicable
		if self.total_other_expenses > 0:
			self._create_journal_entry_for_expenses()

		# Create journal entry for invoices if there are rows in purchase_loan_repayment_invoices
		if self.purchase_loan_repayment_invoices:
			self._create_journal_entry_for_invoices()

		# Update the Purchase Loan Request with the repaid amount and outstanding amount
		self._update_purchase_loan_request()

	def _create_journal_entry_for_expenses(self):
		"""Creates a journal entry for other expenses in the loan repayment."""
		journal_entry = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Purchase Loan Settlement Expense",
			"posting_date": frappe.utils.nowdate(),
			"custom_purchase_loan_request": self.purchase_loan_request,
			"custom_purchase_loan_repayment": self.name,
			"company": self.company,
			"user_remark": _("Repayment made for Purchase Loan Request: {}").format(self.purchase_loan_request),
			"accounts": [
				{
					"account": self.default_account,
					"party_type": "Employee",
					"party": self.employee,
					"credit_in_account_currency": self.total_other_expenses
				}
			]
		})

		# Add debit entries for each row in `loan_repayment_other_expenses`
		for row in self.loan_repayment_other_expenses:
			journal_entry.append("accounts", {
				"account": row.account,
				"debit_in_account_currency": row.amount
			})

		# Insert and submit the journal entry in one go
		journal_entry.insert(ignore_permissions=True)
		journal_entry.submit()

		self.db_update()

	def _create_journal_entry_for_invoices(self):
		"""Creates a journal entry for each invoice in the loan repayment and links each entry to a Purchase Invoice."""
		# List to hold all journal entries to be created in one batch
		journal_entries = []

		# Loop through each row in purchase_loan_repayment_invoices to create individual journal entries
		for row in self.purchase_loan_repayment_invoices:
			# Fetch the purchase invoice document to get `credit_to` and `outstanding_amount`
			purchase_invoice = frappe.get_doc("Purchase Invoice", row.purchase_invoice)

			# Create a journal entry for the current invoice
			journal_entry = frappe.get_doc({
				"doctype": "Journal Entry",
				"voucher_type": "Purchase Loan Settlement Invoice",
				"posting_date": frappe.utils.nowdate(),
				"custom_purchase_loan_request": self.purchase_loan_request,
				"custom_purchase_loan_repayment": self.name,
				"company": self.company,
				"user_remark": _("Repayment made for Purchase Loan Request: {}").format(self.purchase_loan_request),
				"accounts": [
					{
						"account": self.default_account,
						"party_type": "Employee",
						"party": self.employee,
						"credit_in_account_currency": purchase_invoice.outstanding_amount,
						"reference_type": "Purchase Loan Request",
						"reference_name": self.purchase_loan_request
					},
					{
						"account": purchase_invoice.credit_to,
						"party_type": "Supplier",
						"party": purchase_invoice.supplier,
						"debit_in_account_currency": purchase_invoice.outstanding_amount,
						"against_voucher_type": "Purchase Invoice",
						"against_voucher": row.purchase_invoice,
						"reference_type": "Purchase Loan Request",
						"reference_name": self.purchase_loan_request
					}
				]
			})

			# Add the journal entry to the list
			journal_entries.append(journal_entry)

			# Set the outstanding amount to zero and mark the invoice as paid
			purchase_invoice.db_set("status", "Paid")
			purchase_invoice.db_set("outstanding_amount", 0)

		# Insert and submit all journal entries in one go
		for journal_entry in journal_entries:
			journal_entry.insert(ignore_permissions=True)
			journal_entry.submit()

		# Update the loan repayment document to reflect the changes
		self.db_update()

	def _update_purchase_loan_request(self):
		"""Updates the Purchase Loan Request with the repaid amount and outstanding amount."""
		purchase_loan_request = frappe.get_doc("Purchase Loan Request", self.purchase_loan_request)
		purchase_loan_request.repaid_amount += self.total_repayment_amount
		purchase_loan_request.outstanding_amount_from_repayment = purchase_loan_request.paid_amount_from_request - purchase_loan_request.repaid_amount
		purchase_loan_request.save()
		purchase_loan_request.reload()

	def validate(self):
		"""Validates duplicate entries and repayment constraints."""
		self._validate_duplicate_entries()
		self._sum_outstanding_and_expense_amounts()
		

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

		if self.total_repayment_amount > self.outstanding_amount:
			frappe.throw(_("Repayment amount cannot exceed the outstanding loan amount."))
