import asyncio
from database import list_all_tokens

async def main():
    tokens = await list_all_tokens()
    if not tokens:
        print("No tokens found in the database.")
    else:
        print("Found the following tokens:")
        for token in tokens:
            print(f"  User ID: {token.user_id}")
            print(f"    Access Token: {token.access_token[:15]}...")
            print(f"    Expires At: {token.expires_at}")

if __name__ == "__main__":
    asyncio.run(main())