"""
CPA Exam Availability Checker — Refactored to Playwright with Stealth & Optimizations.
"""

import json
import time
import re
import platform
import base64
from datetime import datetime, date, timedelta
from playwright.sync_api import sync_playwright, expect
from playwright_stealth import Stealth

import config
import captcha as captcha_mod

URL = "https://proscheduler.prometric.com/scheduling/searchAvailability"


def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_start_date() -> str:
    d = config.START_DATE if config.START_DATE else (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    parts = d.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    return d


def get_end_date() -> str:
    parts = config.END_DATE.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    return config.END_DATE


def _fmt_date_notify(date_str: str) -> str:
    """Helper for notification display."""
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%m/%d/%Y")
        except ValueError:
            pass
    return date_str


def _get_time_slots(page) -> list[str]:
    """
    Tries to capture time slots after clicking a date.
    Prioritizes absolute accuracy by being "slow and steady".
    """
    # 1. Increased mandatory wait to ensure the site clears the previous results
    page.wait_for_timeout(1500) 
    
    candidates = [
        "div.time-card", "div.time-slot", "button.time-slot", "li.time-slot",
        "div[class*='timecard']", "div[class*='time-card']", "div[class*='timeslot']",
        "div[class*='appointment-time']", "ul.timeslots li", "div.col-sm-3.col-xs-6",
    ]
    time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.IGNORECASE)

    # 2. Longer retry loop with more spacing
    for _ in range(10):
        # Look for specific time elements
        for sel in candidates:
            els = page.query_selector_all(sel)
            texts = [e.inner_text().strip() for e in els if e.inner_text().strip()]
            times = [t for t in texts if time_pattern.search(t)]
            if times:
                # Extra grace period to ensure all slots are populated
                page.wait_for_timeout(500)
                return times

        # Check for "Loading" text or spinner to avoid premature scraping
        body_text = page.inner_text("body")
        if "Loading" in body_text or "Please wait" in body_text:
            page.wait_for_timeout(1000)
            continue

        # Fallback to container text
        try:
            container = page.locator("div.card.card-default.marginBottom").first
            if container.is_visible():
                times = time_pattern.findall(container.inner_text())
                if times:
                    page.wait_for_timeout(500)
                    return times
        except:
            pass

        page.wait_for_timeout(500)

    return []


def scrape_results(page) -> list:
    """Parse test center result cards, filtering >100 miles and fetching time slots."""
    results = []
    try:
        page.wait_for_selector("div.card.card-default.marginBottom", timeout=15000)
    except:
        return []

    cards = page.query_selector_all("div.card.card-default.marginBottom")

    for card in cards:
        try:
            h2_el = card.query_selector("h2.location-heading")
            if not h2_el:
                continue
            header = h2_el.inner_text().strip()

            distance = ""
            dist_el = card.query_selector("span#mi")
            if dist_el:
                distance = dist_el.inner_text().strip()
            
            # Simple 100 mile filter
            if distance:
                try:
                    miles = float(distance.split()[0])
                    if miles > 100:
                        log(f"Skipping {header} ({distance} > 100 miles)")
                        continue
                except:
                    pass

            dates_with_times = []
            date_cards = card.query_selector_all("div.date-card")
            for dc in date_cards:
                label = dc.get_attribute("aria-label") or ""
                if ", " in label:
                    label = label.split(", ", 1)[1]
                date_str = label.strip()
                if not date_str:
                    continue

                try:
                    dc.scroll_into_view_if_needed()
                    # Wait for scrolling to settle
                    page.wait_for_timeout(400)
                    # Natural click allows Playwright to wait for actionability
                    dc.click()
                    times = _get_time_slots(page)
                except Exception as e:
                    log(f"  Error clicking date {date_str}: {e}")
                    times = []

                dates_with_times.append({"date": date_str, "times": times})

            results.append({
                "center": header,
                "distance": distance,
                "available_dates": dates_with_times,
            })
        except Exception as e:
            log(f"Error scraping card: {e}")
            continue
    return results


