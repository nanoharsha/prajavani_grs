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


def _build_timeline(grievance):
    """Build a chronological list of events for a grievance."""
    events = []

    # 1. Always: complaint filed
    events.append({
        "date":    str(grievance.get("filing_date") or ""),
        "type":    "filed",
        "title":   "Complaint Filed",
        "officer": "",
        "details": {
            "Department": grievance.get("department", ""),
            "Category":   grievance.get("category", ""),
            "Channel":    "Online",
        },
    })

    # 2. Officer assigned (if applicable)
    assignment_date = grievance.get("assignment_date")
    officer_name    = grievance.get("assigned_officer_name")
    if assignment_date:
        events.append({
            "date":    str(assignment_date),
            "type":    "assigned",
            "title":   "Officer Assigned",
            "officer": officer_name or "",
            "details": {"Officer": officer_name} if officer_name else {},
        })

    # 3. ATR actions
    atrs = frappe.db.get_all(
        "ATR Action",
        filters={"grievance": grievance.name},
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

    # 4. Prajavani attendances (multiple allowed)
    try:
        praj_list = frappe.db.get_all(
            "Prajavani Attendance",
            filters={"grievance": grievance.name},
            fields=["prajavani_date", "prajavani_level", "location",
                    "attending_officer_name", "nodal_officer_name",
                    "citizen_present", "gro_remarks", "citizen_remarks", "name"],
            order_by="prajavani_date asc",
        )
    except Exception:
        praj_list = []
    for pa in praj_list:
        details = {
            "Level":    pa.prajavani_level,
            "Venue":    pa.location,
        }
        if pa.attending_officer_name:
            details["Attending Officer"] = pa.attending_officer_name
        if pa.nodal_officer_name:
            details["Nodal Officer"] = pa.nodal_officer_name
        if pa.gro_remarks:
            details["GRO Remarks"] = pa.gro_remarks
        if pa.citizen_remarks:
            details["Citizen Remarks"] = pa.citizen_remarks
        if not pa.citizen_present:
            details["Note"] = "Citizen was not present"
        events.append({
            "date":    str(pa.prajavani_date or ""),
            "type":    "prajavani",
            "title":   f"Prajavani Hearing — {pa.prajavani_level} Level",
            "officer": pa.attending_officer_name or "",
            "details": details,
        })

    # 5. Enquiry entries (submitted only — not draft)
    try:
        enquiries = frappe.db.get_all(
            "GRS Enquiry",
            filters={"grievance": grievance.name, "status": "Submitted"},
            fields=["enquiry_date", "enquiry_type", "recorded_by_name",
                    "recorded_on_behalf_of", "persons_met", "location_visited",
                    "citizen_present", "findings", "recommendation"],
            order_by="enquiry_date asc",
        )
    except Exception:
        enquiries = []
    for eq in enquiries:
        details = {"Type": eq.enquiry_type}
        if eq.location_visited:
            details["Location"] = eq.location_visited
        if eq.persons_met:
            details["Persons Met"] = eq.persons_met
        if eq.findings:
            details["Findings"] = eq.findings
        if eq.recommendation:
            details["Recommendation"] = eq.recommendation
        officer_label = eq.recorded_by_name or eq.recorded_on_behalf_of or ""
        events.append({
            "date":    str(eq.enquiry_date or ""),
            "type":    "enquiry",
            "title":   f"Enquiry — {eq.enquiry_type}",
            "officer": officer_label,
            "details": details,
        })

    # 6. Appeals
    appeals = frappe.db.get_all(
        "Appeal",
        filters={"linked_grievance": grievance.name},
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

    # Fallback 1: try case-insensitive / normalised format variants
    # Old records used GRS/YYYY/DIST/SEQ (slashes); new ones use GRS-DIST-YYYY-SEQ (dashes).
    # Convert between the two so both formats always work.
    if not grievance:
        if "/" in query:
            # slash → dash: "GRS/2026/HYD/00001" → "GRS-HYD-2026-00001"
            parts = query.split("/")
            if len(parts) == 4:
                alt = f"{parts[0]}-{parts[2]}-{parts[1]}-{parts[3]}"
                grievance = frappe.db.get_value(
                    "Grievance", {"registration_no": alt}, FIELDS, as_dict=True)
        else:
            # dash → slash: "GRS-HYD-2026-00001" → "GRS/2026/HYD/00001"
            parts = query.split("-")
            if len(parts) == 4:
                alt = f"{parts[0]}/{parts[2]}/{parts[1]}/{parts[3]}"
                grievance = frappe.db.get_value(
                    "Grievance", {"registration_no": alt}, FIELDS, as_dict=True)

    # Fallback 2: the caller might have the raw Frappe document name (e.g. GRS-2026-00001)
    if not grievance:
        grievance = frappe.db.get_value("Grievance", query, FIELDS, as_dict=True)

    if not grievance:
        return {"error": "No complaint found. Check your registration number or search by mobile."}

    has_atr = bool(frappe.db.get_value("ATR Action", {"grievance": grievance.name}, "name"))
    # Appeal is only allowed when the officer has filed a Final ATR or Closure ATR
    has_final_atr = bool(frappe.db.get_value(
        "ATR Action",
        {"grievance": grievance.name, "atr_type": ["in", ["Final ATR", "Closure"]]},
        "name",
    ))
    status_label, status_desc = STATUS_LABELS.get(grievance.status, (grievance.status, ""))

    return {
        "registration_no": grievance.registration_no or grievance.name,
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
        "can_appeal":      has_final_atr and not frappe.db.get_value(
                               "Appeal", {"linked_grievance": grievance.name}, "name"),
        "steps":           _compute_steps(grievance, has_atr),
        "timeline":        _build_timeline(grievance),
    }


@frappe.whitelist(allow_guest=True)
def get_districts():
    return frappe.db.get_all(
        "GRS District",
        filters={"active": 1},
        fields=["name as district_name"],
        order_by="district_name asc",
    )


@frappe.whitelist(allow_guest=True)
def get_mandals(district=None):
    filters = {"active": 1}
    if district:
        filters["district"] = district
    return frappe.db.get_all(
        "GRS Mandal",
        filters=filters,
        fields=["name as mandal_name", "district"],
        order_by="mandal_name asc",
    )


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
