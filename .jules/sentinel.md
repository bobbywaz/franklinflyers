## 2024-10-17 - Migration to Hashed Passwords
**Vulnerability:** Plaintext passwords were used for the admin authentication, allowing credential theft in case of database leak.
**Learning:** When migrating plaintext passwords to hashes in a live application where some configurations might still be plaintext, it is critical to implement precise structural checks (`len(string) == 97 and string[32] == "$"`) instead of loose substring checks (`"$" in string`) to avoid false positives and incorrectly identifying valid plaintext passwords as hashes.
**Prevention:** Always enforce strong cryptography for stored secrets and plan out precise backward-compatibility logic for migrating legacy plaintexts to prevent logic bypasses.
