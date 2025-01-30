import frappe
from frappe.utils import nowdate, add_days, date_diff
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate
from frappe import _
import random
import string
import re


@frappe.whitelist()
def validate_posting_date(doc, method):
    """Validate that posting_date is not in the future."""
    if doc.posting_date > nowdate():
        frappe.throw(_("Posting Date cannot be in the future."))


# Triggered before deleting a file
@frappe.whitelist()
def before_delete_file(doc, method):
    if doc.attached_to_doctype and doc.attached_to_name:
        # Get the roles of the current user
        user_roles = frappe.get_all(
            "Has Role",
            filters={"parent": frappe.session.user},
            fields=["role"]
        )
        user_roles = [role["role"] for role in user_roles]

        # Check if the user does not have the System Manager role
        if "System Manager" not in user_roles:
            frappe.throw(
                f"You cannot delete this file because it is attached to the document: {doc.attached_to_doctype} {doc.attached_to_name}. Please contact a System Manager to delete it.",
                frappe.PermissionError
            )


@frappe.whitelist()
def copy_attachments_to_target(target_doctype, target_docname, source_doctype, transaction_unique_id_field="custom_transaction_unique_id"):
    """
    Copies all attachments from a source doctype to a target doctype based on a shared Transaction Unique ID.
    Before inserting, it checks if the file is already attached to the target document.

    Args:
        target_doctype (str): The target doctype to attach files to (e.g., "Purchase Invoice").
        target_docname (str): The target document name to attach files to.
        source_doctype (str): The source doctype to fetch attachments from (e.g., "Purchase Order").
        transaction_unique_id_field (str): The field name for the Transaction Unique ID (default: "custom_transaction_unique_id").

    Raises:
        frappe.ValidationError: If the source document or attachments are not found.
    """
    try:
        # Fetch the target document
        target_doc = frappe.get_doc(target_doctype, target_docname)

        # Ensure the target document has a Transaction Unique ID
        transaction_unique_id = getattr(target_doc, transaction_unique_id_field, None)
        if not transaction_unique_id:
            frappe.throw(
                _(f"Transaction Unique ID ({transaction_unique_id_field}) is missing in the {target_doctype}: {target_docname}")
            )

        # Find the source documents with the same Transaction Unique ID
        source_docs = frappe.get_all(
            source_doctype,
            filters={transaction_unique_id_field: transaction_unique_id},
            fields=["name"]
        )

        if not source_docs:
            frappe.throw(
                _(f"No {source_doctype} found with the same Transaction Unique ID: {transaction_unique_id}")
            )

        # Fetch the first matching source document (adjust this if multiple matches are expected)
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
                frappe.msgprint(_(f"File {attachment['file_name']} already attached to {target_doctype}: {target_docname}"))
                continue  # Skip if file is already attached

            # If file is not attached, add it
            frappe.get_doc({
                "doctype": "File",
                "file_url": attachment["file_url"],
                "file_name": attachment["file_name"],
                "attached_to_doctype": target_doctype,
                "attached_to_name": target_docname
            }).insert(ignore_permissions=True)

        frappe.msgprint(
            _(f"Attachments copied successfully from {source_doctype} ({source_docname}) to {target_doctype} ({target_docname})")
        )

    except Exception as e:
        frappe.log_error(f"Error in copying attachments: {str(e)}")
        frappe.throw(_("An error occurred while copying attachments."))



def notify_purchase_order_and_invoice_issues():

    notify_sales_orders_without_delivery()
    notify_sales_orders_with_less_billed_amt()
    notify_sales_invoices_not_paid()


    notify_purchase_orders_without_receipts()
    notify_purchase_invoices_not_paid()
    notify_purchase_orders_with_items_billed_amt_less_than_net_amount()


