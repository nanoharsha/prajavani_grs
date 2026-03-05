import frappe
from frappe.utils import today

def check_sla_breaches():
    breached = frappe.get_list("Grievance",
        filters={"status": ["not in", ["Closed","Sub-Judice","Appeal Filed"]], "days_pending": [">", 21]},
        fields=["name","registration_no","department","assigned_officer_name","days_pending"],
        order_by="days_pending desc", limit=500)
    if not breached:
        return
    frappe.logger("prajavani_grs").info(f"[GRS] SLA breach: {len(breached)} cases over 21 days")

def send_daily_digest():
    frappe.logger("prajavani_grs").info("[GRS] Daily digest task ran.")
