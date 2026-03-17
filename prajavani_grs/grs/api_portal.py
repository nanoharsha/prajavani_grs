"""
Staff Portal API — Operator & Officer endpoints.

All endpoints require the user to be logged in (not guest).
Role-based access is enforced per function.
"""

import frappe
from frappe import _


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to continue."), frappe.AuthenticationError)


def _roles():
    return frappe.get_roles(frappe.session.user)


def _is_operator():
    r = _roles()
    return "GRS Operator" in r or "GRS Admin" in r


def _is_officer():
    r = _roles()
    return "GRS Officer" in r or "GRS Appellate Authority" in r or "GRS Admin" in r


def _get_officer_record():
    """Return GRO Officer record linked to the current user, or None."""
    user = frappe.session.user
    return frappe.db.get_value(
        "GRO Officer",
        {"user": user, "active": 1},
        ["name", "full_name", "designation", "level", "district", "mandal",
         "department", "login_role", "is_appellate_authority"],
        as_dict=True,
    )


def _build_grievance_filters(officer, level=None, district=None, mandal=None,
                              status=None, search=None):
    filters = {}
    if officer:
        if officer.level == "Mandal":
            filters["registration_level"] = "Mandal"
            if officer.district:
                filters["district"] = officer.district
        elif officer.level == "District":
            if officer.district:
                filters["district"] = officer.district
        # State level sees everything — no additional filter

    # Request-level overrides
    if level:
        filters["registration_level"] = level
    if district:
        filters["district"] = district
    if status:
        filters["status"] = status

    return filters


# ── User Info ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_user_info():
    """Return current session user info + roles + officer profile."""
    user = frappe.session.user
    if user == "Guest":
        return {"logged_in": False}

    roles = _roles()
    officer = _get_officer_record()

    return {
        "logged_in": True,
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "roles": roles,
        "is_operator": "GRS Operator" in roles,
        "is_officer": "GRS Officer" in roles,
        "is_appellate": "GRS Appellate Authority" in roles,
        "is_admin": "GRS Admin" in roles,
        "officer": officer,
    }


# ── Grievance List & Detail ────────────────────────────────────────────────────

@frappe.whitelist()
def get_grievance_list(level=None, district=None, mandal=None, status=None,
                       page=1, per_page=20, search=None):
    _require_login()
    if not (_is_operator() or _is_officer()):
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    officer = _get_officer_record()
    filters = _build_grievance_filters(officer, level, district, mandal, status)

    page, per_page = int(page), int(per_page)

    or_filters = None
    if search:
        search = search.strip()
        or_filters = [
            ["registration_no", "like", f"%{search}%"],
            ["citizen_name", "like", f"%{search}%"],
        ]

    grievances = frappe.get_all(
        "Grievance",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "registration_no", "status", "filing_date", "department",
                "category", "gist_of_grievance", "assigned_officer_name",
                "district", "registration_level", "days_pending", "channel",
                "citizen_name", "is_emergency"],
        order_by="filing_date desc",
        limit=per_page,
        start=(page - 1) * per_page,
    )

    total = frappe.db.count("Grievance", filters=filters)
    return {"data": grievances, "total": total, "page": page, "per_page": per_page}


@frappe.whitelist()
def get_grievance_detail(grievance_id):
    _require_login()
    if not (_is_operator() or _is_officer()):
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    g = frappe.get_doc("Grievance", grievance_id)

    citizen = None
    if g.citizen:
        citizen = frappe.db.get_value(
            "Citizen", g.citizen,
            ["full_name", "mobile_number", "gender", "district", "mandal_ward",
             "address", "is_senior_citizen", "is_pwd"],
            as_dict=True,
        )

    atrs = frappe.get_all(
        "ATR Action",
        filters={"grievance": grievance_id},
        fields=["name", "atr_type", "submission_date", "filed_by",
                "atr_remarks", "citizen_remarks", "citizen_contacted",
                "forward_to_level", "expected_resolution_days"],
        order_by="submission_date asc",
    )

    attendances = frappe.get_all(
        "Prajavani Attendance",
        filters={"grievance": grievance_id},
        fields=["name", "prajavani_date", "prajavani_level", "location",
                "nodal_officer_name", "attending_officer_name",
                "gro_remarks", "citizen_present"],
        order_by="prajavani_date asc",
    )

    appeals = frappe.get_all(
        "Appeal",
        filters={"linked_grievance": grievance_id},
        fields=["name", "appeal_level", "filing_date", "status", "reason_for_appeal"],
        order_by="filing_date asc",
    )

    return {
        "grievance": g.as_dict(),
        "citizen": citizen,
        "atrs": atrs,
        "prajavani_attendances": attendances,
        "appeals": appeals,
    }


