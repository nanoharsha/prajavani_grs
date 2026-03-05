app_name = "prajavani_grs"
app_title = "Prajavani GRS"
app_publisher = "Open Source Contributors"
app_description = "Decentralised Grievance Redressal System for Indian State Governments"
app_email = ""
app_license = "MIT"
app_version = "1.0.0"

fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "GRS Citizen", "GRS Operator", "GRS Officer",
        "GRS Appellate Authority", "GRS Admin"
    ]]]},
    {"dt": "GRS District"},
    {"dt": "GRS Department"},
    {"dt": "GRS Category"},
    {"dt": "GRS Sub Category"},
]

doc_events = {
    "Grievance": {
        "before_save":  "prajavani_grs.grs.doctype.grievance.grievance.before_save",
        "after_insert": "prajavani_grs.grs.doctype.grievance.grievance.after_insert",
        "on_update":    "prajavani_grs.grs.doctype.grievance.grievance.on_update",
    },
    "ATR Action": {
        "before_save":  "prajavani_grs.grs.doctype.atr_action.atr_action.before_save",
        "after_insert": "prajavani_grs.grs.doctype.atr_action.atr_action.after_insert",
    },
    "Appeal": {
        "before_save":  "prajavani_grs.grs.doctype.appeal.appeal.before_save",
        "after_insert": "prajavani_grs.grs.doctype.appeal.appeal.after_insert",
    },
    "Appeal ATR": {
        "before_save":  "prajavani_grs.grs.doctype.appeal_atr.appeal_atr.before_save",
        "after_insert": "prajavani_grs.grs.doctype.appeal_atr.appeal_atr.after_insert",
    },
}

scheduler_events = {
    "daily": [
        "prajavani_grs.grs.tasks.daily.check_sla_breaches",
        "prajavani_grs.grs.tasks.daily.send_daily_digest",
    ],
    "hourly": [
        "prajavani_grs.grs.tasks.hourly.check_48hr_deadlines",
    ],
}

website_route_rules = [
    {"from_route": "/grs",        "to_route": "grs"},
    {"from_route": "/grs/track",  "to_route": "grs/track"},
    {"from_route": "/grs/file",   "to_route": "grs/file"},
    {"from_route": "/grs/appeal", "to_route": "grs/appeal"},
]