def notify_sales_invoices_not_paid():
    # Today's date
    today = nowdate()

    # Fetch Sales Invoices where billed amount is greater than the paid amount
    invoices_not_paid = frappe.db.sql("""
        SELECT si.name AS invoice_name, si.posting_date, si.grand_total,
               si.outstanding_amount, si.paid_amount
        FROM `tabSales Invoice` si
       
        WHERE si.docstatus = 1
        AND si.outstanding_amount > 0  
    """, as_dict=True)

    # Prepare email content for notifications
    invoices_to_notify = []
    for invoice in invoices_not_paid:
        posting_date = invoice["posting_date"]
        
        # Calculate the difference between today and the posting date
        days_difference = date_diff(today, posting_date)

        # Check if it's exactly 2 days or every 10 days
        if days_difference == 2 or (days_difference > 2 and days_difference % 10 == 0):
            invoices_to_notify.append(invoice)

    if invoices_to_notify:
        # Fetch System Managers for email recipients
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", [sm["parent"] for sm in system_managers]], "enabled": 1},
            fields=["email"]
        )
        recipient_list = [user["email"] for user in recipients if user["email"]]

        if not recipient_list:
            frappe.log_error("No System Managers found to send notifications.")
            return

        # Prepare email content
        subject = "Sales Invoices Not Paid"
        message = "<p>The following Sales Invoices have outstanding amounts (unpaid):</p>"
        message += "<ul>"
        for invoice in invoices_to_notify:
            message += f"<li>Invoice: {invoice['invoice_name']} | Date: {invoice['posting_date']} | Total: {invoice['grand_total']} | Outstanding: {invoice['outstanding_amount']}</li>"
            message += f"<ul>"
        message += "</ul>"

        # Send email
        frappe.sendmail(
            recipients=recipient_list,
            subject=subject,
            message=message
        )


def notify_sales_orders_with_less_billed_amt():
    # Today's date
    today = nowdate()

    # Fetch Sales Orders with billed amount less than net amount
    so_with_less_billed_amt = frappe.db.sql("""
        SELECT so.name AS so_name, so.transaction_date, so.grand_total,
               soi.item_code, soi.item_name,
               soi.qty AS ordered_qty, soi.delivered_qty, soi.rate, soi.amount
        FROM `tabSales Order` so
        INNER JOIN `tabSales Order Item` soi ON so.name = soi.parent
        WHERE so.docstatus = 1
        AND soi.base_net_amount > soi.billed_amt  
    """, as_dict=True)

    # Prepare email content for notifications
    so_to_notify = []
    for so in so_with_less_billed_amt:
        transaction_date = so["transaction_date"]

        # Calculate the difference between today and the transaction date
        days_difference = date_diff(today, transaction_date)

        # Check if it's exactly 2 days or every 10 days
        if days_difference == 2 or (days_difference > 2 and days_difference % 10 == 0):
            so_to_notify.append(so)

    if so_to_notify:
        # Fetch System Managers for email recipients
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", [sm["parent"] for sm in system_managers]], "enabled": 1},
            fields=["email"]
        )
        recipient_list = [user["email"] for user in recipients if user["email"]]

        if not recipient_list:
            frappe.log_error("No System Managers found to send notifications.")
            return

        # Prepare email content
        subject = "Sales Orders with Billed Amount Less Than Net Amount"
        message = "<p>The following Sales Orders have Billed Amount less than the Net Amount:</p>"
        message += "<ul>"
        for so in so_to_notify:
            message += f"<li>SO: {so['so_name']} | Date: {so['transaction_date']} | Total: {so['grand_total']} </li>"
            message += f"<ul>"
            message += f"<li>Item: {so['item_name']} | Ordered Qty: {so['ordered_qty']} | Delivered Qty: {so['delivered_qty']}</li>"
            message += f"<li>Rate: {so['rate']} | Amount: {so['amount']}</li>"
            message += f"</ul>"
        message += "</ul>"

        # Send email
        frappe.sendmail(
            recipients=recipient_list,
            subject=subject,
            message=message
        )


