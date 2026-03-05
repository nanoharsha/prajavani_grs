import frappe
from frappe.model.document import Document
from prajavani_grs.grs.doctype.grievance.grievance import _send_sms

class Appeal(Document):

    def before_save(self):
        pass

    def after_insert(self):
        if self.linked_grievance:
            frappe.db.set_value("Grievance", self.linked_grievance, "status", "Appeal Filed")
        cit = frappe.get_value("Grievance", self.linked_grievance, "citizen") if self.linked_grievance else None
        if cit:
            mobile = frappe.get_value("Citizen", cit, "mobile_number")
            if mobile:
                _send_sms(mobile, f"Prajavani GRS: Appeal {self.name} registered for "
                    f"grievance {self.grievance_registration_no}.")
