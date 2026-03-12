import frappe

# ── Citizen-friendly label maps ──────────────────────────────────────────────

STATUS_LABELS = {
    "New":           ("Received",                  "Your complaint has been received and is waiting to be assigned."),
    "Assigned":      ("Officer Assigned",           "An officer has been assigned to look into your complaint."),
    "Accepted":      ("Under Review",               "The officer has accepted your complaint and is reviewing it."),
    "Under Enquiry": ("Being Investigated",         "An officer is actively investigating your complaint."),
    "Interim Reply": ("Update Sent",                "The officer has sent you an interim update while investigation continues."),
    "Sub-Judice":    ("Sub-Judice",                 "This matter is currently being heard in a court of law."),
    "Policy Awaited":("Policy Decision Pending",    "A policy-level decision is being awaited from higher authorities."),
    "Closed":        ("Resolved",                   "Your complaint has been resolved and closed."),
    "Appeal Filed":  ("Appeal in Progress",         "Your appeal has been filed and is under review."),
}

ATR_TITLES = {
    "Final ATR":               "Officer Submitted Final Response",
    "ATR for Further Action":  "Complaint Forwarded for Further Investigation",
    "Sub-Judice":              "Complaint is Now a Court Matter",
    "Interim Reply":           "Officer Sent You an Update",
    "Policy Decision Awaited": "Awaiting Policy-Level Decision",
    "Closure":                 "Complaint Has Been Closed",
}

STEP_ORDER = [
    "New", "Assigned", "Accepted", "Under Enquiry",
    "Interim Reply", "Sub-Judice", "Policy Awaited", "Closed",
]


def _compute_steps(grievance, has_atr):
    status = grievance.get("status", "New")
    assignment_date = grievance.get("assignment_date")
    filing_date = str(grievance.get("filing_date") or "")

    completed_index = STEP_ORDER.index(status) if status in STEP_ORDER else 0

    steps = [
        {
            "key":   "received",
            "label": "Complaint Received",
            "done":  True,
            "date":  filing_date,
        },
        {
            "key":   "assigned",
            "label": "Officer Assigned",
            "done":  bool(assignment_date),
            "date":  str(assignment_date or ""),
        },
        {
            "key":   "investigating",
            "label": "Being Investigated",
            "done":  completed_index >= STEP_ORDER.index("Under Enquiry") if "Under Enquiry" in STEP_ORDER else False,
            "date":  "",
        },
        {
            "key":   "response",
            "label": "Officer's Response",
            "done":  has_atr,
            "date":  "",
        },
        {
            "key":   "resolved",
            "label": "Resolved",
            "done":  status == "Closed",
            "date":  "",
        },
    ]

    # Mark the first incomplete step as active
    for step in steps:
        if not step["done"]:
            step["active"] = True
            break

    return steps


def _build_timeline(grievance_name, status):
    events = []

    # ATR actions
    atrs = frappe.db.get_all(
        "ATR Action",
        filters={"grievance": grievance_name},
        fields=["submission_date", "atr_type", "filed_by_name",
                "citizen_remarks", "forward_to_level",
                "redressed_in_favour", "expected_resolution_days"],
        order_by="submission_date asc",
    )
    for atr in atrs:
        details = {}
        if atr.citizen_remarks:
            details["Message from Officer"] = atr.citizen_remarks
        if atr.forward_to_level:
            details["Forwarded to"] = atr.forward_to_level
        if atr.redressed_in_favour:
            details["Resolved in Your Favour"] = "Yes" if atr.redressed_in_favour == "Yes" else "No"
        if atr.expected_resolution_days:
            details["Expected Resolution"] = atr.expected_resolution_days
        events.append({
            "date":    str(atr.submission_date or ""),
            "type":    "atr",
            "title":   ATR_TITLES.get(atr.atr_type, "Officer Responded"),
            "officer": atr.filed_by_name or "",
            "details": details,
        })

    # Appeals
    appeals = frappe.db.get_all(
        "Appeal",
        filters={"linked_grievance": grievance_name},
        fields=["filing_date", "appeal_level", "reason_for_appeal", "status", "name"],
        order_by="filing_date asc",
    )
    for appeal in appeals:
        details = {"Reason": appeal.reason_for_appeal, "Status": appeal.status}
        appeal_atr = frappe.db.get_value(
            "Appeal ATR",
            {"linked_appeal": appeal.name},
            ["atr_type", "submission_date"],
            as_dict=True,
        )
        if appeal_atr:
            details["Appeal Outcome"] = appeal_atr.get("atr_type", "")
            details["Order Date"] = str(appeal_atr.get("submission_date") or "")
        events.append({
            "date":    str(appeal.filing_date or ""),
            "type":    "appeal",
            "title":   f"You Filed an Appeal ({appeal.appeal_level})",
            "officer": "",
            "details": details,
        })

    events.sort(key=lambda x: x["date"])
    return events


