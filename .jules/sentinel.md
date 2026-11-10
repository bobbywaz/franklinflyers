## 2025-02-14 - Use PBKDF2 for admin password
**Vulnerability:** The admin password is stored in plaintext in the database (Configuration key `admin_password`) and checked in plaintext during login. This is a critical security vulnerability.
**Learning:** Hardcoded default passwords ('changeme') were stored in plaintext in the database during application startup. Passwords must be hashed.
**Prevention:** Implement PBKDF2 hashing for all stored passwords. Compare using constant-time comparison `secrets.compare_digest`. Ensure the default password is also hashed on initialization. Fallback logic to check if a stored password is in plaintext and update it to a hash upon first successful login is a good practice when upgrading an existing application.
