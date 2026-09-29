## 2024-05-24 - Hash Admin Password
**Vulnerability:** Admin passwords are unnecessarily stored in plaintext, vulnerable if db is leaked. Furthermore they are compared using `!=`, making them vulnerable to timing attacks.
**Learning:** Admin authentication can be vastly improved by applying a hash function to the password before storage.
**Prevention:** Use PBKDF2 hash on all passwords before saving them. Use `secrets.compare_digest` to check passwords.
