import frappe
from frappe.model.document import Document

class Appeal(Document):
    def after_insert(self):
        if self.linked_grievance:
            frappe.db.set_value("Grievance", self.linked_grievance, "status", "Appeal Filed")