def notify_sales_orders_without_delivery():
    # Today's date
    today = nowdate()

    # Fetch Sales Orders with Stock/Fixed Asset Items and Delivered Quantity < Ordered Quantity
    so_without_delivery = frappe.db.sql("""
        SELECT so.name AS so_name, so.transaction_date, so.grand_total,
               soi.item_code, soi.item_name, soi.qty AS ordered_qty, 
               soi.delivered_qty, soi.rate, soi.amount
        FROM `tabSales Order` so
        INNER JOIN `tabSales Order Item` soi ON so.name = soi.parent
        WHERE so.docstatus = 1
        AND soi.qty > (soi.delivered_qty + soi.returned_qty)
        AND soi.item_code IN (
            SELECT name FROM `tabItem`
            WHERE is_stock_item = 1 OR is_fixed_asset = 1
        )
    """, as_dict=True)

    # Prepare email content for notifications
    so_to_notify = []
    for so in so_without_delivery:
        transaction_date = so["transaction_date"]

        # Calculate the difference between today and the transaction date
        days_difference = date_diff(today, transaction_date)

        # Check if it's exactly 2 days or every 10 days
        if days_difference == 2 or (days_difference > 2 and days_difference % 10 == 0):
            so_to_notify.append(so)

    if so_to_notify:
        # Fetch System Managers for email recipients
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", [sm["parent"] for sm in system_managers]], "enabled": 1},
            fields=["email"]
        )
        recipient_list = [user["email"] for user in recipients if user["email"]]

        if not recipient_list:
            frappe.log_error("No System Managers found to send notifications.")
            return

        # Prepare email content
        subject = "Sales Orders With Less Delivered Quantity"
        message = "<p>The following Sales Orders for Stock or Fixed Asset Items have Delivered Quantity less than Ordered Quantity:</p>"
        message += "<ul>"
        for so in so_to_notify:
            message += f"<li>SO: {so['so_name']} | Date: {so['transaction_date']} | Amount: {so['grand_total']}</li>"
            message += f"<ul>"
            message += f"<li>Item: {so['item_name']} | Ordered Qty: {so['ordered_qty']} | Delivered Qty: {so['delivered_qty']}</li>"
            message += f"<li>Rate: {so['rate']} | Amount: {so['amount']}</li>"
            message += f"</ul>"
        message += "</ul>"

        # Send email
        frappe.sendmail(
            recipients=recipient_list,
            subject=subject,
            message=message
        )


def notify_purchase_orders_with_items_billed_amt_less_than_net_amount():
    # Today's date
    today = nowdate()

    # Fetch Purchase Orders where items billed amount < Net Amount
    po_with_items_billed_amt_less_than_net = frappe.db.sql("""
        SELECT po.name AS po_name, po.transaction_date, poi.net_amount, 
               po.grand_total, poi.item_code, poi.item_name, 
               poi.billed_amt AS billed_amt, poi.qty AS ordered_qty,
               poi.rate, poi.amount
        FROM `tabPurchase Order` po
        INNER JOIN `tabPurchase Order Item` poi ON po.name = poi.parent
        WHERE po.docstatus = 1
        AND poi.billed_amt < poi.net_amount
        
    """, as_dict=True)

    # Prepare email content for notifications
    po_to_notify = []
    for po in po_with_items_billed_amt_less_than_net:
        transaction_date = po["transaction_date"]

        # Calculate the difference between today and the transaction date
        days_difference = date_diff(today, transaction_date)

        # Check if it's exactly 2 days or every 10 days
        if days_difference == 2 or (days_difference > 2 and days_difference % 10 == 0):
            po_to_notify.append(po)

    if po_to_notify:
        # Fetch System Managers for email recipients
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", [sm["parent"] for sm in system_managers]], "enabled": 1},
            fields=["email"]
        )
        recipient_list = [user["email"] for user in recipients if user["email"]]

        if not recipient_list:
            frappe.log_error("No System Managers found to send notifications.")
            return

        # Prepare email content
        subject = "Purchase Orders with Items Billed Amount Less Than Net Amount"
        message = "<p>The following Purchase Orders have items where the billed amount is less than the Net Amount:</p>"
        message += "<ul>"
        for po in po_to_notify:
            message += f"<li>PO: {po['po_name']} | Date: {po['transaction_date']} | Net Amount: {po['net_amount']} | Billed Amount: {po['billed_amt']}</li>"
            message += f"<ul>"
            message += f"<li>Item: {po['item_name']} | Ordered Qty: {po['ordered_qty']} | Rate: {po['rate']}</li>"
            message += f"<li>Amount: {po['amount']}</li>"
            message += f"</ul>"
        message += "</ul>"

        # Send email
        frappe.sendmail(
            recipients=recipient_list,
            subject=subject,
            message=message
        )

