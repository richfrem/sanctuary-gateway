#!/usr/bin/env python3
"""Recreate Gateway - Setup and configure the MCP Gateway container.

PURPOSE:
    This script performs a complete teardown and rebuild of the MCP Gateway
    container, configuring all necessary credentials and verifying the setup.

TOKEN GENERATION FLOW:
    recreate_gateway.py
      └─> provision_token()
            └─> copies scripts/bootstrap_token.py to container
            └─> Executes: podman exec mcp_gateway python3 bootstrap_token.py
                  └─> bootstrap_token.py (runs inside container):
                        1. Finds admin user in database
                        2. Calls TokenCatalogService.create_token()
                        3. Token signed with certs/jwt/private.pem (RS256)
                        4. Token registered in database (appears in Admin UI)
                        5. Outputs: BOOTSTRAP_TOKEN_START:{jwt}:BOOTSTRAP_TOKEN_END
            └─> Captures token from output
            └─> Saves to .env:
                  - MCPGATEWAY_BEARER_TOKEN={jwt}
    
    RESULT: JWT token authorized for admin API operations

OUTPUTS/OBJECTIVES:
    1. Container Management:
       - Stop and remove existing 'mcp_gateway' container
       - Build fresh container image from Dockerfile
       - Start new container with proper configuration
       
    2. Credential Generation:
       - Generate JWT API token (MCPGATEWAY_BEARER_TOKEN) - AUTHORIZES all API operations
       - Save token to .env file
       - NOTE: Currently only JWT token is used for Gateway API auth
       The JWT Bearer token (stored as MCPGATEWAY_BEARER_TOKEN) is the only credential needed to:
            - Register MCP servers
            - Register virtual servers
            - Call tools
            - Access all Gateway APIs
       
    3. Token Registration:
       - Register JWT token in Gateway database via TokenCatalogService
       - Token appears in Admin UI and is authorized for all API operations
       
    4. Server Registration:
       - Register hello-world MCP server for testing
       - Verify tool discovery and invocation
       - use this to test registration of new servers, MCP and allow server to be discoverable on the server
       - validate the token registration and authorization
       
    5. Verification:
       - Health check on https://localhost:4444/health
       - JWT auth verification
       - Blackbox API tests

USAGE:
    python3 setup/recreate_gateway.py          # Full setup
    python3 setup/recreate_gateway.py --dry-run  # Preview without changes
"""
import os
import subprocess
import sys
import shutil
import argparse
import re
import datetime
import jwt
import time

# Container name from Makefile
CONTAINER_NAME = "mcp_gateway"

# Import shared env utilities
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_utils import load_env, update_env_file

def provision_token(env, dry_run=False):
    """Register JWT API token in Gateway database via TokenCatalogService.
    
    This function:
    1. Copies bootstrap_token.py into the running container
    2. Executes it, which calls TokenCatalogService.create_token()
    3. Token is registered in database (appears in Admin UI)
    4. Token is signed with PEM keys in certs/jwt/
    5. Saves raw JWT to .env for API authentication
    
    Returns:
        str: The JWT token if successful, None otherwise
    """
    bootstrap_file = "scripts/bootstrap_token.py"
    if not os.path.exists(bootstrap_file):
        print(f"⚠️  Cannot provision token: {bootstrap_file} not found locally.")
        return None

    print("🚀 Registering API Token ('sanctuary gateway api') inside container catalog...")
    
    if dry_run:
        print(f"Dry-run: Would cp {bootstrap_file} and exec it inside {CONTAINER_NAME}.")
        return "DRY_RUN_TOKEN"

    # 1. Clear existing token from host environment
    os.environ.pop("MCPGATEWAY_BEARER_TOKEN", None)
    
    try:
        # 2. Copy the script to the container
        run_cmd(f"podman cp {bootstrap_file} {CONTAINER_NAME}:/tmp/bootstrap_token.py", "Copying bootstrap script to container", dry_run)
        
        # 3. Execute the script inside the container
        # Note: We use run_cmd wrapper but capture output manually since we need the token value
        cmd = f"podman exec {CONTAINER_NAME} python3 /tmp/bootstrap_token.py"
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error executing bootstrap script:\n{result.stderr}")
            return None
            
        # 4. Extract the token from output
        import re
        match = re.search(r"BOOTSTRAP_TOKEN_START:(.*?):BOOTSTRAP_TOKEN_END", result.stdout)
        if not match:
            print(f"❌ Failed to extract token from bootstrap output. Output:\n{result.stdout}")
            return None
            
        token = match.group(1)
        
        # 5. Update .env file
        update_env_file("MCPGATEWAY_BEARER_TOKEN", token)
        
        # 6. Update .zshrc (User Request)
        update_zshrc(token)
        
        # 7. Update current process environment for immediate testing
        os.environ["MCPGATEWAY_BEARER_TOKEN"] = token
        
        print("✅ Token registered in database and .env synchronized.")
        return token
    except Exception as e:
        print(f"❌ Error provisioning token: {e}")
        return None

