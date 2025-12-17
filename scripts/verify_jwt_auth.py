import os
import ssl
import urllib.request
import urllib.error
import json

def get_token():
    """Extract specifically MCP_GATEWAY_API_TOKEN from .env"""
    token = None
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip().startswith('MCP_GATEWAY_API_TOKEN='):
                    # Split on first = and strip whitespace/quotes
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        token = parts[1].strip().strip('\'"')
                        break
    except FileNotFoundError:
        print("Error: .env file not found")
        return None
    return token

def make_request(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Create unverified SSL context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"\nTesting: {url}")
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            print(f"Status: {response.getcode()}")
            body = response.read().decode('utf-8')
            try:
                # Try to pretty print JSON
                parsed = json.loads(body)
                print(json.dumps(parsed, indent=2))
            except:
                print(body)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

def main():
    token = get_token()
    if not token:
        print("no token found in .env")
        return

    print(f"Token found (prefix): {token[:10]}...")

    # 1. Test Health (No Auth) - Baseline
    make_request("https://localhost:4444/health")

    # 2. Test Tools (Auth) - Should work if token is valid
    make_request("https://localhost:4444/tools", token)

if __name__ == "__main__":
    main()