# ── Create Grievance (Operator) ────────────────────────────────────────────────

@frappe.whitelist()
def create_grievance(full_name, mobile, district, department, category, gist,
                     gender=None, sub_category=None, mandal=None,
                     channel="Prajavani", registration_level="Mandal",
                     is_group=0, group_count=None,
                     is_senior=0, is_pwd=0, is_emergency=0):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Only operators can create grievances."), frappe.PermissionError)

    full_name  = (full_name or "").strip()
    mobile     = (mobile or "").strip()
    district   = (district or "").strip()
    department = (department or "").strip()
    category   = (category or "").strip()
    gist       = (gist or "").strip()

    if not all([full_name, mobile, district, department, category, gist]):
        frappe.throw(_("All required fields must be filled."))
    if len(mobile) != 10 or not mobile.isdigit():
        frappe.throw(_("Please enter a valid 10-digit mobile number."))
    if len(gist) < 10:
        frappe.throw(_("Please describe the grievance in at least 10 characters."))

    # Find or create citizen
    citizen_name = frappe.db.get_value("Citizen", {"mobile_number": mobile}, "name")
    if citizen_name:
        cit = frappe.get_doc("Citizen", citizen_name)
        cit.full_name = full_name
        cit.district = district
        if mandal:
            cit.mandal_ward = mandal
        if gender:
            cit.gender = gender
        cit.is_senior_citizen = int(is_senior)
        cit.is_pwd = int(is_pwd)
        cit.save(ignore_permissions=True)
    else:
        cit = frappe.get_doc({
            "doctype": "Citizen",
            "full_name": full_name,
            "mobile_number": mobile,
            "gender": gender or "Male",
            "district": district,
            "mandal_ward": mandal or "",
            "aadhaar_last4": "0000",
            "address": f"{mandal or district}",
            "is_senior_citizen": int(is_senior),
            "is_pwd": int(is_pwd),
        })
        cit.insert(ignore_permissions=True, ignore_mandatory=True)
        citizen_name = cit.name

    g = frappe.get_doc({
        "doctype": "Grievance",
        "filing_date": frappe.utils.today(),
        "channel": channel,
        "registration_level": registration_level,
        "status": "New",
        "grievance_type": "Group" if int(is_group) else "Individual",
        "group_members_count": int(group_count) if group_count and int(is_group) else None,
        "citizen": citizen_name,
        "department": department,
        "category": category,
        "sub_category": sub_category or None,
        "gist_of_grievance": gist,
        "is_emergency": int(is_emergency),
    })
    g.insert(ignore_permissions=True, ignore_mandatory=True)
    frappe.db.commit()

    reg_no = frappe.db.get_value("Grievance", g.name, "registration_no") or g.name
    return {"success": True, "registration_no": reg_no, "name": g.name}


# ── Officer Suggestions & Assignment ──────────────────────────────────────────

@frappe.whitelist()
def get_officer_suggestions(district=None, mandal=None, department=None, level=None):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    filters = {"active": 1}
    if level:
        filters["level"] = level
    if district:
        filters["district"] = district
    if mandal:
        filters["mandal"] = mandal
    if department:
        filters["department"] = department

    return frappe.get_all(
        "GRO Officer",
        filters=filters,
        fields=["name", "full_name", "designation", "level", "district", "mandal", "department"],
        order_by="level asc, full_name asc",
        limit=30,
    )


