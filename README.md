## Purchase Loan Management Module
This module is designed for managing the purchase loan requests and repayments within an ERPNext-based system. It tracks the loan request, payments made, repayments, and the outstanding amounts. It also supports handling overpayments and adjusting the loan request and repayment amounts.

## Features
Purchase Loan Request Management: Create, track, and manage purchase loan requests, including the requested loan amount.
Ledger Tracking: Tracks payments and repayments, including the type of payment (Pay or RePay).
Outstanding Amount Calculation: Automatically calculates the outstanding loan amount based on payments and repayments.
Overpayment Handling: Supports overpayment of loans, ensuring repayments can exceed the requested amount and properly calculating the overpaid amount.
Repayment Validation: Ensures repayment amounts do not exceed the outstanding loan amount unless explicitly allowed by the company's settings.
Purchase Loan Request Update: Updates the Purchase Loan Request document based on aggregate values from the ledger.


## Usage
1. Creating a Purchase Loan Request
    Go to Purchase Loan Request and create a new document.
    Fill in the required fields such as Request Amount, Employee, and Company.
    Save the document.

2. Tracking Payments
    Payments made towards the loan are recorded in the Purchase Loan Ledger.
    When a payment is made, ensure the payment type is set to Pay.

3. Tracking Repayments
    Repayments are also recorded in the Purchase Loan Ledger, with the payment type set to RePay.
    
4. Updating Purchase Loan Request
    The update_purchase_loan_request function will automatically update the Purchase Loan Request document with the following values:

    Paid Amount From Request: The total paid amount (sum of Pay entries in the ledger).
    Repaid Amount: The total repaid amount (sum of RePay entries in the ledger).
    Outstanding Amount From Request: The remaining outstanding amount after considering the payments.
    Outstanding Amount From Repayment: The remaining amount from the repayment after considering the paid amount.
    Overpaid Repayment Amount: If the repayment exceeds the paid amount, this field tracks the overpaid amount.

5. Repayment Validation
    Repayments are validated to ensure that the repayment amount does not exceed the outstanding loan amount unless explicitly allowed by the company settings (custom_allow_repayment_beyond_loan_amount).

