## 2026-10-22 - Fix Plaintext Password Storage
**Vulnerability:** Admin passwords were created and stored as plain text, leading to critical risk if database was dumped. Authentication also used a simple equality string comparison.
**Learning:** Legacy systems might rely on older, insecure plaintext default passwords that later require migration scripts to safely upgrade to hashes like PBKDF2. Length-based checks for hashing algorithms are fragile because the length depends on the byte encoding of the salt/key.
**Prevention:** Store passwords via one-way algorithms like PBKDF2 immediately. Compare them securely using `secrets.compare_digest` to prevent timing attacks. Support legacy fallbacks securely during migrations.
