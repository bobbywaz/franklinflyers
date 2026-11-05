## 2024-05-18 - Admin Password Stored in Plaintext
**Vulnerability:** The admin password was stored in the configuration table in plaintext, and verified via plain string comparison.
**Learning:** Initializing default configurations during app startup can easily lead to hardcoded plaintexts in the database if not careful.
**Prevention:** Always implement password hashing (like PBKDF2 with a salt) from the start. Verify inputs using secure hashing comparisons, casting `await request.form()` variables properly before hashing to prevent errors. Provide fallback validation to support migrating older plaintext databases.
