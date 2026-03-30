import frappe
from frappe.model.document import Document


class GRSEnquiry(Document):
    def before_insert(self):
        if self.recorded_by:
            self.recorded_by_name = frappe.db.get_value(
                "GRO Officer", self.recorded_by, "full_name"
            ) or self.recorded_by_name

    def before_save(self):
        self.before_insert()
        # When submitted, move grievance status to Under Enquiry
        if self.status == "Submitted":
            current_status = frappe.db.get_value("Grievance", self.grievance, "status")
            if current_status in ("Assigned", "Accepted"):
                frappe.db.set_value(
                    "Grievance", self.grievance, "status", "Under Enquiry"
                )
