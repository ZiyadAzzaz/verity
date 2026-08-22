"""Capture pitch screenshots of Verity's best artifacts.

Uses Chrome's own headless screenshot mode rather than Playwright or Selenium, because
neither is installed and neither is worth adding as a dependency for this. Chrome is already
on the machine.

    python scripts/capture_screenshots.py

Writes PNGs to docs/assets/screenshots/.

Captures the architecture page and the filed verdict Issue. Both repositories are public,
so no signed-in session is needed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "screenshots"
ISSUE_URL = "https://github.com/ZiyadAzzaz/verity-reports/issues/1"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def find_browser() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return shutil.which("chrome") or shutil.which("chromium") or shutil.which("google-chrome")


def capture(browser: str, url: str, destination: Path, width: int, height: int) -> bool:
    """One headless screenshot. A throwaway profile keeps this out of the real one."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="verity-shot-") as profile:
        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",  # retina-quality output for a pitch deck
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            f"--screenshot={destination}",
            "--virtual-time-budget=8000",  # let fonts and layout settle
            url,
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if destination.is_file() and destination.stat().st_size > 0:
        size_kb = destination.stat().st_size / 1024
        print(f"  [ OK ] {destination.name}  ({size_kb:,.0f} KB, {width}x{height} @2x)")
        return True
    print(f"  [FAIL] {destination.name}")
    detail = (result.stderr or result.stdout or "").strip()[:300]
    if detail:
        print(f"         {detail}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="extra URL to capture")
    parser.add_argument("--name", help="filename for --url (without extension)")
    args = parser.parse_args()

    browser = find_browser()
    if browser is None:
        print("No Chrome or Edge found. Take the screenshots manually instead.")
        return 2
    print(f"browser: {browser}\noutput : {OUT}\n")

    ok = True
    architecture = ROOT / "verity-architecture.html"
    if architecture.is_file():
        url = architecture.resolve().as_uri()
        # Tall window so the whole page lands in one image rather than a fold.
        ok &= capture(browser, url, OUT / "architecture-full.png", 1440, 6200)
        ok &= capture(browser, url, OUT / "architecture-hero.png", 1440, 900)
    else:
        print("  verity-architecture.html not found")
        ok = False

    # The filed verdict. Two crops: a tight one for a slide, and the whole page for the
    # repo. The tight height stops just past the debug trail, which is where the Debug
    # Agent's refusal to fabricate lives - that sentence is the pitch.
    ok &= capture(browser, ISSUE_URL, OUT / "issue-verdict.png", 1440, 1620)
    ok &= capture(browser, ISSUE_URL, OUT / "issue-verdict-full.png", 1440, 2400)

    if args.url:
        name = args.name or "capture"
        ok &= capture(browser, args.url, OUT / f"{name}.png", 1440, 2400)

    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
