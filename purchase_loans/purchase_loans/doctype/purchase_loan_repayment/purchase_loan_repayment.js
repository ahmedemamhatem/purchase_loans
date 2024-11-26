// Copyright (c) 2024, Ahmed Emam and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Purchase Loan Repayment", {
// 	refresh(frm) {

// 	},
// });

// Copyright (c) 2024, Ahmed Emam and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Loan Repayment", {
    setup: function(frm) {
        // Set up custom query for 'purchase_loan_request' field
        frm.set_query("purchase_loan_request", function() {
            // If 'employee' is not set, return an empty list
            if (!frm.doc.employee) {
                return {
                    filters: {
                        name: ["=", ""] // This will return no records
                    }
                };
            }
            
            // If 'employee' is set, filter by employee and outstanding_amount > 0
            return {
                filters: {
                    employee: frm.doc.employee,
                    outstanding_amount: [">", 0]
                }
            };
        });
    }
});

frappe.ui.form.on('Purchase Loan Repayment', {
    setup: function(frm) {
        // Filter 'purchase_invoice' field in the child table based on custom_employee and outstanding amount
        frm.fields_dict['purchase_loan_repayment_invoices'].grid.get_field('purchase_invoice').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    'custom_employee': doc.custom_employee,  // Updated from 'employee' to 'custom_employee'
                    'outstanding_amount': ['>', 0]
                }
            };
        };
    },
});
