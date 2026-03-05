import frappe

def check_48hr_deadlines():
    overdue = frappe.db.sql("""
        SELECT name, registration_no, assigned_officer
        FROM `tabGrievance`
        WHERE status = 'Assigned'
          AND accept_transfer_deadline IS NOT NULL
          AND accept_transfer_deadline < NOW()
    """, as_dict=True)
    for g in overdue:
        frappe.logger("prajavani_grs").info(
            f"[GRS] 48hr breach: {g.get('registration_no') or g['name']}")
