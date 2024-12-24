# Purchase Loan Management Module

The **Purchase Loan Management Module** provides a comprehensive system for handling employee purchase loans, repayments, and their tracking within an ERPNext-based environment. This module is tailored for businesses needing accurate loan tracking, validation, and reconciliation functionalities.

## Functional Overview

### 1. Purchase Loan Request
- **Purpose**: Acts as the primary document for recording and managing purchase loan requests.
- **Key Features**:
  - Specify the requested loan amount, employee, and associated company.
  - Tracks all loan-related payments and repayments through automatic updates.

### 2. Loan Payment Tracking
- **Purpose**: Enables recording of loan disbursements.
- **How It Works**:
  - Payments are logged in the Purchase Loan Ledger with the type set to "Pay."
  - The total paid amount is automatically aggregated and reflected in the Purchase Loan Request.
  - Validates that payments do not exceed the loan request amount unless explicitly allowed.

### 3. Loan Repayment Management
- **Purpose**: Records repayments made against the loan.
- **Key Features**:
  - Repayments are logged in the Purchase Loan Ledger with the type set to "RePay."
  - Automatically calculates the outstanding amount after repayments.
  - Tracks overpayments if repayments exceed the loan amount.

### 4. Ledger Management
- **Purpose**: Serves as the central repository for all loan-related financial activities.
- **Key Features**:
  - Tracks every transaction (payment or repayment) with a detailed breakdown.
  - Validates that ledger entries are properly categorized as "Pay" or "RePay."
  - Supports cancellation of ledger entries, ensuring they are excluded from calculations.

### 5. Outstanding and Overpayment Calculations
- **Outstanding Amount From Request**:
  - Represents the remaining unpaid portion of the loan.
  - Automatically updated based on the total paid amount.
- **Outstanding Amount From Repayment**:
  - Represents the remaining unpaid balance after considering repayments.
  - Ensures any overpayment is accurately tracked.
- **Overpaid Repayment Amount**:
  - Tracks the excess amount paid over the total loan amount.

### 6. Repayment Validation
- **Purpose**: Prevents errors during repayment.
- **Features**:
  - Ensures repayments do not exceed the outstanding loan amount unless explicitly allowed.
  - Allows customization at the company level to enable or disable repayments beyond loan amounts.

## Functional Flow

### Loan Request
1. Employee submits a loan request with the required amount.
2. The Purchase Loan Request document is created and tracks all related activities.

### Payment Disbursement
1. Payments made by the company are logged in the Purchase Loan Ledger.
2. The ledger automatically updates the Purchase Loan Request document with the total paid amount.

### Repayment
1. Repayments are recorded in the Purchase Loan Ledger.
2. Outstanding and overpaid amounts are calculated in real-time and reflected in the Purchase Loan Request.

### Validation
1. Each repayment is validated to ensure compliance with company policies.
2. Overpayments are tracked if enabled.

### Adjustments and Cancellation
1. Users can cancel individual ledger entries, and the system recalculates the totals.

## Business Scenarios Supported

### Scenario 1: Standard Loan Repayment
- **Example**: An employee requests a loan of $5,000. Payments of $3,000 are disbursed, and the employee repays $2,000.
- **System Behavior**:
  - Outstanding amount: $3,000 (from request).
  - Repayment tracked: $2,000.
  - Overpaid amount: $0.

### Scenario 2: Overpayment
- **Example**: An employee repays $6,000 against a $5,000 loan request.
- **System Behavior**:
  - Outstanding amount: $0.
  - Overpaid amount: $1,000.

### Scenario 3: Partial Payments
- **Example**: A company disburses payments in multiple installments (e.g., $2,000, then $1,000).
- **System Behavior**:
  - Total paid: $3,000.
  - Outstanding amount: Adjusted dynamically based on payments.

### Scenario 4: Ledger Entry Cancellation
- **Example**: A payment ledger entry is canceled.
- **System Behavior**:
  - The total paid amount is recalculated, and the outstanding amount is adjusted.

## Additional Information

### Modules and Documents
- **Purchase Loan Request**: The central document for managing loan requests.
- **Purchase Loan Ledger**: Tracks all payments and repayments with detailed breakdowns.
- **Purchase Loan Repayment**: Records detailed repayment plans and their execution.
- **Purchase Loan Report**: Provides detailed analytics and summaries of loan activities.
- **Company**: Custom settings at the company level for repayment validation.