def update_zshrc(token):
    """Update MCPGATEWAY_BEARER_TOKEN in ~/.zshrc."""
    zshrc_path = os.path.expanduser("~/.zshrc")
    key = "MCPGATEWAY_BEARER_TOKEN"
    line_content = f'export {key}="{token}"\n'
    
    try:
        lines = []
        if os.path.exists(zshrc_path):
            with open(zshrc_path, "r") as f:
                lines = f.readlines()

        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"export {key}=") or line.strip().startswith(f"{key}="):
                lines[i] = line_content
                found = True
                break
        
        if not found:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(line_content)
            
        with open(zshrc_path, "w") as f:
            f.writelines(lines)
        print(f"✅ Updated {zshrc_path} with new token.")
            
    except Exception as e:
        print(f"⚠️  Failed to update .zshrc: {e}")

def register_demo_server(token, dry_run=False):
    """Registers a 'hello-world' MCP server via the Gateway API.
    
    Uses JWT Bearer token for authorization.
    """
    print("\n--- Phase 7.6: Registering Demo Server ---")
    
    # Hello World Server Payload (Internal Network)
    payload = f'''{{
           "name": "hello-world",
           "url": "http://helloworld_mcp:8005/sse",
           "description": "Automated Hello World Server (Internal Network)",
           "auth_type": null,
           "tags": ["test:automated"]
         }}'''
    
    cmd = f"""curl -s -X POST -H "Authorization: Bearer {token}" \
     -H "Content-Type: application/json" \
     -d '{payload}' \
     https://localhost:4444/gateways"""
     
    # Note: Using -k for curl insecure until we trust CA fully in all contexts
    cmd = cmd.replace("curl -s", "curl -k -s")

    if dry_run:
        print(f"🏜  [DRY RUN] Would register server: {cmd}")
        return True

    print(f"🚀 Registering 'hello-world' server...")
    try:
        # We don't use run_cmd here because we want to inspect the output JSON specifically
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Curl failed: {result.stderr}")
            return False
            
        if "hello-world" in result.stdout:
            print(f"✅ Server 'hello-world' registered successfully.")
            return True
        elif "Conflict" in result.stdout or "already exists" in result.stdout:
             print(f"⚠️  Server 'hello-world' already exists (Skipping).")
             return True
        else:
            print(f"❌ Unexpected response: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ Error registering server: {e}")
        return False


def invoke_demo_tool(token, dry_run=False):
    """Invokes a tool via the Gateway's /rpc endpoint using JSON-RPC format.
    
    Uses JWT Bearer token for authorization.
    """
    print("\n--- Phase 7.7: Verifying Tool Invocation (via Gateway /rpc) ---")
    
    # JSON-RPC payload for tool invocation
    payload = r'''{
           "jsonrpc": "2.0",
           "method": "tools/call",
           "params": {
             "name": "hello-world-say-hello",
             "arguments": {"name": "SanctuaryUser"}
           },
           "id": 1
         }'''
    
    cmd_invoke = f"""curl -k -s -X POST -H "Authorization: Bearer {token}" \
     -H "Content-Type: application/json" \
     -d '{payload}' \
     https://localhost:4444/rpc"""
    
    if dry_run:
        print(f"🏜  [DRY RUN] Would invoke tool: {cmd_invoke}")
        # print("Header: X-Vault-Tokens: " + vault_tokens)
        return True

    print(f"🚀 Invoking tool 'say_hello' (hello-world) via Gateway...")
    try:
        result = subprocess.run(cmd_invoke, shell=True, capture_output=True, text=True)
        
        # Check for success and expected content
        # Gateway returns the tool result wrapped in a response
        if result.returncode == 0 and "Hello, SanctuaryUser!" in result.stdout:
             print(f"✅ Tool invocation successful! Gateway returned: {result.stdout}")
             return True
        else:
             print(f"❌ Failed to invoke tool. \n   Output: {result.stdout}\n   Error: {result.stderr}")
             return False
    except Exception as e:
         print(f"❌ Error invoking tool: {e}")
         return False

def wait_for_ready(url, timeout=30):
    """Waits for a URL to return a 200 status."""
    import ssl
    import urllib.request
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    start_time = time.time()
    print(f"⏳ Waiting for Gateway at {url} (timeout {timeout}s)...")
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=2) as response:
                if response.getcode() == 200:
                    print("✅ Gateway is ready!")
                    return True
        except Exception:
            # Silence connection errors during polling
            pass
        time.sleep(1)
    
    print(f"❌ Timeout waiting for Gateway at {url}")
    return False

