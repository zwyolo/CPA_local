# CPA Exam Availability Checker — Configuration

# Exam section (full name as shown on Prometric)
# Options: "Auditing and Attestation", "Financial Accounting and Reporting",
#          "Regulation", "Business Analysis and Reporting",
#          "Information Systems and Controls", "Tax Compliance and Planning"
EXAM_SECTION = "Auditing and Attestation"

# Location
STATE = "GA"
CITY_OR_ZIP = "Alpharetta"

# Date range (YYYY-MM-DD). START_DATE defaults to tomorrow if left as None.
START_DATE = "2026-03-30"
END_DATE = "2026-03-31"

# How often to search (minutes)
CHECK_INTERVAL_MINUTES = 60

# CAPTCHA solver: "ddddocr" (free & offline), "2captcha" (paid), "manual"
CAPTCHA_SOLVER = "ddddocr"
CAPTCHA_2CAPTCHA_API_KEY = ""  # only needed for "2captcha"

# Show browser window (False = visible, True = run silently in background)
HEADLESS = False
