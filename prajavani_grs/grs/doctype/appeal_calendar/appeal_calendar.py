import frappe
from frappe.model.document import Document


class AppealCalendar(Document):
    def validate(self):
        if self.max_cases and len(self.scheduled_grievances) > self.max_cases:
            frappe.throw(f"Cannot schedule more than {self.max_cases} grievances for this event.")

    def before_save(self):
        for row in self.scheduled_grievances:
            if row.grievance and not row.citizen_name:
                citizen_id = frappe.db.get_value("Grievance", row.grievance, "citizen")
                if citizen_id:
                    row.citizen_name = frappe.db.get_value("Citizen", citizen_id, "full_name") or ""
            if row.grievance and not row.department:
                row.department = frappe.db.get_value("Grievance", row.grievance, "department") or ""
            if row.grievance and not row.gist:
                full_gist = frappe.db.get_value("Grievance", row.grievance, "gist_of_grievance") or ""
                row.gist = full_gist[:200]
