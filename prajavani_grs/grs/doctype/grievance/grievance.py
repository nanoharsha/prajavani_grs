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
        officer_mobile = frappe.get_value("GRO Officer", self.assigned_officer, "mobile")
        if officer_mobile:
            ref = self.registration_no or self.name
            _send_sms(officer_mobile,
                f"Prajavani GRS: Grievance {ref} assigned to you. "
                f"Accept or Transfer within 48 hours. Login: https://yourdomain.gov.in")

    def _notify_status_change(self):
        prev = self.get_doc_before_save()
        if prev and prev.get("status") != self.status:
            mobile = frappe.get_value("Citizen", self.citizen, "mobile_number")
            if mobile:
                ref = self.registration_no or self.name
                _send_sms(mobile, f"Prajavani GRS: Ref {ref} status updated to {self.status}. "
                    f"Track: https://yourdomain.gov.in/grs/track")

    def _sms_citizen_confirmation(self):
        mobile = frappe.get_value("Citizen", self.citizen, "mobile_number")
        if mobile:
            ref = self.registration_no or self.name
            _send_sms(mobile, f"Prajavani GRS: Grievance {ref} registered. "
                f"Dept: {self.department}. Track: https://yourdomain.gov.in/grs/track")


def _send_sms(mobile, message):
    """Wire to your SMS gateway here (GUPSHUP / Twilio / NIC)."""
    frappe.logger("prajavani_grs").info(f"[GRS SMS] To={mobile} | {message}")


@frappe.whitelist(allow_guest=True)
def track_grievance(registration_no, mobile):
    results = frappe.get_list("Grievance",
        filters={"registration_no": registration_no},
        fields=["name", "registration_no", "status", "department",
                "category", "filing_date", "days_pending",
                "assigned_officer_name", "citizen"],
        limit=1)
    if not results:
        frappe.throw("No grievance found.", frappe.DoesNotExistError)
    g = results[0]
    cit_mobile = frappe.get_value("Citizen", g["citizen"], "mobile_number")
    if cit_mobile != mobile:
        frappe.throw("Mobile number does not match.", frappe.PermissionError)
    g["atr_history"] = frappe.get_list("ATR Action",
        filters={"grievance": g["name"]},
        fields=["atr_type", "submission_date", "citizen_remarks", "filed_by_name"],
        order_by="submission_date asc")
    return g


@frappe.whitelist()
def accept_grievance(grievance_name):
    frappe.only_for(["GRS Officer", "GRS Admin"])
    doc = frappe.get_doc("Grievance", grievance_name)
    if doc.status != "Assigned":
        frappe.throw("Grievance must be in Assigned status to accept.")
    doc.status = "Accepted"
    doc.save(ignore_permissions=True)
    return {"message": "Grievance accepted."}


@frappe.whitelist()
def transfer_grievance(grievance_name, to_officer, reason):
    frappe.only_for(["GRS Officer", "GRS Operator", "GRS Admin"])
    doc = frappe.get_doc("Grievance", grievance_name)
    doc.add_comment("Info", f"Transferred to {to_officer}. Reason: {reason}")
    doc.assigned_officer = to_officer
    doc.assignment_date = None
    doc.accept_transfer_deadline = None
    doc.save(ignore_permissions=True)
    return {"message": f"Transferred to {to_officer}."}
