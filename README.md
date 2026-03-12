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
