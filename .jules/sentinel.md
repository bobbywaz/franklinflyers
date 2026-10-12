## YYYY-MM-DD - Fix Plaintext Admin Password

**Vulnerability:** Admin passwords were created in plaintext as "changeme" and later verified by direct string comparison to the database. They were also allowed to be changed with direct plaintext database inserts.
**Learning:** The database model was fine, however `app/main.py` directly handled string checks.
**Prevention:** In the future when building authentication forms with Python, ensure to incorporate standard libraries such as `secrets` and `hashlib` to hash any passwords stored and securely verify any inputted plaintext strings using `pbkdf2_hmac` and `secrets.compare_digest`.
