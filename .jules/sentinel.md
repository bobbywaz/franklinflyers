## 2024-03-24 - Plaintext Admin Password Storage
**Vulnerability:** Admin passwords were created and stored as plain text in the database (`Configuration` table).
**Learning:** Storing passwords as plain text is a critical vulnerability; it exposes credentials if the database is compromised.
**Prevention:** Always use a secure key derivation function like PBKDF2, bcrypt, or Argon2 to hash passwords before storing them.

## 2024-03-24 - Plaintext Admin Password Storage Fixed
**Vulnerability:** Admin password was checked using plain text equality and stored as plain text.
**Learning:** Checking and storing plain text passwords is a vulnerability; it exposes credentials if the DB is compromised.
**Prevention:** Always use `hashlib.pbkdf2_hmac` with a salt (e.g. from `secrets.token_hex`) and store the hash instead of plain text, and verify against the hash.
