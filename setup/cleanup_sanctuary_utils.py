"""
Cleanup Script for MCP Gateway Servers

Purpose:
    This script is designed to remove server entries from the MCP Gateway database.

Usage:
    python3 setup/cleanup_sanctuary_utils.py [server_name]

    - If a server_name is provided, only that server is removed.
    - If NO argument is provided, ALL servers are removed (Factory Reset for servers).
"""
import sys
import os
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path to allow imports if needed
sys.path.append(os.getcwd())

# Database URL from .env or default
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/mcp.db")

def cleanup_servers(server_name=None):
    print(f"Connecting to database: {DB_URL}")
    if DB_URL.startswith("sqlite"):
        # Ensure path exists for sqlite
        db_path = DB_URL.replace("sqlite:///", "")
        if not os.path.exists(db_path):
             print(f"Error: Database file not found at {db_path}")
             return

    try:
        engine = create_engine(DB_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Inspect tables to find the correct table name
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result]
        print(f"Tables found: {tables}")
        
        server_table = 'server' if 'server' in tables else 'servers'
        if server_table not in tables:
             print("Could not find 'server' or 'servers' table.")
             return

        if server_name:
            print(f"Searching for artifacts related to: '{server_name}'...")
            
            # 1. Clean Servers Table
            query = text(f"SELECT id, name FROM {server_table} WHERE name = :name")
            target = db.execute(query, {"name": server_name}).first()
            if target:
                print(f"Found server: ID={target.id}, Name={target.name}")
                delete_query = text(f"DELETE FROM {server_table} WHERE id = :id")
                db.execute(delete_query, {"id": target.id})
                print(f"Deleted server record '{server_name}'")
            else:
                print(f"Server record '{server_name}' not found.")

            # 2. Clean Tools Table (Orphaned or named similarly)
            # Searching for tools that might belong to this server by name convention if possible
            # Assuming tool names might be namespaced like 'server_name_tool_name' or similar, 
            # OR we check associations if the server WAS found. 
            # Since server might be gone, we do a pattern match on tool name/id as a fallback.
            print(f"Scanning for related tools (containing '{server_name}')...")
            tools_query = text("SELECT id, name FROM tools WHERE name LIKE :pattern")
            tools = db.execute(tools_query, {"pattern": f"%{server_name}%"}).fetchall()
            for t in tools:
                 print(f"Found related tool: {t.name} (ID: {t.id}) .. DELETING")
                 db.execute(text("DELETE FROM tools WHERE id = :id"), {"id": t.id})

            # 3. Clean Resources
            print(f"Scanning for related resources (containing '{server_name}')...")
            res_query = text("SELECT id, name FROM resources WHERE name LIKE :pattern OR uri LIKE :pattern")
            resources = db.execute(res_query, {"pattern": f"%{server_name}%"}).fetchall()
            for r in resources:
                 print(f"Found related resource: {r.name} (ID: {r.id}) .. DELETING")
                 db.execute(text("DELETE FROM resources WHERE id = :id"), {"id": r.id})

            # 4. Clean Prompts
            print(f"Scanning for related prompts (containing '{server_name}')...")
            prompts_query = text("SELECT id, name FROM prompts WHERE name LIKE :pattern")
            prompts = db.execute(prompts_query, {"pattern": f"%{server_name}%"}).fetchall()
            for p in prompts:
                 print(f"Found related prompt: {p.name} (ID: {p.id}) .. DELETING")
                 db.execute(text("DELETE FROM prompts WHERE id = :id"), {"id": p.id})

            # 5. Clean Gateways (Federation)
            # Check gateways table if it exists
            if 'gateways' in tables:
                print(f"Scanning for related gateways (containing '{server_name}')...")
                gw_query = text("SELECT id, url FROM gateways WHERE url LIKE :pattern")
                gateways = db.execute(gw_query, {"pattern": f"%{server_name}%"}).fetchall()
                for g in gateways:
                     print(f"Found related gateway: {g.url} (ID: {g.id}) .. DELETING")
                     db.execute(text("DELETE FROM gateways WHERE id = :id"), {"id": g.id})

            db.commit()
            print("Cleanup operations committed.")
            
        else:
            print("No server name provided. Executing cleanup of ALL servers...")
            # Count servers first
            count_query = text(f"SELECT count(*) FROM {server_table}")
            count = db.execute(count_query).scalar()
            
            if count > 0:
                print(f"Found {count} servers. removing them all...")
                delete_all_servers = text(f"DELETE FROM {server_table}")
                db.execute(delete_all_servers)
                
                # Also clean related tables
                print("Cleaning all tools, resources, and prompts...")
                db.execute(text("DELETE FROM tools"))
                db.execute(text("DELETE FROM resources"))
                db.execute(text("DELETE FROM prompts"))
                # cleaning associations is usually automatic via cascade or we should wipe them too
                
                db.commit()
                print(f"Successfully deleted all {count} servers and related artifacts.")
            else:
                 print("Database is already empty of servers.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup MCP Gateway Servers")
    parser.add_argument("server_name", nargs="?", help="Name of the specific server to remove. If omitted, ALL servers are removed.")
    args = parser.parse_args()
    
    cleanup_servers(args.server_name)