@frappe.whitelist()
def assign_officer_to_grievance(grievance_id, officer_id):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    g = frappe.get_doc("Grievance", grievance_id)
    g.assigned_officer = officer_id
    if g.status == "New":
        g.status = "Assigned"
    g.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


# ── Prajavani Attendance ───────────────────────────────────────────────────────

@frappe.whitelist()
def add_prajavani_attendance(grievance_id, prajavani_date, prajavani_level,
                              location=None, nodal_officer=None, attending_officer=None,
                              citizen_present=1, gro_remarks=None, citizen_remarks=None):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    pa = frappe.get_doc({
        "doctype": "Prajavani Attendance",
        "grievance": grievance_id,
        "prajavani_date": prajavani_date,
        "prajavani_level": prajavani_level,
        "location": location or "",
        "nodal_officer": nodal_officer or None,
        "attending_officer": attending_officer or None,
        "citizen_present": int(citizen_present),
        "gro_remarks": gro_remarks or "",
        "citizen_remarks": citizen_remarks or "",
    })
    pa.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": pa.name}


@frappe.whitelist()
def get_prajavani_list(level=None, district=None, from_date=None, to_date=None,
                       page=1, per_page=20):
    _require_login()
    if not (_is_operator() or _is_officer()):
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    filters = {}
    if level:
        filters["prajavani_level"] = level
    if from_date and to_date:
        filters["prajavani_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["prajavani_date"] = [">=", from_date]

    page, per_page = int(page), int(per_page)
    records = frappe.get_all(
        "Prajavani Attendance",
        filters=filters,
        fields=["name", "grievance", "grievance_reg_no", "prajavani_date",
                "prajavani_level", "location", "attending_officer_name",
                "citizen_present", "gro_remarks"],
        order_by="prajavani_date desc",
        limit=per_page,
        start=(page - 1) * per_page,
    )
    total = frappe.db.count("Prajavani Attendance", filters=filters)
    return {"data": records, "total": total, "page": page, "per_page": per_page}


# ── File Appeal (Operator on behalf of Citizen) ───────────────────────────────

@frappe.whitelist()
def file_appeal_operator(grievance_id, reason_for_appeal, detailed_explanation,
                          appeal_level="District", relief_requested=None):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    existing = frappe.db.exists(
        "Appeal", {"linked_grievance": grievance_id, "status": ["!=", "Closed"]}
    )
    if existing:
        frappe.throw(_("An active appeal already exists for this grievance."))

    appeal = frappe.get_doc({
        "doctype": "Appeal",
        "linked_grievance": grievance_id,
        "appeal_level": appeal_level,
        "channel": "Prajavani",
        "filing_date": frappe.utils.today(),
        "status": "Filed",
        "reason_for_appeal": reason_for_appeal,
        "detailed_explanation": detailed_explanation,
        "relief_requested": relief_requested or "",
    })
    appeal.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "appeal_no": appeal.name}


# ── Appeal Calendar ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_calendar_events(month=None, year=None, level=None, district=None):
    _require_login()
    if not (_is_operator() or _is_officer()):
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    filters = {}
    if level:
        filters["level"] = level
    if district:
        filters["district"] = district
    if month and year:
        m, y = int(month), int(year)
        start = f"{y}-{str(m).zfill(2)}-01"
        end_m = 1 if m == 12 else m + 1
        end_y = y + 1 if m == 12 else y
        end = f"{end_y}-{str(end_m).zfill(2)}-01"
        filters["event_date"] = ["between", [start, end]]

    events = frappe.get_all(
        "Appeal Calendar",
        filters=filters,
        fields=["name", "title", "event_date", "event_time", "event_type",
                "level", "district", "mandal", "venue", "presiding_officer",
                "status", "max_cases"],
        order_by="event_date asc",
    )

    for ev in events:
        ev["grievance_count"] = frappe.db.count(
            "Appeal Calendar Grievance", {"parent": ev.name}
        )

    return events


