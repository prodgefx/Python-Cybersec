#!/usr/bin/env python3
"""
Site Scanner — Recursive link crawler using Selenium
Crawls a website, validates all internal links, and reports broken ones.

Usage:
    python site_scanner.py https://example.com
    python site_scanner.py https://example.com --depth 3 --timeout 10 --output report.json
"""
"""
# Default — errors saved to errors.csv automatically

# To run>>>>>
* python site_scanner.py https://cuk.ac.ke --no-verify

# Custom CSV filename
* python site_scanner.py https://cuk.ac.ke --no-verify --csv cuk_errors.csv

# CSV + full JSON report
* python site_scanner.py https://cuk.ac.ke --no-verify --csv errors.csv --output full_report.json

"""
import argparse
import csv
import json
import sys
import time
from collections import deque
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse   # still needed for joining/parsing only

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ─── Colour helpers (ANSI) ────────────────────────────────────────────────────

def green(s):  return f"\033[92m{s}\033[0m"
def red(s):    return f"\033[91m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def cyan(s):   return f"\033[96m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"
def dim(s):    return f"\033[2m{s}\033[0m"


# ─── Driver setup ─────────────────────────────────────────────────────────────

def build_driver(timeout: int = 15, headless: bool = True, verify_ssl: bool = True) -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    if not verify_ssl:
        opts.add_argument("--ignore-certificate-errors")
        opts.add_argument("--allow-insecure-localhost")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--log-level=3")
    opts.add_argument("--silent")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(log_path="/dev/null" if sys.platform != "win32" else "NUL")
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(timeout)
    return driver


# ─── Requests session ────────────────────────────────────────────────────────

def build_session(timeout: int = 15, verify_ssl: bool = True) -> requests.Session:
    """
    Create a requests.Session with:
      • a browser-like User-Agent so servers don't reject headless probes
      • automatic retries on transient network errors (not 4xx/5xx)
      • a shared timeout applied to every call
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://",  adapter)
    session.mount("https://", adapter)
    session.timeout    = timeout
    session.verify_ssl = verify_ssl          # custom attr read by check_url()
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print(yellow("⚠  SSL verification disabled — treat results with caution."))
    return session


def check_url(session: requests.Session, url: str) -> dict:
    """
    Validate a URL using requests (HEAD first, fall back to GET).
    Also catches urllib.error exceptions that bubble up through urllib3.
    Returns { ok, status, error_type, elapsed }
    """
    t0 = time.time()
    timeout    = getattr(session, "timeout", 15)
    verify_ssl = getattr(session, "verify_ssl", True)

    def _elapsed():
        return round(time.time() - t0, 2)

    try:
        resp = session.head(url, allow_redirects=True, timeout=timeout, verify=verify_ssl)
        if resp.status_code == 405:
            resp = session.get(url, allow_redirects=True, timeout=timeout, stream=True, verify=verify_ssl)
            resp.close()

        ok = resp.status_code < 400
        return {
            "ok":         ok,
            "status":     resp.status_code,
            "error_type": None if ok else "HTTP_ERROR",
            "elapsed":    _elapsed(),
        }

    # ── urllib.error exceptions (surface through urllib3/requests) ────────────
    except HTTPError as exc:
        return {"ok": False, "status": exc.code,
                "error_type": "urllib.error.HTTPError", "elapsed": _elapsed()}
    except URLError as exc:
        return {"ok": False, "status": str(exc.reason),
                "error_type": "urllib.error.URLError",  "elapsed": _elapsed()}

    # ── requests-native exceptions ────────────────────────────────────────────
    except requests.exceptions.SSLError as exc:
        msg = str(exc).split("(")[0].strip()
        return {"ok": False, "status": f"SSL_ERROR: {msg}",
                "error_type": "SSLError", "elapsed": _elapsed()}
    except requests.exceptions.ConnectionError as exc:
        msg = str(exc).split("(")[0].strip()
        return {"ok": False, "status": f"CONN_ERROR: {msg}",
                "error_type": "ConnectionError", "elapsed": _elapsed()}
    except requests.exceptions.Timeout:
        return {"ok": False, "status": "TIMEOUT",
                "error_type": "Timeout", "elapsed": _elapsed()}
    except requests.exceptions.TooManyRedirects:
        return {"ok": False, "status": "TOO_MANY_REDIRECTS",
                "error_type": "TooManyRedirects", "elapsed": _elapsed()}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "status": f"ERROR: {exc}",
                "error_type": type(exc).__name__, "elapsed": _elapsed()}


# ─── URL utilities ────────────────────────────────────────────────────────────

def normalise(url: str) -> str:
    """Strip fragment and trailing slash so duplicates are caught."""
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    return p._replace(fragment="", path=path, query=p.query).geturl()


def same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def is_crawlable(href: str) -> bool:
    """Return True only for http/https links worth crawling."""
    if not href:
        return False
    lower = href.lower()
    skip = ("mailto:", "tel:", "javascript:", "ftp:", "#", "data:")
    return not any(lower.startswith(s) for s in skip)


# ─── Link extractor ───────────────────────────────────────────────────────────

def extract_links(driver: webdriver.Chrome, base_url: str) -> list[dict]:
    """
    Return all <a href> links on the current page, each with:
      • url  — absolute URL
      • text — anchor text
      • valid — whether the href resolves / is well-formed
    """
    anchors = driver.find_elements(By.TAG_NAME, "a")
    links = []
    seen = set()

    for anchor in anchors:
        try:
            href = anchor.get_attribute("href") or ""
            text = anchor.text.strip()[:80] or dim("<no text>")
        except Exception:
            continue

        if not is_crawlable(href):
            continue

        absolute = normalise(urljoin(base_url, href))
        if absolute in seen:
            continue
        seen.add(absolute)

        links.append({"url": absolute, "text": text})

    return links


# ─── Page loader ──────────────────────────────────────────────────────────────

def load_page(driver: webdriver.Chrome, url: str, wait: int = 5) -> dict:
    """
    Navigate to `url`.
    Returns:
      { ok: bool, status: str, elapsed: float }
    """
    t0 = time.time()
    try:
        driver.get(url)
        # Brief wait for JS-heavy pages
        try:
            WebDriverWait(driver, wait).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass  # Body didn't appear — page still partially loaded; we continue

        elapsed = round(time.time() - t0, 2)
        title = driver.title or ""
        return {"ok": True, "status": "200", "elapsed": elapsed, "title": title}

    except TimeoutException:
        return {"ok": False, "status": "TIMEOUT", "elapsed": round(time.time() - t0, 2), "title": ""}
    except WebDriverException as exc:
        msg = str(exc).splitlines()[0]
        return {"ok": False, "status": f"ERROR: {msg}", "elapsed": round(time.time() - t0, 2), "title": ""}


# ─── Core crawler ─────────────────────────────────────────────────────────────

class SiteScanner:
    def __init__(
        self,
        start_url: str,
        *,
        max_depth: int = 0,          # 0 = unlimited
        max_pages: int = 0,          # 0 = unlimited
        timeout: int = 15,
        page_wait: int = 5,
        follow_external: bool = False,
        headless: bool = True,
        delay: float = 0.5,
        verify_ssl: bool = True,
    ):
        self.start_url      = normalise(start_url)
        self.base_domain    = urlparse(start_url).netloc
        self.max_depth      = max_depth
        self.max_pages      = max_pages
        self.timeout        = timeout
        self.page_wait      = page_wait
        self.follow_external = follow_external
        self.headless       = headless
        self.delay          = delay
        self.verify_ssl     = verify_ssl

        # State
        self.visited:  dict[str, dict] = {}   # url → result
        self.broken:   list[dict]      = []
        self.queue:    deque           = deque()   # (url, depth, referrer)
        self.driver:   webdriver.Chrome | None = None
        self.session:  requests.Session | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, csv_path: str = "errors.csv", all_links_path: str = "all_links.csv") -> dict:
        print(bold(f"\n🔍  Site Scanner"))
        print(f"    Start : {cyan(self.start_url)}")
        print(f"    Domain: {self.base_domain}")
        limits = []
        if self.max_depth:  limits.append(f"depth ≤ {self.max_depth}")
        if self.max_pages:  limits.append(f"pages ≤ {self.max_pages}")
        if limits: print(f"    Limits: {', '.join(limits)}")
        print()

        self.driver = build_driver(timeout=self.timeout, headless=self.headless, verify_ssl=self.verify_ssl)
        self.session = build_session(timeout=self.timeout, verify_ssl=self.verify_ssl)
        self.queue.append((self.start_url, 0, "—"))

        try:
            self._crawl_loop()
        finally:
            self.driver.quit()
            self.session.close()

        return self._build_report(csv_path=csv_path, all_links_path=all_links_path)

    # ── internals ─────────────────────────────────────────────────────────────

    def _crawl_loop(self):
        while self.queue:
            if self.max_pages and len(self.visited) >= self.max_pages:
                print(yellow(f"\n⚠  Page limit ({self.max_pages}) reached — stopping."))
                break

            url, depth, referrer = self.queue.popleft()

            if url in self.visited:
                continue
            if self.max_depth and depth > self.max_depth:
                continue

            # Mark as visited immediately to prevent re-queuing
            self.visited[url] = {}

            self._scan_page(url, depth, referrer)
            time.sleep(self.delay)

    def _scan_page(self, url: str, depth: int, referrer: str):
        indent = "  " * depth
        counter = len(self.visited)
        print(f"{indent}{dim(f'[{counter}]')} {cyan(url)}")

        # ── Step 1: validate the URL with requests (fast, no browser needed) ──
        check = check_url(self.session, url)
        result = {
            "ok":          check["ok"],
            "status":      check["status"],
            "error_type":  check.get("error_type"),
            "elapsed":     check["elapsed"],
            "title":       "",
            "depth":       depth,
            "referrer":    referrer,
            "links_found": 0,
        }

        status_str = (
            green(f"✓ {check['status']}  {check['elapsed']}s") if check["ok"]
            else red(f"✗ {check['status']}  [{check.get('error_type','')}]")
        )
        print(f"{indent}    {status_str}")

        if not check["ok"]:
            self.broken.append({
                "url":        url,
                "status":     check["status"],
                "error_type": check.get("error_type", ""),
                "referrer":   referrer,
                "depth":      depth,
                "elapsed":    check["elapsed"],
            })
            self.visited[url] = result
            return

        # ── Step 2: only crawl for links on internal pages via Selenium ───────
        is_internal = same_domain(url, self.start_url)
        if not is_internal:
            # External URL is reachable — record it but don't spider it
            self.visited[url] = result
            return

        selenium_result = load_page(self.driver, url, wait=self.page_wait)
        result["title"] = selenium_result.get("title", "")
        if result["title"]:
            print(f"{indent}    {dim(result['title'][:60])}")

        links = extract_links(self.driver, url)
        result["links_found"] = len(links)
        self.visited[url] = result

        queued = 0
        for link in links:
            child_url = link["url"]
            child_internal = same_domain(child_url, self.start_url)

            if child_url in self.visited:
                continue
            if not child_internal and not self.follow_external:
                continue
            if self.max_depth and depth + 1 > self.max_depth:
                continue

            self.queue.append((child_url, depth + 1, url))
            queued += 1

        if queued:
            print(f"{indent}    {dim(f'↳ queued {queued} new link(s)')}")

    def _build_report(self, csv_path: str = "errors.csv", all_links_path: str = "all_links.csv") -> dict:
        total   = len(self.visited)
        ok_cnt  = sum(1 for v in self.visited.values() if v.get("ok"))
        err_cnt = len(self.broken)

        report = {
            "start_url":    self.start_url,
            "scanned_at":   datetime.now().isoformat(timespec="seconds"),
            "total_pages":  total,
            "ok":           ok_cnt,
            "broken":       err_cnt,
            "pages":        self.visited,
            "broken_links": self.broken,
        }

        # ── CSV 1: errors only ────────────────────────────────────────────────
        if self.broken:
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=[
                    "url", "status", "error_type", "referrer", "depth", "elapsed"
                ])
                writer.writeheader()
                writer.writerows(self.broken)

        # ── CSV 2: all links with status ──────────────────────────────────────
        broken_urls = {b["url"] for b in self.broken}
        with open(all_links_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=[
                "url", "status", "is_broken", "error_type", "referrer", "depth",
                "title", "links_found", "elapsed"
            ])
            writer.writeheader()
            for url, data in self.visited.items():
                if not data:          # placeholder for pages not yet fully scanned
                    continue
                writer.writerow({
                    "url":         url,
                    "status":      data.get("status", ""),
                    "is_broken":   "YES" if url in broken_urls else "NO",
                    "error_type":  data.get("error_type") or "",
                    "referrer":    data.get("referrer", ""),
                    "depth":       data.get("depth", ""),
                    "title":       data.get("title", ""),
                    "links_found": data.get("links_found", ""),
                    "elapsed":     data.get("elapsed", ""),
                })

        # ── Terminal summary ──────────────────────────────────────────────────
        print(f"\n{'─'*55}")
        print(bold("  Scan complete"))
        print(f"  Pages scanned : {bold(str(total))}")
        print(f"  OK            : {green(str(ok_cnt))}")
        print(f"  Broken        : {red(str(err_cnt)) if err_cnt else green('0')}")
        print(f"  All links CSV : {cyan(all_links_path)}")
        if self.broken:
            print(f"  Errors CSV    : {cyan(csv_path)}")

        if self.broken:
            print(f"\n{bold('  Broken links:')}")
            for b in self.broken:
                print(f"    {red('✗')} {b['url']}")
                print(f"       status     : {red(str(b['status']))}")
                print(f"       error type : {yellow(b.get('error_type',''))}")
                print(f"       referrer   : {dim(b['referrer'])}")

        print(f"{'─'*55}\n")
        return report


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Recursive Selenium site scanner — crawls every link on a site.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python site_scanner.py https://example.com
  python site_scanner.py https://example.com --depth 2 --max-pages 100
  python site_scanner.py https://example.com --output results.json --no-headless
        """,
    )
    parser.add_argument("url",          help="Starting URL to scan (e.g. https://example.com)")
    parser.add_argument("--depth",      type=int, default=0,   metavar="N", help="Max crawl depth (0 = unlimited)")
    parser.add_argument("--max-pages",  type=int, default=0,   metavar="N", help="Max pages to visit (0 = unlimited)")
    parser.add_argument("--timeout",    type=int, default=15,  metavar="S", help="Page load timeout in seconds (default 15)")
    parser.add_argument("--wait",       type=int, default=5,   metavar="S", help="Extra JS wait after load (default 5)")
    parser.add_argument("--delay",      type=float, default=0.5, metavar="S", help="Delay between requests (default 0.5)")
    parser.add_argument("--no-verify",   action="store_true",   help="Skip SSL certificate verification (for sites with bad certs)")
    parser.add_argument("--external",   action="store_true",   help="Also follow external links")
    parser.add_argument("--no-headless",action="store_true",   help="Show the browser window")
    parser.add_argument("--output",     metavar="FILE",        help="Save full JSON report to FILE")
    parser.add_argument("--csv",        metavar="FILE",        default="errors.csv",    help="CSV file for broken links (default: errors.csv)")
    parser.add_argument("--all-links",  metavar="FILE",        default="all_links.csv", help="CSV file for all links with status (default: all_links.csv)")

    args = parser.parse_args()

    # Basic URL sanity check
    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        print(red(f"✗ Invalid URL: {args.url}"))
        sys.exit(1)

    scanner = SiteScanner(
        args.url,
        max_depth      = args.depth,
        max_pages      = args.max_pages,
        timeout        = args.timeout,
        page_wait      = args.wait,
        follow_external= args.external,
        headless       = not args.no_headless,
        delay          = args.delay,
        verify_ssl     = not args.no_verify,
    )

    report = scanner.run(csv_path=args.csv, all_links_path=args.all_links)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(green(f"✓ Report saved to {args.output}\n"))


if __name__ == "__main__":
    main()
