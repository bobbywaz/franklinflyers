## 2024-05-18 - [Fix Plaintext Password Storage]
**Vulnerability:** Admin passwords were stored in plaintext in the database (configuration table), exposing them in case of a DB dump or unauthorized read access.
**Learning:** Found in `app/main.py` where a default "changeme" password was stored unhashed, and authentication directly compared plaintext passwords.
**Prevention:** Always use strong password hashing algorithms like PBKDF2, bcrypt, or Argon2 before storing passwords. Implement hashing utilities early in the development lifecycle.
