# Security Policy

## Supported Versions

We provide security updates for the following versions of ConnectLife MCP Server:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest| :x:                |

We recommend always running the latest container image or installing the latest source version.

---

## Reporting a Vulnerability

If you discover a security vulnerability in ConnectLife MCP Server, **please do not open a public issue**.

Instead, use one of the following private channels:

1. **GitHub Private Vulnerability Reporting** (preferred)  
   Go to **Security → Advisories → Report a vulnerability** on this repository:  
   <https://github.com/OldemarJesus/connectlife-mcp/security/advisories/new>

2. **Email the maintainers**  
   Send a description of the issue to: **security@example.com**  
   *(Replace with a real maintainer email address once available.)*

### What to include

- A clear description of the vulnerability and its impact.
- Steps to reproduce, including minimal code or configuration snippets if applicable.
- The affected version(s) or commit SHA.
- Any suggested mitigations or fixes.
- A PGP key or secure contact method if you'd like encrypted replies (we can provide one on request).

### Response timeline

| Step | Timeframe |
|------|-----------|
| Initial acknowledgement | Within 48 hours |
| Assessment & reproduction | Within 7 days |
| Fix or mitigation plan | Within 30 days |
| Disclosure (coordinated) | After patch is released |

We will keep you informed throughout the process and credit you in the advisory unless you prefer to remain anonymous.

---

## Security Best Practices for Users

- **Never hard-code credentials.** Always pass ConnectLife credentials via environment variables (`MCP_CONNECTLIFE_USERNAME`, `MCP_CONNECTLIFE_PASSWORD`) — never through tool parameters or commit them to version control.
- **Run the server on localhost only** (`127.0.0.1:8000`) unless you have additional network security in place.
- **Use the latest container image** to ensure you have all security patches.
- **Review logs** for unusual access patterns; the server logs connection and authentication events via the module `_LOGGER`.

---

## Security Scanning

The project runs automated security checks in CI:

- [`bandit`](https://bandit.readthedocs.io/) — static analysis for common Python security issues (`bandit -r src`).
- Dependabot alerts for outdated dependencies.
, including `pip-audit` scans for known vulnerabilities in Python dependencies.

See `CONTRIBUTING.md` for how to run these checks locally.

---

## Acknowledgements

We thank all security researchers and community members who responsibly disclose vulnerabilities and help keep this project safe.
