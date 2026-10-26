## 2026-10-26 - [CRITICAL] Fix plaintext password storage
**Vulnerability:** Admin passwords were being stored in plaintext in the configurations database, exposing them directly if the database were compromised.
**Learning:** The existing implementation initialized and handled passwords via simple string comparison (`password != stored_pass.value`). No secure cryptographic hash function was in place for configuration values.
**Prevention:** Always use secure, standard password hashing schemes like PBKDF2 with a salt and high iteration count (e.g. `hashlib.pbkdf2_hmac` with >100k iterations and `secrets.token_hex`) to protect stored credentials against exposure. Employ constant-time string comparison (`secrets.compare_digest`) to prevent timing attacks.