# ── Public API endpoints ─────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def track_grievance(registration_no):
    """Public endpoint: citizen tracks their complaint.

    Accepts either a registration number (GRS/YYYY/…) or a 10-digit
    mobile number.  When a mobile number is supplied, all grievances
    filed from that number are returned as a summary list so the
    citizen can pick the one they want to inspect.
    """
    query = (registration_no or "").strip()
    if not query:
        return {"error": "Please enter a registration number or mobile number."}

    # ── Mobile-number search ──────────────────────────────────────────────────
    if query.isdigit() and len(query) == 10:
        citizen_names = frappe.db.get_all(
            "Citizen",
            filters={"mobile_number": query},
            pluck="name",
        )
        if not citizen_names:
            return {"error": "No complaints found for this mobile number."}

        grievances = frappe.db.get_all(
            "Grievance",
            filters={"citizen": ["in", citizen_names]},
            fields=["name", "registration_no", "filing_date",
                    "department", "category", "status"],
            order_by="filing_date desc",
        )
        if not grievances:
            return {"error": "No complaints found for this mobile number."}

        # Return a list so the UI can display a picker
        summary = []
        for g in grievances:
            label, _ = STATUS_LABELS.get(g.status, (g.status, ""))
            summary.append({
                "registration_no": g.registration_no or g.name,
                "filing_date":     str(g.filing_date or ""),
                "department":      g.department,
                "category":        g.category,
                "status":          g.status,
                "status_label":    label,
            })
        return {"grievances": summary}

    # ── Registration-number search ────────────────────────────────────────────
    FIELDS = ["name", "status", "filing_date", "department", "category",
              "gist_of_grievance", "assigned_officer_name",
              "assignment_date", "citizen_name", "registration_no",
              "days_pending"]

    grievance = frappe.db.get_value(
        "Grievance",
        {"registration_no": query},
        FIELDS,
        as_dict=True,
    )

    # Fallback: the caller might have the raw document name (e.g. GRS-2026-00001)
    if not grievance:
        grievance = frappe.db.get_value("Grievance", query, FIELDS, as_dict=True)

    if not grievance:
        return {"error": "No complaint found. Check your registration number or search by mobile."}

    has_atr = bool(frappe.db.get_value("ATR Action", {"grievance": grievance.name}, "name"))
    status_label, status_desc = STATUS_LABELS.get(grievance.status, (grievance.status, ""))

    return {
        "registration_no": grievance.registration_no,
        "citizen_name":    grievance.citizen_name,
        "department":      grievance.department,
        "category":        grievance.category,
        "gist":            grievance.gist_of_grievance,
        "filing_date":     str(grievance.filing_date or ""),
        "days_pending":    grievance.days_pending,
        "status":          grievance.status,
        "status_label":    status_label,
        "status_desc":     status_desc,
        "officer_name":    grievance.assigned_officer_name or "",
        "can_appeal":      grievance.status in ("Closed",) and not frappe.db.get_value(
                               "Appeal", {"linked_grievance": grievance.name}, "name"),
        "steps":           _compute_steps(grievance, has_atr),
        "timeline":        _build_timeline(grievance.name, grievance.status),
    }


@frappe.whitelist(allow_guest=True)
def get_departments():
    return frappe.db.get_all("GRS Department", fields=["name"], order_by="name asc")


@frappe.whitelist(allow_guest=True)
def get_categories(department=None):
    filters = {}
    if department:
        filters["department"] = department
    cats = frappe.db.get_all("GRS Category", filters=filters, fields=["name"], order_by="name asc")
    return cats


@frappe.whitelist(allow_guest=True)
def get_sub_categories(category=None):
    filters = {}
    if category:
        filters["category"] = category
    return frappe.db.get_all("GRS Sub Category", filters=filters, fields=["name"], order_by="name asc")


@frappe.whitelist(allow_guest=True)
def submit_grievance(full_name, mobile, district, department, category, gist,
                     gender=None, sub_category=None):
    """Public endpoint: citizen files a grievance online."""
    full_name  = (full_name or "").strip()
    mobile     = (mobile or "").strip()
    district   = (district or "").strip()
    department = (department or "").strip()
    category   = (category or "").strip()
    gist       = (gist or "").strip()

    if not all([full_name, mobile, district, department, category, gist]):
        return {"error": "All required fields must be filled."}
    if len(mobile) != 10 or not mobile.isdigit():
        return {"error": "Please enter a valid 10-digit mobile number."}
    if len(gist) < 20:
        return {"error": "Please describe your complaint in at least 20 characters."}

    # Find existing citizen by mobile, or create a new one
    citizen_name = frappe.db.get_value("Citizen", {"mobile_number": mobile}, "name")
    if not citizen_name:
        citizen = frappe.get_doc({
            "doctype": "Citizen",
            "full_name": full_name,
            "mobile_number": mobile,
            "gender": gender or "Male",
            "district": district,
            # aadhaar_last4, mandal_ward, address are collected offline
            "aadhaar_last4": "0000",
            "address": f"{district} (Online)",
        })
        citizen.insert(ignore_permissions=True, ignore_mandatory=True)
        citizen_name = citizen.name

    grievance = frappe.get_doc({
        "doctype": "Grievance",
        "filing_date": frappe.utils.today(),
        "channel": "Online",
        "registration_level": "State",
        "status": "New",
        "grievance_type": "Individual",
        "citizen": citizen_name,
        "department": department,
        "category": category,
        "sub_category": sub_category or None,
        "gist_of_grievance": gist,
    })
    grievance.insert(ignore_permissions=True, ignore_mandatory=True)
    frappe.db.commit()

    # Reload to get registration_no set by after_insert hook
    reg_no = frappe.db.get_value("Grievance", grievance.name, "registration_no") or grievance.name
    return {"registration_no": reg_no}
