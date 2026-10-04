## 2026-10-04 - [High] Secure Password Hashing
**Vulnerability:** Admin passwords were fundamentally stored in plain text leading to immediate risk if the database was compromised.
**Learning:** Legacy configurations frequently rely on unencrypted direct comparisons. The transition to secure PBKDF2 hashing demands a robust migration step for preexisting unhashed entries to prevent locking administrators out while ensuring data safety forward.
**Prevention:** Always default to salted password hashing out of the gate with functions mapping `get_password_hash` and `verify_password` via `hashlib` and `secrets` built-in libraries.