def notify_purchase_invoices_not_paid():
    # Today's date
    today = nowdate()

    # Fetch Purchase Invoices where billed amount is greater than the paid amount
    invoices_not_paid = frappe.db.sql("""
        SELECT pi.name AS invoice_name, pi.posting_date, pi.grand_total,
               pi.outstanding_amount, pi.paid_amount, 
               pii.item_code, pii.item_name, pii.qty, pii.rate, pii.amount
        FROM `tabPurchase Invoice` pi
        INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
        WHERE pi.docstatus = 1
        AND pi.outstanding_amount > 0  -- This ensures there is outstanding payment
    """, as_dict=True)

    # Prepare email content for notifications
    invoices_to_notify = []
    for invoice in invoices_not_paid:
        posting_date = invoice["posting_date"]

        # Calculate the difference between today and the posting date
        days_difference = date_diff(today, posting_date)

        # Check if it's exactly 2 days or every 10 days
        if days_difference == 2 or (days_difference > 2 and days_difference % 10 == 0):
            invoices_to_notify.append(invoice)

    if invoices_to_notify:
        # Fetch System Managers for email recipients
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", [sm["parent"] for sm in system_managers]], "enabled": 1},
            fields=["email"]
        )
        recipient_list = [user["email"] for user in recipients if user["email"]]

        if not recipient_list:
            frappe.log_error("No System Managers found to send notifications.")
            return

        # Prepare email content
        subject = "Purchase Invoices Not Paid"
        message = "<p>The following Purchase Invoices have outstanding amounts (unpaid):</p>"
        message += "<ul>"
        for invoice in invoices_to_notify:
            message += f"<li>Invoice: {invoice['invoice_name']} | Date: {invoice['posting_date']} | Total: {invoice['grand_total']} | Outstanding: {invoice['outstanding_amount']}</li>"
            message += f"<ul>"
            message += f"<li>Item: {invoice['item_name']} | Ordered Qty: {invoice['qty']} | Rate: {invoice['rate']}</li>"
            message += f"<li>Amount: {invoice['amount']}</li>"
            message += f"</ul>"
        message += "</ul>"

        # Send email
        frappe.sendmail(
            recipients=recipient_list,
            subject=subject,
            message=message
        )


def notify_purchase_orders_without_receipts():
    # Today's date
    today = nowdate()

    # Fetch Purchase Orders with Stock/Fixed Asset Items and Received Quantity < Ordered Quantity
    po_without_receipts = frappe.db.sql("""
        SELECT po.name AS po_name, po.transaction_date, po.grand_total,
               poi.item_code, poi.item_name, poi.qty AS ordered_qty, 
               poi.received_qty, poi.rate, poi.amount
        FROM `tabPurchase Order` po
        INNER JOIN `tabPurchase Order Item` poi ON po.name = poi.parent
        WHERE po.docstatus = 1
        AND poi.qty > (poi.received_qty + poi.returned_qty) 
        AND poi.item_code IN (
            SELECT name FROM `tabItem`
            WHERE is_stock_item = 1 OR is_fixed_asset = 1
        )
    """, as_dict=True)

    # Prepare email content for notifications
    po_to_notify = []
    for po in po_without_receipts:
        transaction_date = po["transaction_date"]

        # Calculate the difference between today and the transaction date
        days_difference = date_diff(today, transaction_date)

        # Check if it's exactly 2 days or every 10 days
        if days_difference == 2 or (days_difference > 2 and days_difference % 10 == 0):
            po_to_notify.append(po)

    if po_to_notify:
        # Fetch System Managers for email recipients
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager"},
            fields=["parent"]
        )
        recipients = frappe.get_all(
            "User",
            filters={"name": ["in", [sm["parent"] for sm in system_managers]], "enabled": 1},
            fields=["email"]
        )
        recipient_list = [user["email"] for user in recipients if user["email"]]

        if not recipient_list:
            frappe.log_error("No System Managers found to send notifications.")
            return

        # Prepare email content
        subject = "Purchase Orders With Less Received Quantity"
        message = "<p>The following Purchase Orders for Stock or Fixed Asset Items have Received Quantity less than Ordered Quantity:</p>"
        message += "<ul>"
        for po in po_to_notify:
            message += f"<li>PO: {po['po_name']} | Date: {po['transaction_date']} | Amount: {po['grand_total']}</li>"
            message += f"<ul>"
            message += f"<li>Item: {po['item_name']} | Ordered Qty: {po['ordered_qty']} | Received Qty: {po['received_qty']}</li>"
            message += f"<li>Rate: {po['rate']} | Amount: {po['amount']}</li>"
            message += f"</ul>"
        message += "</ul>"

        # Send email
        frappe.sendmail(
            recipients=recipient_list,
            subject=subject,
            message=message
        )


