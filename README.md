Python Cybersecurity Tools
Experimental Networking & Security Utilities

This repository contains a collection of Python-based scripts designed for exploring core cybersecurity concepts, network reconnaissance, and automated vulnerability research.
🛠️ Included Utilities
1. TCP Port Scanner (port_scanner.py)

A reconnaissance tool that maps the attack surface of a target host by identifying open and listening TCP ports.

    Logic: Utilizes the socket library to perform connection attempts across a defined range.

    Ideal for: Understanding service availability and network footprinting.

Usage
Bash

python3 port_scanner.py

2. Directory Fuzzer (fuzz.py)

A high-efficiency fuzzer designed to discover hidden directories and sensitive files on a web server using wordlist-based brute forcing.

    Logic: Processes input via stdin to allow for seamless integration with other CLI tools.

    Ideal for: Identifying unlinked assets and misconfigured web endpoints.

Usage

Pipe your preferred wordlist directly into the script:
Bash

cat <directory_wordlist> | python3 fuzz.py

🚀 Future Roadmap

    [ ] Implement Multi-threading for faster port scanning.

    [ ] Add User-Agent randomization to the fuzzer to bypass basic WAFs.

    [ ] Integration of logging for persistent scan results.

⚠️ Legal & Ethical Disclaimer

For Educational and Authorized Testing Purposes Only. The software provided in this repository is intended for academic study and authorized security audits. Unauthorized access to computer systems is illegal. Vela Software Solutions and its contributors hold no liability for any misuse, data loss, or damage caused by these tools. Always obtain written consent before testing any infrastructure.

3. Site Scanner (web_crawler.py)

A recursive website link scanner built with **Python, Selenium, and Requests** that crawls a website, validates internal links, and reports broken links.

It works by:

- Crawling pages recursively from a starting URL
- Extracting all `<a href="">` links on each page
- Validating links using `requests`
- Loading internal pages with Selenium for JavaScript-rendered content
- Detecting:
  - Broken links
  - SSL issues
  - Connection errors
  - Timeouts
  - Redirect issues
- Exporting scan results to:
  - `errors.csv` → broken links only
  - `all_links.csv` → all scanned links and their statuses
  - Optional JSON report

---

## Features

✅ Recursive crawling of internal pages  
✅ Optional external link scanning  
✅ Handles JavaScript-heavy websites using Selenium  
✅ Detects broken links (404s, timeouts, SSL issues, redirects, etc.)  
✅ Generates CSV reports  
✅ Optional JSON export  
✅ Headless browser support  
✅ Custom crawl depth and page limits  

---

## Requirements

Make sure you have:

- Python 3.8+
- Google Chrome installed
- ChromeDriver installed (must match your Chrome version)

### Install dependencies

```bash
pip install selenium requests urllib3
```

---

## How to Run

### Basic scan

```bash
python site_scanner.py https://example.com
```

Scans the website recursively and saves:

- `errors.csv`
- `all_links.csv`

---

### Scan a site with SSL verification disabled

Useful for sites with invalid SSL certificates.

```bash
python site_scanner.py https://cuk.ac.ke --no-verify
```

---

### Save broken links to a custom CSV file

```bash
python site_scanner.py https://cuk.ac.ke --no-verify --csv cuk_errors.csv
```

---

### Save full JSON report

```bash
python site_scanner.py https://cuk.ac.ke --no-verify --csv errors.csv --output full_report.json
```

---

### Limit crawl depth

```bash
python site_scanner.py https://example.com --depth 3
```

---

### Limit number of pages scanned

```bash
python site_scanner.py https://example.com --max-pages 100
```

---

### Scan external links too

```bash
python site_scanner.py https://example.com --external
```

---

### Run with visible browser window

```bash
python site_scanner.py https://example.com --no-headless
```

---

## Output Files

### `errors.csv`

Contains only broken links:

- URL
- Status
- Error type
- Referrer page
- Depth
- Response time

---

### `all_links.csv`

Contains all scanned links:

- URL
- Status
- Broken status
- Error type
- Referrer
- Page title
- Links found
- Response time

---

### JSON Report (optional)

Use:

```bash
--output report.json
```

This generates a full JSON report containing all scan details.

---

## Example Use Cases

- Website maintenance
- QA testing
- SEO audits
- Finding broken internal links
- Checking migrated websites
- Monitoring website health

---

## Example Output

```bash
🔍 Site Scanner
Start : https://example.com
Domain: example.com

[1] https://example.com
✓ 200

[2] https://example.com/about
✓ 200

[3] https://example.com/contact
✗ 404

Scan complete
Pages scanned: 3
Broken: 1
```

---

## Disclaimer

Use responsibly and only scan websites you own or have permission to test.

---

## Author

Built with Python 🐍 using Selenium + Requests
