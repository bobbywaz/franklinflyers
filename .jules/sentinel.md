## 2024-11-04 - Fix Plaintext Admin Password Storage
**Vulnerability:** Admin passwords were stored and compared in plaintext in the database configurations table.
**Learning:** Storing plaintext passwords exposes them completely if the database is dumped or leaked, violating basic security principles. Also needed to migrate legacy passwords transparently on login.
**Prevention:** Always use a strong one-way cryptographic hash with salt (e.g., PBKDF2, Argon2, bcrypt) for storing passwords.
