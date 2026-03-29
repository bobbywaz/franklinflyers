import os
import asyncio
from unittest.mock import MagicMock, patch

# Mocking FastAPI components since they are not installed in the environment
class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail

# Mocking the logger
logger = MagicMock()

# The function to test, copied from app/main.py (with minimal changes for testing)
async def get_api_key_test(api_key_header: str):
    admin_api_key = os.getenv("ADMIN_API_KEY")
    if not admin_api_key:
        logger.error("ADMIN_API_KEY not set in environment variables.")
        raise HTTPException(
            status_code=403,
            detail="API Key not configured."
        )
    if api_key_header == admin_api_key:
        return api_key_header
    raise HTTPException(
        status_code=403,
        detail="Could not validate credentials"
    )

async def run_tests():
    print("Running authentication logic tests...")

    # Test Case 1: Missing ADMIN_API_KEY in environment
    print("Test Case 1: ADMIN_API_KEY not set...")
    with patch.dict(os.environ, {}, clear=True):
        try:
            await get_api_key_test("some_key")
            print("FAILED: Expected HTTPException when ADMIN_API_KEY is not set")
        except HTTPException as e:
            assert e.status_code == 403
            assert e.detail == "API Key not configured."
            print("PASSED")

    # Test Case 2: Correct API Key
    print("Test Case 2: Correct API Key...")
    with patch.dict(os.environ, {"ADMIN_API_KEY": "secret123"}):
        try:
            result = await get_api_key_test("secret123")
            assert result == "secret123"
            print("PASSED")
        except HTTPException as e:
            print(f"FAILED: Unexpected HTTPException: {e.detail}")

    # Test Case 3: Incorrect API Key
    print("Test Case 3: Incorrect API Key...")
    with patch.dict(os.environ, {"ADMIN_API_KEY": "secret123"}):
        try:
            await get_api_key_test("wrong_key")
            print("FAILED: Expected HTTPException for incorrect key")
        except HTTPException as e:
            assert e.status_code == 403
            assert e.detail == "Could not validate credentials"
            print("PASSED")

    # Test Case 4: Missing API Key (None)
    print("Test Case 4: Missing API Key (None)...")
    with patch.dict(os.environ, {"ADMIN_API_KEY": "secret123"}):
        try:
            await get_api_key_test(None)
            print("FAILED: Expected HTTPException for missing key")
        except HTTPException as e:
            assert e.status_code == 403
            assert e.detail == "Could not validate credentials"
            print("PASSED")

if __name__ == "__main__":
    asyncio.run(run_tests())
