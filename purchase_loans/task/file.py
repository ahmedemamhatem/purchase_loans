import frappe

@frappe.whitelist()
def before_delete_file(doc, method):
    if doc.attached_to_doctype and doc.attached_to_name:
        attached_doc = frappe.get_doc(doc.attached_to_doctype, doc.attached_to_name)

        # Check if the document has workflow restrictions
        if not has_write_access_on_workflow(frappe.session.user, doc.attached_to_doctype, doc.attached_to_name):
            frappe.throw(
                f"You cannot delete this file because you do not have edit access on the workflow state of {doc.attached_to_doctype} {doc.attached_to_name}.",
                frappe.PermissionError
            )

        # If the attached document is submitted (docstatus == 1), only System Manager can delete
        if attached_doc.docstatus == 1:
            if "System Manager" not in frappe.get_roles():
                frappe.throw(
                    f"You cannot delete this file because it is attached to a submitted document: {doc.attached_to_doctype} {doc.attached_to_name}. Only a System Manager can delete it.",
                    frappe.PermissionError
                )
            return  # System Manager is allowed to delete submitted documents

        # If the attached document is in draft (docstatus == 0), only the file owner can delete
        if doc.owner != frappe.session.user:
            frappe.throw(
                "You cannot delete this file because only the owner of the file can delete it in the draft state.",
                frappe.PermissionError
            )


def has_write_access_on_workflow(user, doctype, docname):
    """
    Check if the user has write access to a document based on its current workflow state.
    """
    doc = frappe.get_doc(doctype, docname)

    # Check if the document has a workflow_state field
    if "workflow_state" not in doc.as_dict():
        return True  # No workflow restriction, allow write access

    current_state = doc.get("workflow_state")

    if not current_state:
        return True  # No specific workflow state set, allow write access

    workflow_name = frappe.db.get_value("Workflow", {"document_type": doctype}, "name")

    if not workflow_name:
        return True  # No workflow configured, allow write access

    # Get allowed roles for the current workflow state
    allowed_roles = frappe.get_all(
        "Workflow Document State",
        filters={"parent": workflow_name, "state": current_state},
        pluck="allow_edit"
    )

    if not allowed_roles:
        return False  # No roles have write permission on this state

    # Get user roles
    user_roles = frappe.get_roles(user)

    # Check if user has at least one allowed role
    return any(role in user_roles for role in allowed_roles)
