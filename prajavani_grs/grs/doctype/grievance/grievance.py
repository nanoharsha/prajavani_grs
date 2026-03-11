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

    @frappe.whitelist()
    def get_case_timeline(self):
        events = []

        # 1. Grievance Filed
        events.append({
            "date": str(self.filing_date) if self.filing_date else "",
            "type": "filed",
            "title": "Grievance Filed",
            "details": {
                "Registration No": self.registration_no or self.name,
                "Channel": self.channel,
                "Level": self.registration_level,
                "Department": self.department,
                "Category": self.category,
                "Gist": self.gist_of_grievance,
            }
        })

        # 2. Assignment
        if self.assignment_date:
            events.append({
                "date": str(self.assignment_date),
                "type": "assigned",
                "title": "Assigned to Officer",
                "details": {
                    "Officer": self.assigned_officer_name,
                    "Designation": self.assigned_officer_designation,
                    "Deadline (48 hr)": str(self.accept_transfer_deadline) if self.accept_transfer_deadline else "",
                }
            })

        # 3. ATR Actions
        atrs = frappe.get_all(
            "ATR Action",
            filters={"grievance": self.name},
            fields=["submission_date", "atr_type", "filed_by_name", "filed_by_designation",
                    "citizen_remarks", "forward_to_level", "redressed_in_favour",
                    "court_case_number", "pending_court", "expected_resolution_days", "name"],
            order_by="submission_date asc"
        )
        for atr in atrs:
            details = {
                "ATR Type": atr.atr_type,
                "Filed By": atr.filed_by_name,
                "Designation": atr.filed_by_designation,
                "Remarks to Citizen": atr.citizen_remarks,
            }
            if atr.forward_to_level:
                details["Forwarded To"] = atr.forward_to_level
            if atr.redressed_in_favour:
                details["Redressed in Favour"] = atr.redressed_in_favour
            if atr.court_case_number:
                details["Court Case No"] = atr.court_case_number
                details["Court"] = atr.pending_court
            if atr.expected_resolution_days:
                details["Expected Resolution"] = atr.expected_resolution_days
            events.append({
                "date": str(atr.submission_date) if atr.submission_date else "",
                "type": "atr",
                "title": f"ATR Filed — {atr.atr_type}",
                "details": details
            })

        # 4. Appeals
        appeals = frappe.get_all(
            "Appeal",
            filters={"linked_grievance": self.name},
            fields=["filing_date", "appeal_level", "reason_for_appeal",
                    "detailed_explanation", "relief_requested", "status", "name"],
            order_by="filing_date asc"
        )
        for appeal in appeals:
            details = {
                "Appeal Level": appeal.appeal_level,
                "Reason": appeal.reason_for_appeal,
                "Explanation": appeal.detailed_explanation,
                "Relief Requested": appeal.relief_requested,
                "Status": appeal.status,
            }
            # Check for Appeal ATR
            appeal_atr = frappe.get_value(
                "Appeal ATR",
                {"linked_appeal": appeal.name},
                ["atr_type", "findings", "submission_date"],
                as_dict=True
            )
            if appeal_atr:
                details["Appeal Outcome"] = appeal_atr.get("atr_type", "")
                details["Order Date"] = str(appeal_atr.get("submission_date", "") or "")
            events.append({
                "date": str(appeal.filing_date) if appeal.filing_date else "",
                "type": "appeal",
                "title": f"Appeal Filed — {appeal.appeal_level}",
                "details": details
            })

        events.sort(key=lambda x: x["date"] or "")
        return events