@frappe.whitelist()
def validate_patch(self):
    self.flags.ignore_submit_comment = True
    from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

    self.set_posting_datetime()
    self.validate_mandatory()
    voucher = frappe.get_doc(self.voucher_type, self.voucher_no)
    if self.voucher_type in ["Stock Entry","Purchase Receipt","Delivery Note"] and voucher.custom_allow_expired_batches == 0:
        self.validate_batch()
    elif self.voucher_type not in ["Stock Entry", "Purchase Receipt" , "Purchase Invoice"]:
        self.validate_batch()
    validate_disabled_warehouse(self.warehouse)
    validate_warehouse_company(self.warehouse, self.company)
    self.scrub_posting_time()
    self.validate_and_set_fiscal_year()
    self.block_transactions_against_group_warehouse()
    self.validate_with_last_transaction_posting_time()
    self.validate_inventory_dimension_negative_stock()


@frappe.whitelist()
def validate_serialized_batch(self):
    from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
    from frappe.utils import flt, getdate

    is_material_issue = False

    for d in self.get("items"):
        # Validate serial numbers against batches
        if hasattr(d, "serial_no") and hasattr(d, "batch_no") and d.serial_no and d.batch_no:
            serial_nos = frappe.get_all(
                "Serial No",
                fields=["batch_no", "name", "warehouse"],
                filters={"name": ("in", get_serial_nos(d.serial_no))},
            )

            for row in serial_nos:
                if row.warehouse and row.batch_no != d.batch_no:
                    frappe.throw(
                        _("Row #{0}: Serial No {1} does not belong to Batch {2}").format(
                            d.idx, row.name, d.batch_no
                        )
                    )

        # Skip checks for material issue
        if is_material_issue:
            continue

        # Validate batch expiry for other cases
        if flt(d.qty) > 0.0 and d.get("batch_no") and self.get("posting_date") and self.docstatus < 2:
            expiry_date = frappe.get_cached_value("Batch", d.get("batch_no"), "expiry_date")

            if expiry_date and getdate(expiry_date) < getdate(self.posting_date):
                if self.doctype in ["Stock Entry", "Purchase Receipt", "Delivery Note"] and self.get("custom_allow_expired_batches") == 1:
                    pass
                else:
                    frappe.throw(
                        _("Row #{0}: The batch {1} has already expired.").format(
                            d.idx, get_link_to_form("Batch", d.get("batch_no"))
                        ),
                        frappe.ValidationError,
                    )


@frappe.whitelist()
def transfer_expired_batch_on_validate(doc, method):
    """
    Transfer expired batch balances to the custom warehouse during Batch validation.
    """
    # Check if the batch has expired
    today = nowdate()
    if doc.expiry_date and doc.expiry_date > today:
        return  # Skip if the batch is not expired

    # Fetch the remaining balance for the batch
    expired_batch = frappe.db.sql(
        """
        SELECT 
            SUM(sbb.total_qty) AS balance_qty,
            sbb.item_code,
            sbb.company,
            sbb.warehouse AS source_warehouse,
            b.expiry_date,
            b.stock_uom
        FROM 
            `tabSerial and Batch Bundle` sbb
        JOIN 
            `tabSerial and Batch Entry` sbe ON sbe.parent = sbb.name
        JOIN 
            `tabBatch` b ON b.name = sbe.batch_no
        WHERE 
            b.name = %s
            AND sbb.is_cancelled = 0
            AND sbb.is_rejected = 0
        GROUP BY 
            sbb.item_code, sbb.warehouse, b.expiry_date, b.stock_uom
        HAVING 
            balance_qty > 0
        """,
        (doc.name,),
        as_dict=True,
    )

    if not expired_batch:
        return  # No balance to transfer

    # Process the transfer
    for batch in expired_batch:
        company = batch["company"]
        company_record = frappe.get_doc("Company", company)
        custom_warehouse = company_record.custom_warehouse
        custom_enable_automatic_transfer = company_record.custom_enable_automatic_transfer
        if custom_enable_automatic_transfer == "No":
            return

        if not custom_warehouse:
            frappe.throw(
                f"Custom Warehouse is not set in the Company configuration for company {company}."
            )

        if custom_warehouse == batch["source_warehouse"]:
            continue  # Skip if the custom warehouse is the same as the source warehouse

        try:
            # Create a Stock Entry for the transfer
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Transfer"
            stock_entry.custom_allow_expired_batches = 1
            stock_entry.posting_date = today

            # Add the item to the Stock Entry
            stock_entry.append(
                "items",
                {
                    "item_code": batch["item_code"],
                    "qty": batch["balance_qty"],
                    "transfer_qty": batch["balance_qty"],
                    "uom": batch["stock_uom"],
                    "stock_uom": batch["stock_uom"],
                    "conversion_factor": 1,
                    "use_serial_batch_fields": 1,
                    "batch_no": doc.name,
                    "s_warehouse": batch["source_warehouse"],
                    "t_warehouse": custom_warehouse,
                },
            )

            # Save and submit the Stock Entry
            stock_entry.save(ignore_permissions=True)
            stock_entry.submit()

            frappe.msgprint(
                f"Transferred {batch['balance_qty']} of Item {batch['item_code']} (Batch {doc.name}) "
                f"from {batch['source_warehouse']} to {custom_warehouse}."
            )

        except Exception as e:
            frappe.log_error(
                f"Error transferring Batch {doc.name} of Item {batch['item_code']}: {str(e)}",
                "Expired Batch Transfer Job",
            )


