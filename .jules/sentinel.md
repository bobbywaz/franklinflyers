## 2025-02-14 - Plaintext Admin Password

**Vulnerability:** The admin password was being stored and compared in plaintext in the SQLite database.
**Learning:** This exposes the application to severe risks if the database is ever dumped or read by unauthorized users. Since there is a default "changeme" password inserted on startup, it poses a direct plaintext exposure.
**Prevention:** Always use a slow cryptographic hash (e.g. PBKDF2, Argon2, bcrypt) for storing passwords and secrets, generating unique salts and avoiding custom hashing functions.
