## 2024-03-24 - Plaintext Password Storage
**Vulnerability:** Admin passwords were stored in plaintext in the database, allowing anyone with DB access to compromise admin accounts.
**Learning:** Legacy plaintext fallbacks must be carefully implemented to prevent pass-the-hash attacks (e.g., rejecting comparisons if the stored value is already a hash). Form data can be None/UploadFile, so explicit string typing is required before hashing.
**Prevention:** Store passwords using PBKDF2 with a unique salt. Use secrets.compare_digest for constant-time comparisons.
