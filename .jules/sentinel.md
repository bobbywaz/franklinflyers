## 2024-05-18 - Hash plaintext admin passwords
**Vulnerability:** Plaintext password storage and comparison in authentication flow.
**Learning:** Legacy plaintext passwords could be compromised or lead to pass-the-hash vulnerabilities. Constant-time comparison must be used for verify.
**Prevention:** Always use hashing algorithms like PBKDF2 with unique salts, securely store them, and use `secrets.compare_digest` to verify passwords while supporting fallback migration.
