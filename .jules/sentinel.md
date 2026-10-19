## 2024-05-24 - Secure Password Hashing
**Vulnerability:** Admin password stored and verified in plaintext.
**Learning:** Timing attacks are possible if string comparison is used. Also plaintext passwords expose user credentials.
**Prevention:** Use PBKDF2 and secrets.compare_digest for secure password hashing and verification.