@frappe.whitelist()
def transfer_expired_batches():
    """
    Scheduled job to transfer all expired batch balances to the custom warehouse.
    Runs daily at midnight.
    """
    today = nowdate()

    # Fetch all expired batches with remaining balances 
    expired_batches = frappe.db.sql(
        """
        SELECT 
            SUM(sbb.total_qty) AS balance_qty,
            sbb.item_code,
            sbb.company,
            sbb.warehouse AS source_warehouse,
            sbe.batch_no,
            b.expiry_date,
            b.stock_uom
        FROM 
            `tabSerial and Batch Bundle` sbb
        JOIN 
            `tabSerial and Batch Entry` sbe ON sbe.parent = sbb.name
        JOIN 
            `tabBatch` b ON b.name = sbe.batch_no
        WHERE 
            b.expiry_date <= %s
            AND sbb.is_cancelled = 0
            AND sbb.is_rejected = 0
        GROUP BY 
            sbb.item_code, sbb.warehouse, sbe.batch_no
        HAVING 
            balance_qty > 0
        """,
        (today,),
        as_dict=True,
    )

    if not expired_batches:
        frappe.log_error("No expired batches with balances found.", "Expired Batch Transfer Job")
        return

    for batch in expired_batches:
        company = batch["company"]
        company_record = frappe.get_doc("Company", company)
        custom_warehouse = company_record.custom_warehouse
        custom_enable_automatic_transfer = company_record.custom_enable_automatic_transfer
        if custom_enable_automatic_transfer == "No":
            return
        if not custom_warehouse:
            frappe.log_error("Custom Warehouse is not set in the Company configuration.")
            return
        if custom_warehouse == batch["source_warehouse"]:
            return
        # Create a Stock Entry for the transfer
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        stock_entry.custom_allow_expired_batches = 1
        stock_entry.posting_date = today

        # Add the item to the Stock Entry
        stock_entry.append(
            "items",
            {
                "item_code": batch["item_code"],
                "qty": batch["balance_qty"],
                "transfer_qty": batch["balance_qty"],
                "uom": batch["stock_uom"],
                "stock_uom": batch["stock_uom"],
                "conversion_factor": 1,
                "use_serial_batch_fields": 1,
                "batch_no": batch["batch_no"],
                "s_warehouse": batch["source_warehouse"],
                "t_warehouse": custom_warehouse,
            },
        )

        # Save and submit the Stock Entry
        stock_entry.save(ignore_permissions=True)
        stock_entry.submit()

        frappe.msgprint(
            f"Transferred {batch['balance_qty']} of Item {batch['item_code']} (Batch {batch['batch_no']}) "
            f"from {batch['source_warehouse']} to {custom_warehouse}."
        )

            
