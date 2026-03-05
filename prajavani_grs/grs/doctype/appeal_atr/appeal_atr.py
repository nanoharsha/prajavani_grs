import frappe
from frappe.model.document import Document

class AppealATR(Document):
    def before_save(self):
        if not self.filed_by:
            return
        if not frappe.get_value("GRO Officer", self.filed_by, "is_appellate_authority"):
            frappe.throw("Only Appellate Authority officers can file an Appeal ATR.")
        if self.linked_appeal:
            orig = frappe.get_value("Appeal", self.linked_appeal, "original_gro")
            if self.filed_by == orig:
                frappe.throw("Original GRO cannot file an ATR on their own appeal.")
        self.no_lower_transfer = 1

    def after_insert(self):
        if self.linked_appeal:
            frappe.db.set_value("Appeal", self.linked_appeal, "status", "ATR Submitted")
