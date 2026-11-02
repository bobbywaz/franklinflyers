## 2024-05-15 - [Plaintext Password Storage]
**Vulnerability:** The admin password was stored in plaintext in the configurations table.
**Learning:** It existed because it was a simple configuration table but it poses a major security risk.
**Prevention:** Always use hashing algorithms like PBKDF2, bcrypt, or Argon2 before storing passwords, and verify them securely without storing them in plaintext.