@frappe.whitelist()
def create_calendar_event(title, event_date, event_type, level,
                           event_time=None, district=None, mandal=None,
                           venue=None, presiding_officer=None, max_cases=50, notes=None):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    cal = frappe.get_doc({
        "doctype": "Appeal Calendar",
        "title": title,
        "event_date": event_date,
        "event_type": event_type,
        "level": level,
        "event_time": event_time or None,
        "district": district or None,
        "mandal": mandal or None,
        "venue": venue or "",
        "presiding_officer": presiding_officer or None,
        "max_cases": int(max_cases),
        "notes": notes or "",
        "status": "Scheduled",
    })
    cal.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": cal.name}


@frappe.whitelist()
def assign_grievance_to_calendar(calendar_event_id, grievance_id):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    cal = frappe.get_doc("Appeal Calendar", calendar_event_id)

    if any(row.grievance == grievance_id for row in cal.scheduled_grievances):
        frappe.throw(_("This grievance is already scheduled for this event."))

    if len(cal.scheduled_grievances) >= (cal.max_cases or 50):
        frappe.throw(_("Maximum case limit reached for this event."))

    g = frappe.db.get_value(
        "Grievance", grievance_id,
        ["citizen", "department", "gist_of_grievance", "assigned_officer"],
        as_dict=True,
    )
    citizen_name = ""
    if g and g.citizen:
        citizen_name = frappe.db.get_value("Citizen", g.citizen, "full_name") or ""

    cal.append("scheduled_grievances", {
        "grievance": grievance_id,
        "citizen_name": citizen_name,
        "department": (g and g.department) or "",
        "gist": ((g and g.gist_of_grievance) or "")[:200],
        "assigned_officer": (g and g.assigned_officer) or None,
    })
    cal.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def get_calendar_event_detail(calendar_event_id):
    _require_login()
    if not (_is_operator() or _is_officer()):
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    cal = frappe.get_doc("Appeal Calendar", calendar_event_id)
    return cal.as_dict()


@frappe.whitelist()
def remove_grievance_from_calendar(calendar_event_id, grievance_id):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    cal = frappe.get_doc("Appeal Calendar", calendar_event_id)
    cal.scheduled_grievances = [
        row for row in cal.scheduled_grievances if row.grievance != grievance_id
    ]
    cal.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def mark_officer_notified(calendar_event_id, grievance_id):
    _require_login()
    if not _is_operator():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    cal = frappe.get_doc("Appeal Calendar", calendar_event_id)
    for row in cal.scheduled_grievances:
        if row.grievance == grievance_id:
            row.officer_notified = 1
            row.notification_sent_on = frappe.utils.now()
    cal.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


# ── Officer: My Cases ──────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_officer_cases(status=None, page=1, per_page=20):
    _require_login()
    if not _is_officer():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    officer = _get_officer_record()
    if not officer:
        frappe.throw(_("No officer profile found for your account. Contact admin."))

    filters = {"assigned_officer": officer.name}
    if status:
        filters["status"] = status

    page, per_page = int(page), int(per_page)
    cases = frappe.get_all(
        "Grievance",
        filters=filters,
        fields=["name", "registration_no", "status", "filing_date", "department",
                "category", "gist_of_grievance", "district", "days_pending",
                "registration_level", "channel", "citizen_name", "is_emergency",
                "accept_transfer_deadline"],
        order_by="filing_date asc",
        limit=per_page,
        start=(page - 1) * per_page,
    )

    today = frappe.utils.today()
    for case in cases:
        pending = case.get("days_pending") or 0
        case["is_overdue"] = pending > 30
        case["is_urgent"] = 15 <= pending <= 30

    total = frappe.db.count("Grievance", filters=filters)
    return {"data": cases, "total": total, "page": page, "per_page": per_page}


# ── Officer: Submit ATR ────────────────────────────────────────────────────────

