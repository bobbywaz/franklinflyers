## 2025-02-27 - Hash Admin Passwords
**Vulnerability:** Admin passwords were stored in plaintext in the SQLite database and initialized as `changeme`.
**Learning:** Legacy configurations frequently lack secure storage for administrative credentials, risking full site takeover if the database file is accessed.
**Prevention:** Always implement PBKDF2 with a salt for hashing, migrate existing plaintext passwords seamlessly by checking the hash string format securely (`len == 97` and char 32 is `$`), and use `secrets.compare_digest` for all comparisons.
