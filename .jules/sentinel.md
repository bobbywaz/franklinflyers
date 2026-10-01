## 2025-02-13 - Password format detection

**Vulnerability:** Weak structural checks (like just checking for a `$`) could cause false positives, potentially locking out admins whose plaintext passwords happened to contain that character, or triggering verification logic with invalid data.
**Learning:** When migrating plaintext passwords to hashed versions, exact format requirements (e.g. `len(val) == 97` and `val[32] == '$'`) are necessary to definitively identify PBKDF2 hashes generated with `secrets.token_hex(16)`.
**Prevention:** Always use precise, strict structural validation rather than simple substring checks when disambiguating sensitive payload formats to avoid accidental breakage or logic bypasses.
