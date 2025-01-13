

frappe.ui.form.on("Purchase Loan Request", {
    onload: function(frm) {
        // Check if the document is not new (not local)
        if (!frm.is_new()) {
            // Call the server-side function to update the request
            frappe.call({
                method: "purchase_loans.purchase_loans.tasks.update_purchase_loan_request",
                args: {
                    purchase_loan_request_name: frm.doc.name
                },
                callback: function(response) {
                    
                }
            });
        }
    }
});


frappe.ui.form.on("Purchase Loan Request", {
    refresh(frm) {
        // Check if the document is submitted (docstatus is 1)
        if (frm.doc.docstatus === 1) {
            // Only display old buttons if the request is not closed (closed === 0)
            if (frm.doc.closed === 0) {
                // Display Payment button if outstanding_amount_from_request > 0 or overpaid_repayment_amount > 0
                if (frm.doc.outstanding_amount_from_request > 0 || frm.doc.overpaid_repayment_amount > 0) {
                    frm.add_custom_button(__('Pay To Employee'), function() {
                        show_payment_dialog(frm);
                    });
                }

                // Display Repay Cash button if repaid_amount < paid_amount_from_request
                if (frm.doc.repaid_amount < frm.doc.paid_amount_from_request) {
                    frm.add_custom_button(__('Repay Cash'), function() {
                        show_repay_cash_dialog(frm);
                    });
                }

                // Display Settlement button only if repaid_amount < paid_amount_from_request
                if (frm.doc.repaid_amount < frm.doc.paid_amount_from_request) {
                    frm.add_custom_button(__('Settlement'), function() {
                        create_settlement(frm);
                    });
                }

                // Display "Close" button if the repaid_amount equals paid_amount_from_request
                if (frm.doc.repaid_amount === frm.doc.paid_amount_from_request) {
                    frm.add_custom_button(__('Close'), function() {
                        frappe.confirm(
                            __('Are you sure you want to close this request?'),
                            function() {
                                // Update closed field to 1 (closed)
                                frappe.call({
                                    method: 'frappe.client.set_value',
                                    args: {
                                        doctype: 'Purchase Loan Request',
                                        name: frm.doc.name,
                                        fieldname: 'closed',
                                        value: 1
                                    },
                                    callback: function() {
                                        frm.reload_doc(); // Reload the form to reflect changes
                                    }
                                });
                            }
                        );
                    });
                }
            } else {
                // Display "Reopen" button only for System Manager role
                if (frappe.user_roles.includes('System Manager')) {
                    frm.add_custom_button(__('Reopen'), function() {
                        frappe.confirm(
                            __('Are you sure you want to reopen this request?'),
                            function() {
                                // Update closed field to 0 (reopen)
                                frappe.call({
                                    method: 'frappe.client.set_value',
                                    args: {
                                        doctype: 'Purchase Loan Request',
                                        name: frm.doc.name,
                                        fieldname: 'closed',
                                        value: 0
                                    },
                                    callback: function() {
                                        frm.reload_doc(); // Reload the form to reflect changes
                                    }
                                });
                            }
                        );
                    });
                }
            }
        }
    }
});




function show_payment_dialog(frm) {
    frappe.prompt([
        {
            label: 'Mode of Payment',
            fieldname: 'mode_of_payment',
            fieldtype: 'Link',
            options: 'Mode of Payment', // Link to Mode of Payment doctype
            filters: { enabled: 1 },   // Only show enabled modes of payment
            reqd: 1
        },
        {
            label: 'Payment Amount',
            fieldname: 'payment_amount',
            fieldtype: 'Float', // Use Float for numeric input
            reqd: 1,
            default: frm.doc.outstanding_amount_from_request + frm.doc.overpaid_repayment_amount // Default payment amount as outstanding amount
        },
        {
            label: 'Payment Date',
            fieldname: 'payment_date',
            fieldtype: 'Date',
            reqd: 1,
            default: frappe.datetime.get_today() // Default to today's date
        }
    ], function(values) {
        // Show confirmation dialog before proceeding
        frappe.confirm(
            __('Are you sure you want to proceed with the payment of {0} on {1}?',
              [values.payment_amount, values.payment_date]),
            function() {
                // Call the function to handle the payment upon confirmation
                pay_to_employee(frm, values.mode_of_payment, values.payment_amount, values.payment_date);
            },
            function() {
                frappe.msgprint(__('Payment canceled.'));
            }
        );
    }, 'Payment', 'Pay');
}

