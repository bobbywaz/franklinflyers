## 2024-05-18 - [Fix Hardcoded Secrets]
**Vulnerability:** Admin passwords were created in plaintext in the database ("changeme") and compared against plaintext strings, which means if the database was compromised, the admin password would be immediately known.
**Learning:** Admin authentication lacks secure hashing. Storing passwords in plaintext is a critical security vulnerability.
**Prevention:** Always use secure hashing (e.g., PBKDF2) to store passwords. Implement `hashlib.pbkdf2_hmac` and use `secrets.compare_digest` for constant-time comparisons to prevent timing attacks.
