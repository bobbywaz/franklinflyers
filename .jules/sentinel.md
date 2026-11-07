## 2024-11-07 - Store Admin Password securely using PBKDF2
**Vulnerability:** The admin password was stored in plaintext in the database (as `changeme`), exposing it to anyone with database access.
**Learning:** It existed because it was quick to initialize during development but wasn't updated to be secure.
**Prevention:** Use a secure hash algorithm (e.g., PBKDF2 via `hashlib` with `secrets` for salting) to store all passwords, and never store passwords as plaintext.
