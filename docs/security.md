# Static Security & Secret Detection Architecture

## Overview
CodeAtlas incorporates multi-layer static security analysis executed during repository ingestion. Scans run asynchronously in workers and output structured findings categorized by risk severity.

---

## 1. Detection Modules

### 1.1 Secret Detection
- Shannon entropy calculations combined with regex patterns to detect:
  - AWS access keys, secret keys, session tokens
  - GitHub Personal Access Tokens (classic & fine-grained)
  - Generic private keys (RSA, SSH, PGP)
  - JWT strings, Slack webhooks, database connection strings with passwords
- **Strict Masking Rule**: Raw secrets are **never** persisted to PostgreSQL, never written to logs, and never returned in API payloads. All evidence is masked:
  - Example: `ghp_1234567890abcdef1234567890abcdef12` -> `ghp_1234...ef12`

### 1.2 Dangerous Patterns & Sinks
- **SQL Injection**: Raw string formatting / concatenation in database query calls.
- **Command Injection**: Unsafe `subprocess.Popen(..., shell=True)` or `os.system(...)` with dynamic arguments.
- **Insecure Deserialization**: `pickle.loads(...)`, `yaml.load(..., Loader=yaml.Loader)`.
- **Weak Cryptography**: Usage of MD5, SHA1, DES for secure hashing or encryption.
- **Insecure CORS / Auth**: Permissive CORS (`Allow-Origin: *` with credentials) or hardcoded test credentials.

---

## 2. Severity Classification
- `CRITICAL`: Hardcoded production secrets, unauthenticated remote code execution sinks.
- `HIGH`: SQL injection vulnerabilities, unsafe deserialization.
- `MEDIUM`: Weak cryptographic algorithms, insecure file permissions.
- `LOW`: Hardcoded IP addresses, disabled SSL verification in development blocks.
