import asyncio
from database import test_connection  # Ensure this matches the file structure of your project
import logging

logging.basicConfig(level=logging.DEBUG)
async def main():
    await test_connection()

if __name__ == "__main__":
    asyncio.run(main())
