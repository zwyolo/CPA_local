# CPA Local

A lightweight local tool to check CPA exam seat availability on Prometric.

This project uses Playwright to automatically search for CPA exam seats based on your selected exam section, location, and date range. It periodically checks availability, saves results locally, and sends a notification when seats are found.

## Features

- Search CPA exam availability on Prometric
- Configure exam section, location, and date range
- Automatically run on a schedule (interval-based)
- Save results to a local JSON file
- Filter nearby test centers (within 100 miles)
- Capture available dates and time slots
- Solve CAPTCHA automatically with multiple options
- Send notifications when seats become available

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/zwyolo/CPA_local.git
cd CPA_local
```

### 2. Create Conda environment and install dependencies

```bash
bash setup.sh
```

This script will:

- create a Conda environment named `cpa`
- install all dependencies from `requirements.txt`

### 3. Activate the environment

```bash
conda activate cpa
```

## Configuration

Edit `config.py` before running.

Example:

```python
EXAM_SECTION = "Auditing and Attestation"

STATE = "GA"
CITY_OR_ZIP = "Alpharetta"

START_DATE = "2026-03-30"
END_DATE = "2026-03-31"

CHECK_INTERVAL_MINUTES = 60

CAPTCHA_SOLVER = "ddddocr"
CAPTCHA_2CAPTCHA_API_KEY = ""

HEADLESS = False
```

## Run

```bash
conda activate cpa
python search.py
```

## Results

Results are saved to:

availability_results.json

Example:

```json
{
  "search_params": {
    "exam_section": "Auditing and Attestation",
    "location": "Alpharetta, GA",
    "start_date": "2026-03-30",
    "end_date": "2026-03-31"
  },
  "scraped_at": "2026-03-23T12:00:00",
  "centers": [
    {
      "center": "Prometric Test Center",
      "distance": "12.3 mi",
      "available_dates": [
        {
          "date": "March 30, 2026",
          "times": ["8:00 AM", "12:30 PM"]
        }
      ]
    }
  ]
}
```

## Notifications

When seats are found, a notification is sent via ntfy:

```bash
curl -d "CPA seats available!" https://ntfy.sh/your-topic
```

You can change the topic in `search.py`.

## Notes

- Only test centers within 100 miles are included
- Uses local Chrome if available, otherwise Playwright Chromium
- CAPTCHA solving may occasionally fail
- Set `HEADLESS = False` for debugging

## Disclaimer

This project is for personal use only. Prometric may change their website at any time, which can break the automation. Use responsibly.
