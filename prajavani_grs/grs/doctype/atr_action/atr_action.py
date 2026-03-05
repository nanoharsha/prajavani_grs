import frappe
from frappe.model.document import Document
from prajavani_grs.grs.doctype.grievance.grievance import _send_sms

FINAL_ATR_BLOCKED = ["Gram Panchayat Officer", "Panchayat Secretary", "Section Officer"]

class ATRAction(Document):

    def before_save(self):
        if self.atr_type == "Final ATR":
            if not self.filed_by:
                return
            can_file = frappe.get_value("GRO Officer", self.filed_by, "can_file_final_atr")
            desig = frappe.get_value("GRO Officer", self.filed_by, "designation")
            if not can_file or desig in FINAL_ATR_BLOCKED:
                frappe.throw(
                    f"Officers with designation '{desig}' cannot file a Final ATR. "
                    f"Use ATR for Further Action instead.")
        if self.atr_type == "Sub-Judice":
            self.citizen_remarks = (
                "Your grievance is currently sub-judice (pending before a court of law). "
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
        self._notify_citizen()
        if self.atr_type == "ATR for Further Action" and self.forward_to_officer:
            doc = frappe.get_doc("Grievance", self.grievance)
            doc.assigned_officer = self.forward_to_officer
            doc.assignment_date = None
            doc.accept_transfer_deadline = None
            doc.status = "Assigned"
            doc.save(ignore_permissions=True)

    def _notify_citizen(self):
        if not self.grievance:
            return
        cit = frappe.get_value("Grievance", self.grievance, "citizen")
        if not cit:
            return
        mobile = frappe.get_value("Citizen", cit, "mobile_number")
        if not mobile:
            return
        ref = frappe.get_value("Grievance", self.grievance, "registration_no") or self.grievance
        _send_sms(mobile, f"Prajavani GRS ATR — Ref:{ref} | Type:{self.atr_type} | "
            f"{(self.citizen_remarks or '')[:150]}")
