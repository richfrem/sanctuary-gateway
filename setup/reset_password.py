import sys
import os
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure /app is in path to import mcpgateway
if "/app" not in sys.path:
    sys.path.append("/app")

try:
    from mcpgateway.db import SessionLocal
    from mcpgateway.services.email_auth_service import EmailAuthService
except ImportError as e:
    logger.error(f"Failed to import application modules: {e}")
    logger.error("Make sure you are running this script INSIDE the mcp_gateway container.")
    sys.exit(1)

async def reset_password(email, new_password):
    print(f"Resetting password for user: {email}")
    
    db = SessionLocal()
    try:
        service = EmailAuthService(db)
        
        # Check if user exists first to give better feedback
        user = await service.get_user_by_email(email)
        if not user:
            print(f"❌ User '{email}' does not exist.")
            return

        # Update the user
        # update_user handles hashing and validation
        await service.update_user(email=email, password=new_password)
        print(f"✅ Successfully updated password for '{email}'.")
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 reset_password.py <email> <new_password>")
        sys.exit(1)
        
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    asyncio.run(reset_password(email, new_password))
