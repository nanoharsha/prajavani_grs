import frappe
from frappe.model.document import Document
from prajavani_grs.grs.doctype.grievance.grievance import _send_sms

class AppealATR(Document):

    def before_save(self):
        if not self.filed_by:
            return
        is_appellate = frappe.get_value("GRO Officer", self.filed_by, "is_appellate_authority")
        if not is_appellate:
            frappe.throw("Only Appellate Authority officers can file an Appeal ATR.")
        if self.linked_appeal:
            original_gro = frappe.get_value("Appeal", self.linked_appeal, "original_gro")
            if self.filed_by == original_gro:
                frappe.throw("The original GRO cannot file an ATR on their own appeal case.")
        self.no_lower_transfer = 1

    def after_insert(self):
        if self.linked_appeal:
            frappe.db.set_value("Appeal", self.linked_appeal, "status", "ATR Submitted")
        if self.linked_appeal:
            grv = frappe.get_value("Appeal", self.linked_appeal, "linked_grievance")
            if grv:
                cit = frappe.get_value("Grievance", grv, "citizen")
                if cit:
                    mobile = frappe.get_value("Citizen", cit, "mobile_number")
                    if mobile:
                        _send_sms(mobile, f"Prajavani GRS Appeal Outcome: {self.atr_type}. "
                            f"{(self.citizen_remarks or '')[:150]}")