@frappe.whitelist()
def update_purchase_loan_request(purchase_loan_request_name):
    """
    Updates a Purchase Loan Request document with aggregate values from the ledger.

    Given a Purchase Loan Request document name, this function aggregates the total paid and
    total repaid amounts from the ledger and calculates the outstanding and overpaid amounts.
    The Purchase Loan Request document is then updated with the calculated values.

    :param purchase_loan_request_name: The name of the Purchase Loan Request document to update.
    """
    if not purchase_loan_request_name:
        return

    loan_request_doc = frappe.get_doc("Purchase Loan Request", purchase_loan_request_name)

    company_currency = frappe.db.get_value(
        "Company", filters={"name": loan_request_doc.company}, fieldname="default_currency"
    )
    
    if company_currency != loan_request_doc.currency:
        exchange_rate = loan_request_doc.exchange_rate
    else:
        exchange_rate = 1.0

    request_amount = loan_request_doc.request_amount * exchange_rate

    # Aggregate paid and repayment amounts from the ledger
    ledger_totals = frappe.db.sql("""
        SELECT 
            SUM(CASE WHEN purchase_loan_payment_type = 'Pay' AND cancelled = 0 THEN amount ELSE 0 END) AS total_paid,
            SUM(CASE WHEN purchase_loan_payment_type = 'RePay' AND cancelled = 0 THEN amount ELSE 0 END) AS total_repaid
        FROM `tabPurchase Loan Ledger`
        WHERE purchase_loan_request = %s
    """, (purchase_loan_request_name), as_dict=True)[0]

    # Ensure totals default to 0 if None
    total_paid = ledger_totals.get('total_paid') or 0
    total_repaid = ledger_totals.get('total_repaid') or 0

    # Calculate overpaid amount
    overpaid_amount = 0.0
    if total_repaid > request_amount:
        overpaid_amount = max(total_repaid - total_paid, 0)

    # Calculate outstanding amounts
    outstanding_from_repayment = max(total_paid - total_repaid, 0)
    outstanding_from_request = max(request_amount - total_paid, 0)
    overpaid_payment_amount = max(total_paid - request_amount, 0)

    # Update the Purchase Loan Request document with calculated values
    frappe.db.sql("""
        UPDATE `tabPurchase Loan Request`
        SET 
            paid_amount_from_request = %s,
            repaid_amount = %s,
            outstanding_amount_from_request = %s,
            outstanding_amount_from_repayment = %s,
            overpaid_payment_amount = %s,
            overpaid_repayment_amount = %s
        WHERE name = %s
    """, (
        total_paid / exchange_rate,
        total_repaid / exchange_rate,
        outstanding_from_request / exchange_rate,
        outstanding_from_repayment / exchange_rate,
        overpaid_payment_amount / exchange_rate,
        overpaid_amount / exchange_rate,
        purchase_loan_request_name
    ))

    # Commit changes to the database
    frappe.db.commit()


@frappe.whitelist()
def cancel_purchase_loan_ledger(doc):
    # Ensure the necessary fields are present
    """
    Cancels a Purchase Loan Ledger entry. This is a whitelisted function called
    by a hook on a custom doctype. It takes a doc object as argument, and
    requires the doc.name to be present. It then gets the Purchase Loan Ledger
    record linked to the doc and updates the cancelled field to 1.
    """
    if not doc.name:
        frappe.throw("Document name is required.")
    
    # Get the Purchase Loan Ledger record linked to the doc
    ledger_entry = frappe.get_all("Purchase Loan Ledger", filters={
        "purchase_loan_request": doc.custom_purchase_loan_request,
        "reference_name": doc.name
    })

    if ledger_entry:
        # Update the cancelled field to 1
        frappe.db.set_value("Purchase Loan Ledger", ledger_entry[0].name, "cancelled", 1)
        
        # Commit the transaction
        frappe.db.commit()

@frappe.whitelist()
def create_purchase_loan_ledger(doc, ledger_amount):
    # Create a new Purchase Loan Ledger entry
    """
    Creates a new entry in the Purchase Loan Ledger based on the provided document.
    Determines the payment type (Pay or RePay) from the voucher type, calculates the
    paid amount, and records the necessary details such as employee, company, and 
    posting date into the ledger. The new ledger entry is then inserted into the database.
    
    Args:
        doc (Document): The document containing details needed for creating the 
        Purchase Loan Ledger entry, including voucher type, custom purchase loan request, 
        employee, company, and posting date.
    """

    loan_request_doc = frappe.get_doc("Purchase Loan Request", doc.custom_purchase_loan_request)
    purchase_loan_payment_type = "Pay" if doc.voucher_type =="Purchase Loan Payment" else "RePay"
    paid_amount = ledger_amount
    ledger_entry = frappe.get_doc({
        "doctype": "Purchase Loan Ledger",
        "purchase_loan_request": loan_request_doc.name,
        "reference_name": doc.name,  
        "purchase_loan_payment_type": purchase_loan_payment_type,
        "employee": loan_request_doc.employee,
        "company": doc.company,
        "posting_date": doc.posting_date,
        "amount": paid_amount
    })

    # Insert the record into the database
    ledger_entry.insert()

    
