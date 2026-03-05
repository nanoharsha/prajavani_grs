import frappe
from frappe.model.document import Document

class AppealATR(Document):
    def before_save(self):
        if not self.filed_by:
            return
        is_appellate = frappe.get_value("GRO Officer", self.filed_by, "is_appellate_authority")
        if not is_appellate:
            frappe.throw("Only Appellate Authority officers can file an Appeal ATR.")
        self.no_lower_transfer = 1

    def after_insert(self):
        if self.linked_appeal:
            frappe.db.set_value("Appeal", self.linked_appeal, "status", "ATR Submitted")

