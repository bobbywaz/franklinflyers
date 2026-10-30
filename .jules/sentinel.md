## 2025-02-14 - Fix Hardcoded Admin Password and Implement Password Hashing
**Vulnerability:** The default admin password ("changeme") was stored in plain text in the database when initializing it and it wasn't hashed when checked or changed.
**Learning:** Hardcoded passwords and plain text passwords stored in the database are major security vulnerabilities.
**Prevention:** Implement PBKDF2 with SHA256 and 100,000 iterations to hash passwords using `hashlib` and `secrets` to ensure securely generated salts, and avoid hardcoding passwords, even default ones, in plain text.