def update_purchase_loan_request_on_submit(doc, method):
    """
    Called on submit of a Purchase Loan Payment, Settlement Invoice, or Settlement Expense.
    Creates a new Purchase Loan Ledger entry and updates the Purchase Loan Request.
    """
    if doc.custom_purchase_loan_request:

        update_purchase_loan_request(doc.custom_purchase_loan_request)

def update_purchase_loan_request_on_cancel(doc, method):
    """
    Called on cancel of a Purchase Loan Payment, Settlement Invoice, or Settlement Expense.
    Cancels the associated Purchase Loan Ledger entry and updates the Purchase Loan Request.
    If the cancelled document is a Purchase Loan Settlement Invoice, it sets the associated Purchase Invoice to "Overdue"
    and resets the outstanding amount. If it is a Purchase Loan Settlement Expense, it clears the Loan Repayment Other Expenses
    table and resets the total. In both cases, it adjusts the total_repayment_amount in the Purchase Loan Repayment document.
    """
    if doc.custom_purchase_loan_request:
        cancel_purchase_loan_ledger(doc)
        # Fetch the linked Purchase Loan Request document
        purchase_loan_request = frappe.get_doc("Purchase Loan Request", doc.custom_purchase_loan_request)
        total_invoices = 0.0
        total_other_expenses = 0.0
        # Fetch the associated Purchase Loan Repayment document
        purchase_loan_repayment = None
        if doc.voucher_type in ["Purchase Loan Settlement Invoice", "Purchase Loan Settlement Expense"]:
            purchase_loan_repayment = frappe.get_doc("Purchase Loan Repayment", doc.custom_purchase_loan_repayment)
            total_invoices = purchase_loan_repayment.total_invoices

            if doc.voucher_type == "Purchase Loan Settlement Invoice":
                # Adjust outstanding and repaid amounts
                purchase_loan_repayment_invoice_name = frappe.db.get_value(
                        "Purchase Loan Repayment Invoices",
                        filters={"purchase_invoice": doc.custom_row_name},
                        fieldname="name"
                    )
                if purchase_loan_repayment_invoice_name:
                    # Fetch the document for further processing
                    purchase_loan_repayment_invoice = frappe.get_doc(
                        "Purchase Loan Repayment Invoices",
                        purchase_loan_repayment_invoice_name
                    )
                    purchase_invoice = purchase_loan_repayment_invoice.purchase_invoice
                    outstanding_amount = purchase_loan_repayment_invoice.outstanding_amount
                    # Update invoices to "Overdue" and reset outstanding amounts
                    frappe.db.set_value("Purchase Invoice", doc.custom_row_name, {
                        "status": "Overdue",
                        "outstanding_amount": outstanding_amount
                    })
                    total_invoices -= outstanding_amount
                    purchase_loan_repayment.total_invoices = total_invoices
                    

            elif doc.voucher_type == "Purchase Loan Settlement Expense":
                # Sum and clear other expenses
                total_other_expenses = sum(row.amount for row in purchase_loan_repayment.loan_repayment_other_expenses)
                
                # Clear the `loan_repayment_other_expenses` table and reset total
                purchase_loan_repayment.loan_repayment_other_expenses = []
                purchase_loan_repayment.total_other_expenses = 0
                
                frappe.msgprint(_("Cleared Loan Repayment Other Expenses table for settlement expense cancellation."))

            # Adjust total_repayment_amount by subtracting the combined totals
            purchase_loan_repayment.total_repayment_amount -= (total_invoices + total_other_expenses)

            # Save changes to the Purchase Loan Repayment document
            purchase_loan_repayment.save(ignore_permissions=True)
            purchase_loan_repayment.reload()


        update_purchase_loan_request(doc.custom_purchase_loan_request)
        # Final success message
        frappe.msgprint(_("Purchase Loan Request '{0}' updated successfully.").format(purchase_loan_request.name))
