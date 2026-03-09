import frappe
from frappe.model.document import Document
from frappe.utils import today, now_datetime, date_diff, add_to_date
import datetime


def _send_sms(mobile, message):
    try:
        from frappe.core.doctype.sms_settings.sms_settings import send_sms
        send_sms([mobile], message)
    except Exception:
        frappe.log_error(f"SMS to {mobile}: {message}", "GRS SMS")


class Grievance(Document):
    def before_save(self):
        if self.filing_date:
            self.days_pending = date_diff(today(), self.filing_date)

    def after_insert(self):
        self._set_registration_no()

    def on_update(self):
        self._handle_assignment()

    def _set_registration_no(self):
        if self.registration_no:
            return
        year = datetime.date.today().year
        seq = self.name.split("-")[-1] if self.name else "00001"
        self.registration_no = f"GRS/{year}/{seq}"
        frappe.db.set_value("Grievance", self.name, "registration_no", self.registration_no)

    def _handle_assignment(self):
        if not self.assigned_officer:
            return
        prev = self.get_doc_before_save()
        if prev and prev.get("assigned_officer") == self.assigned_officer:
            return
        frappe.db.set_value("Grievance", self.name, {
            "assignment_date": today(),
            "accept_transfer_deadline": str(add_to_date(now_datetime(), hours=48)),
            "status": "Assigned" if self.status == "New" else self.status,
        })
