"""
CAPTCHA solving helpers.
Supports: 2captcha API, pytesseract OCR, manual fallback.
"""

import time
import base64
import urllib.request
import urllib.parse
import urllib.error
from io import BytesIO
from typing import Optional

import config


def solve(image_b64: str) -> str:
    """
    Given a base64-encoded CAPTCHA image, return the solved text.
    Tries the method set in config.CAPTCHA_SOLVER.
    """
    method = getattr(config, "CAPTCHA_SOLVER", "manual")

    if method == "ddddocr":
        result = _solve_ddddocr(image_b64)
        if result:
            return result
        print("[CAPTCHA] ddddocr failed, falling back to manual.")

    elif method == "2captcha":
        result = _solve_2captcha(image_b64)
        if result:
            return result
        print("[CAPTCHA] 2captcha failed, falling back to manual.")

    elif method == "ocr":
        result = _solve_ocr(image_b64)
        if result:
            return result
        print("[CAPTCHA] OCR failed, falling back to manual.")

    # return _solve_manual()


def _solve_ddddocr(image_b64: str) -> Optional[str]:
    try:
        import ddddocr
        img_bytes = base64.b64decode(image_b64)
        ocr = ddddocr.DdddOcr(show_ad=False)
        ocr.set_ranges("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz")
        result = ocr.classification(img_bytes)
        result = result.strip().upper()  # CAPTCHA is case-insensitive uppercase
        print(f"[CAPTCHA] ddddocr result: {result}")
        return result if result else None
    except ImportError:
        print("[CAPTCHA] ddddocr not installed. Run: pip install ddddocr")
        return None
    except Exception as e:
        print(f"[CAPTCHA] ddddocr error: {e}")
        return None


def _solve_2captcha(image_b64: str) -> Optional[str]:
    api_key = getattr(config, "CAPTCHA_2CAPTCHA_API_KEY", "")
    if not api_key or api_key == "YOUR_2CAPTCHA_API_KEY":
        print("[CAPTCHA] No 2captcha API key set.")
        return None

    try:
        # Submit CAPTCHA
        submit_url = "http://2captcha.com/in.php"
        data = urllib.parse.urlencode({
            "key": api_key,
            "method": "base64",
            "body": image_b64,
            "json": 1,
        }).encode()
        req = urllib.request.Request(submit_url, data=data)
        with urllib.request.urlopen(req, timeout=30) as resp:
            import json
            result = json.loads(resp.read())

        if result.get("status") != 1:
            print(f"[CAPTCHA] 2captcha submit error: {result}")
            return None

        captcha_id = result["request"]
        print(f"[CAPTCHA] Submitted to 2captcha (id={captcha_id}). Waiting for result...")

        # Poll for result
        for _ in range(24):  # up to ~2 minutes
            time.sleep(5)
            poll_url = (
                f"http://2captcha.com/res.php"
                f"?key={api_key}&action=get&id={captcha_id}&json=1"
            )
            with urllib.request.urlopen(poll_url, timeout=15) as resp:
                poll = json.loads(resp.read())

            if poll.get("status") == 1:
                answer = poll["request"]
                print(f"[CAPTCHA] Solved by 2captcha: {answer}")
                return answer
            if poll.get("request") != "CAPCHA_NOT_READY":
                print(f"[CAPTCHA] 2captcha error: {poll}")
                return None

        print("[CAPTCHA] 2captcha timed out.")
        return None

    except Exception as e:
        print(f"[CAPTCHA] 2captcha exception: {e}")
        return None


def _solve_ocr(image_b64: str) -> Optional[str]:
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageOps

        img_data = base64.b64decode(image_b64)
        img = Image.open(BytesIO(img_data)).convert("L")  # grayscale
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SHARPEN)
        # Threshold to pure black/white
        img = img.point(lambda x: 0 if x < 140 else 255)

        text = pytesseract.image_to_string(
            img,
            config="--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        ).strip()
        text = "".join(c for c in text if c.isalnum())
        if text:
            print(f"[CAPTCHA] OCR result: {text}")
            return text
        return None
    except ImportError:
        print("[CAPTCHA] pytesseract/Pillow not installed.")
        return None
    except Exception as e:
        print(f"[CAPTCHA] OCR error: {e}")
        return None


def _solve_manual() -> str:
    print("")
    print("=" * 60)
    print("CAPTCHA: Type the text shown in the browser window:")
    answer = input(">>> ").strip()
    print("=" * 60)
    return answer