// Function to handle the payment
function pay_to_employee(frm, mode_of_payment, payment_amount, payment_date) {
    frappe.call({
        method: "purchase_loans.purchase_loans.doctype.purchase_loan_request.purchase_loan_request.pay_to_employee",
        args: {
            loan_request: frm.doc.name,
            company: frm.doc.company,
            employee: frm.doc.employee,
            mode_of_payment: mode_of_payment,
            payment_amount: payment_amount,
            payment_date: payment_date
        },
        callback: function(response) {
            if (response.message) {
                frappe.msgprint(__('Payment to employee successfully recorded.'));
                frm.reload_doc();
            }
        }
    });
}




// Function for creating Settlement
function create_settlement(frm) {
    // Check if a Purchase Loan Repayment with the same purchase_loan_request exists in draft status
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Purchase Loan Repayment",
            filters: {
                purchase_loan_request: frm.doc.name,
                docstatus: 0 // Draft status
            },
            fields: ["name"]
        },
        callback: function(response) {
            if (response.message && response.message.length > 0) {
                // If a draft exists, redirect to the existing record
                frappe.set_route('Form', 'Purchase Loan Repayment', response.message[0].name);
                
            } else {
                // No draft record exists, proceed with creation
                frappe.call({
                    method: "frappe.client.insert",
                    args: {
                        doc: {
                            doctype: "Purchase Loan Repayment",
                            employee: frm.doc.employee,
                            loan_request: frm.doc.name,
                            loan_amount: frm.doc.paid_amount_from_request,
                            outstanding_amount: frm.doc.outstanding_amount_from_repayment,
                            company: frm.doc.company,
                            direct_approver: frm.doc.direct_approver,
                            direct_approver_name: frm.doc.direct_approver_name,
                            default_account: frm.doc.default_account,
                            purchase_loan_request: frm.doc.name
                        }
                    },
                    callback: function(response) {
                        frappe.set_route('Form', 'Purchase Loan Repayment', response.message.name);
                    }
                });
            }
        }
    });
}



// Function for showing Repay Cash dialog
function show_repay_cash_dialog(frm) {
    frappe.prompt([
        {
            label: 'Mode of Payment',
            fieldname: 'mode_of_payment',
            fieldtype: 'Link',
            options: 'Mode of Payment',
            filters: { enabled: 1 }, // Only show enabled modes of payment
            reqd: 1
        },
        {
            label: 'Repay Amount',
            fieldname: 'repay_amount',
            fieldtype: 'Float', // Use Float for numeric input
            reqd: 1,
            default: frm.doc.outstanding_amount_from_repayment // Default repayment amount
        },
        {
            label: 'Payment Date',
            fieldname: 'payment_date',
            fieldtype: 'Date',
            reqd: 1,
            default: frappe.datetime.get_today() // Default to today's date
        }
    ], function(values) {
        // Show confirmation dialog before proceeding
        frappe.confirm(
            __('Are you sure you want to repay {0} on {1}?',
              [values.repay_amount, values.payment_date]),
            function() {
                // Call the function to create the repayment entry upon confirmation
                create_repay_cash(frm, values.mode_of_payment, values.repay_amount, values.payment_date);
            },
            function() {
                frappe.msgprint(__('Repayment canceled.'));
            }
        );
    }, 'Repay Cash', 'Repay');
}

// Function for creating Repay Cash
function create_repay_cash(frm, mode_of_payment, repay_amount, payment_date) {
    frappe.call({
        method: "purchase_loans.purchase_loans.doctype.purchase_loan_request.purchase_loan_request.create_repay_cash",
        args: {
            loan_request: frm.doc.name,
            company: frm.doc.company,
            employee: frm.doc.employee,
            mode_of_payment: mode_of_payment,
            payment_amount: repay_amount,
            payment_date: payment_date
        },
        callback: function(response) {
            if (response.message) {
                frappe.msgprint(__('Repayment successfully recorded.'));
                frm.reload_doc();  
            }
        }
    });
}
