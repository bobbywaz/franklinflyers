## 2025-02-27 - Plaintext Admin Password Storage
**Vulnerability:** The default admin password was stored in the configuration table as a plaintext string 'changeme'.
**Learning:** Storing passwords in plaintext allows any user with read access to the database to retrieve passwords directly, which violates basic security best practices.
**Prevention:** Always use a secure cryptographic hash function, such as PBKDF2 with a random salt, to store password hashes instead of raw passwords. Use `secrets.compare_digest` during validation to prevent timing attacks.
