## 2024-11-06 - Plaintext Admin Password Storage
**Vulnerability:** Admin passwords were stored and verified in plaintext.
**Learning:** Hardcoded/plaintext secrets expose entire systems on DB breach.
**Prevention:** Always hash passwords before storing using strong algorithms like PBKDF2.
