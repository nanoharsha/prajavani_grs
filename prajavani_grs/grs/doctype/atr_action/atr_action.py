import frappe
from frappe.model.document import Document

FINAL_ATR_BLOCKED = ["Gram Panchayat Officer", "Panchayat Secretary", "Section Officer"]

class ATRAction(Document):
    def before_save(self):
        if self.atr_type == "Final ATR" and self.filed_by:
            can_file = frappe.get_value("GRO Officer", self.filed_by, "can_file_final_atr")
            desig = frappe.get_value("GRO Officer", self.filed_by, "designation")
            if not can_file or desig in FINAL_ATR_BLOCKED:
                frappe.throw(f"Officers with designation '{desig}' cannot file a Final ATR.")
        if self.atr_type == "Sub-Judice":
            self.citizen_remarks = (
                "Your grievance is sub-judice (pending before a court). "
                "Action will be taken after court proceedings conclude.")

    def after_insert(self):
        status_map = {
            "Final ATR": "Closed",
            "ATR for Further Action": "Under Enquiry",
            "Sub-Judice": "Sub-Judice",
            "Interim Reply": "Interim Reply",
            "Policy Decision Awaited": "Policy Awaited",
            "Closure": "Closed",
        }
        if self.grievance and self.atr_type in status_map:
            frappe.db.set_value("Grievance", self.grievance, "status", status_map[self.atr_type])
        if self.atr_type == "ATR for Further Action" and self.forward_to_officer and self.grievance:
            frappe.db.set_value("Grievance", self.grievance, {
                "assigned_officer": self.forward_to_officer,
                "status": "Assigned",
            })

def before_save(doc, method=None):
    doc.before_save()

def after_insert(doc, method=None):
    doc.after_insert()
