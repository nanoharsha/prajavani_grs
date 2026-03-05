import frappe
from frappe.model.document import Document
from frappe.utils import today, now_datetime, date_diff, add_to_date
import datetime

class Grievance(Document):

    def before_save(self):
        if self.filing_date:
            self.days_pending = date_diff(today(), self.filing_date)

    def after_insert(self):
        self._set_registration_no()
        self._sms_citizen_confirmation()

    def on_update(self):
        self._handle_assignment()
        self._notify_status_change()

    def _set_registration_no(self):
        if self.registration_no:
            return
        district_code = ""
        if self.citizen:
            dist = frappe.get_value("Citizen", self.citizen, "district")
            if dist:
                district_code = dist[:3].upper()
        year = datetime.date.today().year
        seq = self.name.split("-")[-1] if self.name else "00001"
        self.registration_no = f"GRS/{year}/{district_code}/{seq}"
        frappe.db.set_value("Grievance", self.name, "registration_no", self.registration_no)

    def _handle_assignment(self):
        if not self.assigned_officer:
            return
        prev = self.get_doc_before_save()
        if prev and prev.get("assigned_officer") == self.assigned_officer:
            return
        self.assignment_date = today()
        self.accept_transfer_deadline = add_to_date(now_datetime(), hours=48)
        if self.status == "New":
            self.status = "Assigned"
        frappe.db.set_value("Grievance", self.name, {
            "assignment_date": self.assignment_date,
            "accept_transfer_deadline": self.accept_transfer_deadline,
            "status": self.status,
        })

    def _notify_status_change(self):
        prev = self.get_doc_before_save()
        if prev and prev.get("status") != self.status:
            frappe.logger("prajavani_grs").info(
                f"[GRS] Status changed: {self.name} → {self.status}")

    def _sms_citizen_confirmation(self):
        frappe.logger("prajavani_grs").info(
            f"[GRS] Grievance registered: {self.name}")


# ── Module-level wrappers required by hooks.py ──
def before_save(doc, method=None):
    doc.before_save()

def after_insert(doc, method=None):
    doc.after_insert()

def on_update(doc, method=None):
    doc.on_update()
