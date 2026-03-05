import frappe
from frappe.model.document import Document

class Appeal(Document):
    def before_save(self):
        pass

    def after_insert(self):
        if self.linked_grievance:
            frappe.db.set_value("Grievance", self.linked_grievance, "status", "Appeal Filed")

def before_save(doc, method=None):
    doc.before_save()

def after_insert(doc, method=None):
    doc.after_insert()
