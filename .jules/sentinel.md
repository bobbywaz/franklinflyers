## 2024-05-18 - [CRITICAL] Admin Password Stored in Plaintext
**Vulnerability:** The admin password was initialized and stored in plaintext in the database (Configuration key "admin_password"). Login and password change endpoints were performing plaintext string comparisons.
**Learning:** Security risks in early development stages often involve hardcoding default passwords or omitting hashing to save time. It's critical to review how initial setups create database configuration values.
**Prevention:** Always implement strong hashing (e.g. PBKDF2 with SHA-256) for any secrets or passwords stored in the database. When mitigating legacy plain text configurations, implement silent auto-migration upon successful login authentication.
