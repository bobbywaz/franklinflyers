
## 2026-10-21 - Secure Admin Password Storage
**Vulnerability:** Admin passwords were stored in plaintext in the database (SQLite `configurations` table). This exposed admin credentials if the database file was accessed.
**Learning:** Even default passwords or simple internal auth flows need cryptographic protection. Additionally, timing attacks could be possible via simple string comparisons (`==`).
**Prevention:** Implement PBKDF2 hashing (`hashlib.pbkdf2_hmac`) with a randomly generated salt for storing passwords. Use `secrets.compare_digest` when verifying passwords to prevent timing attacks. Ensure form inputs are properly cast to strings before encoding.
