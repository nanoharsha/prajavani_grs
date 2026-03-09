app_name = "prajavani_grs"
app_title = "Prajavani GRS"
app_publisher = "Open Source Contributors"
app_description = "Decentralised Grievance Redressal System for Indian State Governments"
app_email = ""
app_license = "MIT"
app_version = "1.0.0"

fixtures = [
    {"dt": "GRS District"},
    {"dt": "GRS Department"},
    {"dt": "GRS Category"},
    {"dt": "GRS Sub Category"},
]


scheduler_events = {
    "daily": [
        "prajavani_grs.grs.tasks.daily.check_sla_breaches",
        "prajavani_grs.grs.tasks.daily.send_daily_digest",
    ],
    "hourly": [
        "prajavani_grs.grs.tasks.hourly.check_48hr_deadlines",
    ],
}
