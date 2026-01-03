import asyncio
import uuid
import sys
import os
from sqlalchemy import select, and_

# Add /app to sys.path to ensure we can import mcpgateway
sys.path.append("/app")

from mcpgateway.db import SessionLocal, EmailUser, EmailApiToken
from mcpgateway.services.token_catalog_service import TokenCatalogService

async def bootstrap_token(name: str):
    """
    Bootstrap an API token within the Gateway container.
    This registers the token in the database so it appears in the UI.
    """
    db = SessionLocal()
    try:
        # 1. Find an admin user to own the token
        result = db.execute(select(EmailUser).where(EmailUser.is_admin == True))
        user = result.scalars().first()
        
        if not user:
            # Fallback to any user if no admin exists
            result = db.execute(select(EmailUser))
            user = result.scalars().first()
        
        if not user:
            print("ERROR: No users found in database. Bootstrap failed.")
            return None

        print(f"Assigning token to user: {user.email}")
        
        service = TokenCatalogService(db)
        
        # 2. Check for existing token and deactivate it to allow re-creation with same name
        token_result = db.execute(
            select(EmailApiToken).where(and_(
                EmailApiToken.user_email == user.email,
                EmailApiToken.name == name,
                EmailApiToken.is_active == True
            ))
        )
        existing = token_result.scalars().first()
        if existing:
            print(f"Deactivating existing token '{name}' for user {user.email}")
            existing.is_active = False
            db.commit()

        # 3. Create fresh token via service
        # This will handle JWT generation and database registration
        try:
            token_record, raw_token = await service.create_token(
                user_email=user.email,
                name=name,
                description="Automated Gateway API Token (Bootstrap)",
                expires_in_days=365
            )
            
            # Print specifically formatted delimiters for the outer script to capture
            print(f"BOOTSTRAP_TOKEN_START:{raw_token}:BOOTSTRAP_TOKEN_END")
            return raw_token
        except Exception as e:
            print(f"ERROR calling service.create_token: {e}")
            return None
            
    finally:
        db.close()

if __name__ == "__main__":
    token_name = sys.argv[1] if len(sys.argv) > 1 else "sanctuary gateway api"
    asyncio.run(bootstrap_token(token_name))
