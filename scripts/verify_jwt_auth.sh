#!/bin/bash
# Recovered from setup/PODMAN_SETUP_HISTORY.md

# You need to manually set this token or export it
# Example: export MCP_GATEWAY_API_TOKEN="ey..."
TOKEN="${MCP_GATEWAY_API_TOKEN:-your-jwt-token-here}"

if [ "$TOKEN" == "your-jwt-token-here" ]; then
    echo "⚠️  Warning: Token not set."
    echo "Usage: export MCP_GATEWAY_API_TOKEN='...' && ./verify_jwt_auth.sh"
    echo "Or edit this file to paste your token."
    echo ""
fi

echo "Include header: Authorization: Bearer <token>"
curl -v -k -H "Authorization: Bearer $TOKEN" https://localhost:4444/v1/servers
