import frappe
from frappe.utils import today
from prajavani_grs.grs.doctype.grievance.grievance import _send_sms

def check_sla_breaches():
    breached = frappe.get_list("Grievance",
        filters={"status": ["not in", ["Closed","Sub-Judice","Appeal Filed"]], "days_pending": [">", 21]},
        fields=["name","registration_no","department","assigned_officer_name","days_pending"],
        order_by="days_pending desc", limit=500)
    if not breached:
        return
    admins = frappe.get_list("Has Role", filters={"role": "GRS Admin", "parenttype": "User"},
        fields=["parent as email"], limit=10)
    rows = "".join(f"<tr><td>{g['registration_no'] or g['name']}</td>"
        f"<td>{g['department']}</td>"
        f"<td>{g['assigned_officer_name'] or 'Unassigned'}</td>"
        f"<td style='color:red'>{g['days_pending']} days</td></tr>" for g in breached)
    body = (f"<h3>SLA Breach Report — {today()}</h3>"
        f"<p>{len(breached)} grievances exceed 21-day target.</p>"
        f"<table border='1' cellpadding='4'>"
        f"<tr><th>Ref</th><th>Dept</th><th>Officer</th><th>Days</th></tr>{rows}</table>")
    for admin in admins:
        if admin.get("email"):
            frappe.sendmail(recipients=[admin["email"]],
                subject=f"[GRS] SLA Breach Alert — {len(breached)} cases", message=body)

def send_daily_digest():
    officers = frappe.get_list("GRO Officer", filters={"active": 1},
        fields=["name","full_name","mobile"])
    for o in officers:
        pending = frappe.get_list("Grievance",
            filters={"assigned_officer": o["name"], "status": ["not in", ["Closed","Appeal Filed"]]},
            fields=["name"], limit=100)
        if not pending or not o.get("mobile"):
            continue
        overdue = frappe.get_list("Grievance",
            filters={"assigned_officer": o["name"],
                "status": ["not in", ["Closed","Appeal Filed"]], "days_pending": [">", 21]},
            fields=["name"], limit=100)
        _send_sms(o["mobile"],
            f"GRS Daily: {o['full_name']} — Open: {len(pending)}, Overdue >21d: {len(overdue)}. "
            f"Login: https://yourdomain.gov.in")
