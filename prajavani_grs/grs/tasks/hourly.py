import frappe
from prajavani_grs.grs.doctype.grievance.grievance import _send_sms

def check_48hr_deadlines():
    overdue = frappe.db.sql("""
        SELECT name, registration_no, assigned_officer, assigned_officer_name
        FROM `tabGrievance`
        WHERE status = 'Assigned'
          AND accept_transfer_deadline IS NOT NULL
          AND accept_transfer_deadline < NOW()
    """, as_dict=True)
    for g in overdue:
        if not g.get("assigned_officer"):
            continue
        mobile = frappe.get_value("GRO Officer", g["assigned_officer"], "mobile")
        if mobile:
            ref = g.get("registration_no") or g["name"]
            _send_sms(mobile,
                f"URGENT GRS: Grievance {ref} has passed the 48-hour accept/transfer deadline. "
                f"Please act immediately.")
        frappe.get_doc({"doctype": "Comment", "comment_type": "Info",
            "reference_doctype": "Grievance", "reference_name": g["name"],
            "content": f"48-hr deadline breached. Officer: {g.get('assigned_officer_name')}"
        }).insert(ignore_permissions=True)
