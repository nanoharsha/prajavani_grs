import frappe
from frappe.model.document import Document


class PrajavaniAttendance(Document):
    def before_save(self):
        # Ensure registration number is always synced (fetch_from may not fire
        # when created programmatically or via the connections sidebar)
        if self.grievance and not self.grievance_reg_no:
            self.grievance_reg_no = frappe.db.get_value(
                "Grievance", self.grievance, "registration_no"
            ) or self.grievance

        # Mirror officer names so receipt prints correctly even without a
        # round-trip that would trigger fetch_from on the client
        if self.nodal_officer and not self.nodal_officer_name:
            self.nodal_officer_name = frappe.db.get_value(
                "GRO Officer", self.nodal_officer, "full_name"
            )
        if self.attending_officer and not self.attending_officer_name:
            self.attending_officer_name = frappe.db.get_value(
                "GRO Officer", self.attending_officer, "full_name"
            )
