import frappe
from frappe.utils import today, now_datetime, add_to_date

# Days-pending thresholds for auto-escalation at each officer level
_ESCALATION_RULES = [
    {"level": "Mandal",   "threshold_days": 30, "escalate_to": "District"},
    {"level": "District", "threshold_days": 45, "escalate_to": "State"},
]

_SKIP_STATUSES = ("Closed", "Sub-Judice", "Appeal Filed")


def auto_escalate_grievances():
    """Reassign long-pending grievances to a senior officer at the next level.

    Rules:
      - Mandal-level officer + >30 days pending  → District-level officer
      - District-level officer + >45 days pending → State-level officer
    A comment is added to each escalated grievance for audit purposes.
    """
    for rule in _ESCALATION_RULES:
        overdue = frappe.db.sql("""
            SELECT g.name, g.registration_no, g.department,
                   g.assigned_officer, g.days_pending
            FROM   `tabGrievance` g
            JOIN   `tabGRO Officer` o ON o.name = g.assigned_officer
            WHERE  g.status NOT IN %(skip)s
              AND  g.days_pending > %(threshold)s
              AND  o.level = %(level)s
              AND  o.active = 1
        """, {
            "skip":      _SKIP_STATUSES,
            "threshold": rule["threshold_days"],
            "level":     rule["level"],
        }, as_dict=True)

        for g in overdue:
            dept = g.get("department")
            next_level = rule["escalate_to"]

            # Prefer an officer in the same department; fall back to any active officer
            senior = (
                frappe.db.get_value(
                    "GRO Officer",
                    {"level": next_level, "department": dept, "active": 1},
                    "name",
                ) or
                frappe.db.get_value(
                    "GRO Officer",
                    {"level": next_level, "active": 1},
                    "name",
                )
            )

            if not senior:
                frappe.logger("prajavani_grs").warning(
                    f"[GRS] No {next_level}-level officer found; "
                    f"cannot escalate {g.get('registration_no') or g['name']}"
                )
                continue

            frappe.db.set_value("Grievance", g["name"], {
                "assigned_officer":        senior,
                "status":                  "Assigned",
                "assignment_date":         today(),
                "accept_transfer_deadline": add_to_date(now_datetime(), hours=48),
            })

            # Audit comment visible in Frappe desk
            frappe.get_doc({
                "doctype":           "Comment",
                "comment_type":      "Info",
                "reference_doctype": "Grievance",
                "reference_name":    g["name"],
                "content": (
                    f"Auto-escalated after {g['days_pending']} days: "
                    f"{rule['level']} → {next_level} officer ({senior})."
                ),
            }).insert(ignore_permissions=True)

            frappe.logger("prajavani_grs").info(
                f"[GRS] Auto-escalated {g.get('registration_no') or g['name']} "
                f"to {senior} ({next_level}) after {g['days_pending']} days"
            )

    frappe.db.commit()


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
    frappe.logger("prajavani_grs").info("[GRS] Daily digest task ran.")
