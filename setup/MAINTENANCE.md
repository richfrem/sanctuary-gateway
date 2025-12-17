# Repository Maintenance & Sync

This repository is configured as a **Fork** of the upstream IBM Context Forge project.

## Remote Configuration

*   **origin**: `https://github.com/richfrem/sanctuary-gateway` (Your custom fork)
*   **upstream**: `https://github.com/IBM/mcp-context-forge.git` (Source of truth)

## Syncing with Upstream

To pull the latest changes from the IBM repository:

```bash
# 1. Fetch updates
git fetch upstream

# 2. Merge into your local main
git checkout main
git merge upstream/main

# 3. Push to your fork
git push origin main
```

## Maintenance Workflows

### Moving Scripts
Utility scripts have been moved to `scripts/` to keep the root directory clean.
*   `tests/mcp_servers/gateway/integration/test_gateway_blackbox.py`: Integration test suite
*   `scripts/verify_jwt_auth.py`: Quick JWT verification tool