def save_results(results: list):
    output = {
        "search_params": {
            "exam_section": config.EXAM_SECTION,
            "location": f"{config.CITY_OR_ZIP}, {config.STATE}",
            "start_date": config.START_DATE,
            "end_date": config.END_DATE,
        },
        "scraped_at": datetime.now().isoformat(),
        "centers": results,
    }
    with open("availability_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def notify(results: list):
    if not results:
        return

    blocks = []
    for center in results:
        dist = center.get("distance", "")
        dates = center.get("available_dates", [])
        if not dates:
            continue
        name = center.get("center", "Unknown").split(" - ")[0].strip()
        center_lines = [f"📍 {name} ({dist})" if dist else f"📍 {name}"]
        for d in dates:
            times = d.get("times", [])
            time_str = ", ".join(times) if times else "times TBD"
            center_lines.append(f"⏰ {_fmt_date_notify(d['date'])}: {time_str}")
        blocks.append("\n".join(center_lines))

    if not blocks:
        return

    message = f"{config.EXAM_SECTION}\n\n" + "\n\n".join(blocks)

    import subprocess
    try:
        subprocess.run(
            ["curl", "-s", "-d", message,
             "-H", "Title: CPA Slot Found!",
             "-H", "Priority: high",
             "-H", "Tags: white_check_mark",
             "https://ntfy.sh/zwyolo"],
            check=True, capture_output=True
        )
        log("Notification sent.")
    except Exception as e:
        log(f"Notification failed: {e}")


def search_once(page):
    try:
        page.goto(URL, wait_until="networkidle")
        
        # ── STEP 1: Select exam ──────────────────────────────────────
        page.select_option("#test_sponsor", label="Uniform CPA Exam")
        page.select_option("#testProgram", label="Uniform CPA Exam")
        page.select_option("#testSelector", label=config.EXAM_SECTION)
        log(f"Selected: {config.EXAM_SECTION}")

        page.click("#nextBtn")

        # ── STEP 2: Address & dates ──────────────────────────────────
        search_box = page.locator("#searchLocation")
        search_box.fill(f"{config.CITY_OR_ZIP}, {config.STATE}")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")

        modifier = "Meta" if platform.system() == "Darwin" else "Control"

        # Fill dates
        for selector, d_str in [("#locationStartDate", get_start_date()), ("#locationEndDate", get_end_date())]:
            inp = page.locator(selector)
            inp.click()
            page.keyboard.press(f"{modifier}+a")
            page.keyboard.press("Backspace")
            page.keyboard.type(d_str)
            page.keyboard.press("Tab")

        log(f"Dates: {get_start_date()} -> {get_end_date()}")

        # ── STEP 3: CAPTCHA ──────────────────────────────────────────
        def get_captcha_image_b64():
            img = page.wait_for_selector("img[src*='captcha'], .captcha img, img[alt*='captcha' i]")
            return base64.b64encode(img.screenshot()).decode('utf-8')

        def try_answer(answer):
            captcha_input = page.locator("input#captcha, input[placeholder*='captcha' i]").first
            captcha_input.fill(answer)
            page.click("#nextBtn")
            
            try:
                page.wait_for_function("""
                    () => document.querySelector('.card-default') || 
                          document.body.innerText.includes('not correct') ||
                          document.body.innerText.includes('No Availability Found')
                """, timeout=10000)
            except:
                pass

            error_exists = page.locator("//*[contains(text(),'not correct')]").is_visible()
            return not error_exists

        def refresh_captcha():
            refresh_btn = page.locator("//*[@title='Reset captcha']").first
            if refresh_btn.is_visible():
                refresh_btn.click()
                page.wait_for_timeout(500)

        solved = False
        for attempt in range(5):
            img_b64 = get_captcha_image_b64()
            answer = captcha_mod.solve(img_b64)
            log(f"CAPTCHA attempt {attempt + 1}: '{answer}'")
            if not answer:
                refresh_captcha()
                continue
            if try_answer(answer):
                log("CAPTCHA accepted.")
                solved = True
                break
            log("CAPTCHA wrong, refreshing...")
            refresh_captcha()

        if not solved:
            log("CAPTCHA failed.")
            return

        log("Search submitted. Waiting for results...")
        
        try:
            page.wait_for_function("""
                () => document.querySelector('div.card.card-default.marginBottom') || 
                      document.body.innerText.includes('No Availability Found')
            """, timeout=30000)
        except:
            pass

        if "No Availability Found" in page.inner_text("body"):
            log("No availability found for these dates.")
            results = []
        else:
            results = scrape_results(page)
        
        save_results(results)
        log(f"Saved {len(results)} result(s) to availability_results.json")
        notify(results)

    except Exception as e:
        log(f"Error during search: {e}")


def run():
    log(f"CPA checker (Playwright): {config.EXAM_SECTION} | {config.CITY_OR_ZIP}, {config.STATE} | every {config.CHECK_INTERVAL_MINUTES} min")

    with sync_playwright() as p:
        try:
            while True:
                try:
                    browser = p.chromium.launch(headless=config.HEADLESS, channel="chrome")
                except:
                    browser = p.chromium.launch(headless=config.HEADLESS)

                context = browser.new_context(
                    viewport={'width': 1280, 'height': 900},
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)

                try:
                    search_once(page)
                finally:
                    log("Search done. Closing browser in 1 min...")
                    time.sleep(60)
                    browser.close()
                    log("Browser closed.")

                wait_mins = config.CHECK_INTERVAL_MINUTES - 1
                log(f"Next check in {wait_mins} min...")
                time.sleep(wait_mins * 60)
        except KeyboardInterrupt:
            log("Stopped.")


if __name__ == "__main__":
    run()
