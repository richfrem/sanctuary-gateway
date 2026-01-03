# -*- coding: utf-8 -*-
import asyncio
from sqlalchemy import select
from mcpgateway.db import get_db, EmailApiToken, EmailUser

async def verify_db_tokens():
    db = next(get_db())
    try:
        print("--- Existing Users ---")
        users = db.execute(select(EmailUser)).scalars().all()
        for u in users:
            print(f"User: {u.email} (Admin: {u.is_admin})")
            
        print("\n--- Registered API Tokens ---")
        tokens = db.execute(select(EmailApiToken)).scalars().all()
        if not tokens:
            print("No tokens found in database.")
        for t in tokens:
            print(f"ID: {t.id} | Name: {t.name}")
            print(f"    User: {t.user_email}")
            print(f"    Team ID: {t.team_id}") # Added this line
            print(f"    Active: {t.is_active}")
            print(f"    Description: {t.description}")
            print("-" * 40)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_db_tokens())