def run_cmd(cmd, description, dry_run=False):
    if dry_run:
        print(f"🏜  [DRY RUN] {description}: {cmd}")
        return True
    print(f"🚀 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} complete.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        if e.stdout:
            print("--- STDOUT ---")
            print(e.stdout)
        if e.stderr:
            print("--- STDERR ---")
            print(e.stderr)
        return False

def check_podman_resource(resource_type, name):
    """Checks if a podman resource (image, container, volume) exists."""
    cmd = f"podman {resource_type} exists {name}"
    return subprocess.run(cmd, shell=True).returncode == 0

def main():
    parser = argparse.ArgumentParser(description="Sanctuary Gateway Granular Recreate Loop")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    parser.add_argument("--force", action="store_true", help="Force all steps regardless of state")
    args = parser.parse_args()

    print("🛠 Sanctuary Gateway - Granular Setup Loop")

    # PHASE 1: ENVIRONMENT LOADING
    print("\n--- Phase 1: Environment Loading ---")
    env = load_env()
    if not env:
        print("❌ Error: .env file not found or empty. Please create it first.")
        sys.exit(1)
    
    # Required paths from .env
    jwt_pub = env.get("JWT_PUBLIC_KEY_PATH", "certs/jwt/public.pem")
    jwt_priv = env.get("JWT_PRIVATE_KEY_PATH", "certs/jwt/private.pem")
    db_url = env.get("DATABASE_URL", "sqlite:////app/data/mcp.db")
    
    print(f"✅ Loaded .env configuration. (JWT Keys: {jwt_pub}, {jwt_priv})")

    # PHASE 2: PREREQUISITES
    print("\n--- Phase 2: Tool Check ---")
    for tool in ["podman", "openssl", "make"]:
        if not shutil.which(tool):
            print(f"❌ Required tool '{tool}' not found in PATH.")
            sys.exit(1)
    print("✅ Prerequisites met.")

    # PHASE 3: SSL CERTIFICATES
    print("\n--- Phase 3: SSL Certificates ---")
    ssl_cert = "certs/cert.pem"
    ssl_key = "certs/key.pem"
    if not os.path.exists(ssl_cert) or not os.path.exists(ssl_key) or args.force:
        os.makedirs("certs", exist_ok=True)
        run_cmd("make certs", "Generating SSL Certificates", args.dry_run)
    else:
        print(f"✅ SSL Certificates already exist at {ssl_cert}")

    # PHASE 4: JWT RSA KEYS
    print("\n--- Phase 4: JWT RSA Keys ---")
    if not os.path.exists(jwt_pub) or not os.path.exists(jwt_priv) or args.force:
        os.makedirs(os.path.dirname(jwt_priv), exist_ok=True)
        run_cmd("make certs-jwt", "Generating JWT RSA Keys", args.dry_run)
    else:
        print(f"✅ JWT RSA Keys already exist at {jwt_priv}")

    # PHASE 4.5: CONTAINER TEARDOWN
    print("\n--- Phase 4.5: Container Teardown ---")
    # Clean up both current and potentially old container names to unlock volumes
    for container in [CONTAINER_NAME, "mcpgateway", "helloworld_mcp"]:
        if check_podman_resource("container", container):
            run_cmd(f"podman stop {container}", f"Stopping {container}", args.dry_run)
            run_cmd(f"podman rm {container}", f"Removing {container}", args.dry_run)

    # PHASE 5: PODMAN VOLUME
    print("\n--- Phase 5: Podman Volume (Cleanup and recreation) ---")
    if check_podman_resource("volume", "mcp_gateway_data"):
        run_cmd("podman volume rm mcp_gateway_data", "Removing existing volume 'mcp_gateway_data'", args.dry_run)
    run_cmd("podman volume create mcp_gateway_data", "Creating fresh volume 'mcp_gateway_data'", args.dry_run)


    # PHASE 6: IMAGE BUILD (Gateway)
    print("\n--- Phase 6: Container Images ---")
    # The image name in the Makefile is mcpgateway/mcpgateway
    # Podman prepends 'localhost/' to locally built images
    GATEWAY_IMAGE = "localhost/mcpgateway/mcpgateway:latest"
    if not check_podman_resource("image", GATEWAY_IMAGE) and not check_podman_resource("image", "mcpgateway/mcpgateway:latest") or args.force:
        run_cmd("make podman-build", "Building Gateway Image", args.dry_run)
    else:
        print(f"✅ Gateway image exists.")


    # Build Hello World Image
    helloworld_dir = "tests/assets/helloworld"
    HELLOWORLD_IMAGE = "localhost/helloworld_mcp:latest"
    if not os.path.exists(helloworld_dir):
        print(f"⚠️  Hello World assets not found at {helloworld_dir}, skipping Hello World build.")
    else:
        if not check_podman_resource("image", HELLOWORLD_IMAGE) or args.force:
             run_cmd(f"podman build -t {HELLOWORLD_IMAGE} {helloworld_dir}", "Building Hello World Image", args.dry_run)
        else:
             print(f"✅ Hello World image '{HELLOWORLD_IMAGE}' exists.")

    # PHASE 6.5: NETWORK setup
    print("\n--- Phase 6.5: Network Setup ---")
    NETWORK_NAME = "sanctuary_network"
    if not check_podman_resource("network", NETWORK_NAME):
        run_cmd(f"podman network create {NETWORK_NAME}", "Creating Network 'sanctuary_network'", args.dry_run)
    else:
        print(f"✅ Network '{NETWORK_NAME}' exists.")

    # PHASE 7: CONTAINER DEPLOYMENT
    print("\n--- Phase 7: Container Deployment ---")

    # Run Hello World Server (Background)
    if check_podman_resource("image", HELLOWORLD_IMAGE):
        run_cmd(f"podman run -d --name helloworld_mcp --network {NETWORK_NAME} -p 8005:8005 {HELLOWORLD_IMAGE}", "Starting Hello World Server", args.dry_run)
    else:
        print("⚠️  Skipping Hello World Server: Image not found.")

    # Run Gateway (attached to network)
    run_cmd("make podman-run-ssl", "Launching Gateway Container", args.dry_run)
    
    # Attach containers to network (optional - may fail on slirp4netns/WSL2)
    if not args.dry_run:
        # Give it a moment to exist
        time.sleep(2)
        # Try to connect containers to network. This may fail on some platforms
        # (e.g., WSL2 with slirp4netns) but is not critical if containers were
        # started with --network flag directly.
        try:
            result = subprocess.run(f"podman network connect {NETWORK_NAME} helloworld_mcp", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Connected helloworld_mcp to '{NETWORK_NAME}'")
            elif "already connected" in result.stderr.lower():
                print(f"✅ helloworld_mcp already connected to '{NETWORK_NAME}'")
            else:
                print(f"⚠️  Could not connect helloworld_mcp to network (non-fatal): {result.stderr.strip()}")
        except Exception as e:
            print(f"⚠️  Network connect not supported on this platform: {e}")
        
        try:
            result = subprocess.run(f"podman network connect {NETWORK_NAME} {CONTAINER_NAME}", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Connected {CONTAINER_NAME} to '{NETWORK_NAME}'")
            elif "already connected" in result.stderr.lower():
                print(f"✅ {CONTAINER_NAME} already connected to '{NETWORK_NAME}'")
            else:
                print(f"⚠️  Could not connect {CONTAINER_NAME} to network (non-fatal): {result.stderr.strip()}")
        except Exception as e:
            print(f"⚠️  Network connect not supported on this platform: {e}")


    # PHASE 7.1: READINESS CHECK
    if not args.dry_run:
        print("\n--- Phase 7.1: Readiness Check ---")
        if not wait_for_ready("https://localhost:4444/health"):
            print("❌ Error: Gateway container did not become ready in time. Aborting.")
            subprocess.run(f"podman logs {CONTAINER_NAME} | tail -n 20", shell=True)
            sys.exit(1)

    # PHASE 7.5: TOKEN PROVISIONING
    token = None
    if not args.dry_run:
        print("\n--- Phase 7.5: Token Provisioning ---")
        token = provision_token(env, args.dry_run)
        
        if token:
             # Registers hello-world/github server
             register_demo_server(token, args.dry_run)
             # Verifies tools list
             invoke_demo_tool(token, args.dry_run)
    
    # Cleanup demo server
    if check_podman_resource("container", "helloworld_mcp"):
          print("\n--- Cleanup ---")
          # We leave it running for manual inspection as per standard dev workflows, or kill it?
          # User said "call that with curl at the end to verify". Usually implies leaving it up or tearing down.
          # Let's leave it up so user can verify manually too.
          print("ℹ️  'helloworld_mcp' container left running for manual verification.")

    # PHASE 8: AUTOMATED VERIFICATION
    if not args.dry_run:
        print("\n--- Phase 8: Automated Verification ---")
        run_cmd("python3 scripts/verify_jwt_auth.py", "Running JWT Auth Verification (scripts/verify_jwt_auth.py)", args.dry_run)
        run_cmd("python3 tests/mcp_servers/gateway/integration/test_gateway_blackbox.py", "Running Blackbox API Tests", args.dry_run)

    print("\n✨ Setup sequence complete!")
    print("🔍 Manual verify: curl -k https://localhost:4444/health")

if __name__ == "__main__":
    main()