@frappe.whitelist()
def submit_atr(grievance_id, atr_type, atr_remarks,
               citizen_contacted=0, mode_of_contact=None,
               enquiry_period_from=None, enquiry_period_to=None,
               citizen_remarks=None, forward_to_officer=None,
               expected_resolution_days=None, court_case_number=None,
               pending_court=None, reason_for_delay=None):
    _require_login()
    if not _is_officer():
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    officer = _get_officer_record()
    if not officer:
        frappe.throw(_("No officer profile found for your account."))

    # Validate that this officer is assigned
    assigned = frappe.db.get_value("Grievance", grievance_id, "assigned_officer")
    r = _roles()
    if assigned != officer.name and "GRS Admin" not in r:
        frappe.throw(_("You are not assigned to this grievance."))

    atr = frappe.get_doc({
        "doctype": "ATR Action",
        "grievance": grievance_id,
        "atr_type": atr_type,
        "filed_by": officer.name,
        "submission_date": frappe.utils.today(),
        "atr_remarks": atr_remarks,
        "citizen_contacted": int(citizen_contacted),
        "mode_of_contact": mode_of_contact or "",
        "enquiry_period_from": enquiry_period_from or None,
        "enquiry_period_to": enquiry_period_to or None,
        "citizen_remarks": citizen_remarks or "",
        "forward_to_officer": forward_to_officer or None,
        "expected_resolution_days": int(expected_resolution_days) if expected_resolution_days else None,
        "court_case_number": court_case_number or "",
        "pending_court": pending_court or "",
        "reason_for_delay": reason_for_delay or "",
    })
    atr.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "atr_id": atr.name}


# ── Dashboard Statistics ───────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stats():
    _require_login()
    if not (_is_operator() or _is_officer()):
        frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

    officer = _get_officer_record()
    base = {}
    if officer:
        if officer.level == "Mandal":
            base["registration_level"] = "Mandal"
            if officer.district:
                base["district"] = officer.district
        elif officer.level == "District":
            if officer.district:
                base["district"] = officer.district

    def cnt(extra_filters):
        return frappe.db.count("Grievance", {**base, **extra_filters})

    today = frappe.utils.today()
    next_7 = frappe.utils.add_days(today, 7)

    stats = {
        "total":           cnt({}),
        "new":             cnt({"status": "New"}),
        "assigned":        cnt({"status": "Assigned"}),
        "under_enquiry":   cnt({"status": ["in", ["Accepted", "Under Enquiry"]]}),
        "closed":          cnt({"status": "Closed"}),
        "overdue":         cnt({"status": ["not in", ["Closed"]], "days_pending": [">", 30]}),
        "appeals":         frappe.db.count("Appeal", {"status": ["!=", "Closed"]}),
        "todays_prajavani": frappe.db.count("Prajavani Attendance", {"prajavani_date": today}),
        "upcoming_events": frappe.db.count(
            "Appeal Calendar",
            {"event_date": ["between", [today, next_7]], "status": "Scheduled"},
        ),
    }

    # Officer-specific: my pending cases
    if officer:
        stats["my_pending"] = frappe.db.count(
            "Grievance",
            {"assigned_officer": officer.name, "status": ["not in", ["Closed"]]},
        )
        stats["my_overdue"] = frappe.db.count(
            "Grievance",
            {"assigned_officer": officer.name, "status": ["not in", ["Closed"]], "days_pending": [">", 30]},
        )

    return stats


# ── Master Data Helpers ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_mandals(district=None):
    filters = {}
    if district:
        filters["district"] = district
    return frappe.get_all(
        "GRS Mandal",
        filters=filters,
        fields=["name"],
        order_by="name asc",
    )


@frappe.whitelist()
def get_active_officers(district=None, mandal=None, level=None):
    _require_login()
    filters = {"active": 1}
    if level:
        filters["level"] = level
    if district:
        filters["district"] = district
    if mandal:
        filters["mandal"] = mandal
    return frappe.get_all(
        "GRO Officer",
        filters=filters,
        fields=["name", "full_name", "designation", "level", "district", "mandal"],
        order_by="full_name asc",
        limit=50,
    )
