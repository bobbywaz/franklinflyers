## 2024-10-11 - [Title: Fix plaintext admin password storage]
**Vulnerability:** The application was storing and checking the admin password (`admin_password` inside the `Configuration` DB table) in plaintext.
**Learning:** During initialization, a default plaintext password was added to the DB, and endpoints like `/admin/login` and `/admin/change-password` were comparing passwords using direct string equality. Storing secrets in plaintext is a critical vulnerability.
**Prevention:** Using PBKDF2 hash with a random salt via `hashlib` and checking for equivalence securely utilizing `secrets.compare_digest` in `verify_password`.
