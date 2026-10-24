## 2024-05-24 - Secure Password Hashing
**Vulnerability:** Admin passwords were stored in plaintext in the SQLite database, exposing them if the database was compromised.
**Learning:** Implemented PBKDF2 hashing using `hashlib.pbkdf2_hmac`. Made the `verify_password` function fallback to a plaintext check if the hash prefix was not found, ensuring that the existing plain text password ("changeme") remains functional until the user updates it via the admin panel.
**Prevention:** Avoid storing raw passwords; always hash them securely and accommodate legacy strings safely during migration.
