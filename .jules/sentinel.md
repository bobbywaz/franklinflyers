## 2025-02-14 - Admin Password Hashing
**Vulnerability:** Admin passwords were created, stored, and compared in plaintext, exposing them if the database was compromised. String comparisons were vulnerable to timing attacks.
**Learning:** Legacy systems often require backward compatibility when migrating auth mechanisms.
**Prevention:** Always hash passwords (e.g. PBKDF2) and use `secrets.compare_digest` for secure string comparison to prevent timing attacks. Support a secure fallback check based on string length and structure to transition legacy plaintext entries safely on next update.
