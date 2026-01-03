# Setup Directory

This directory contains scripts and documentation for setting up the Sanctuary Gateway.

## Key Files

*   `recreate_gateway.py`: The main one-click setup script. It handles:
    *   Tearing down existing containers.
    *   **Deleting the `mcp_gateway_data` volume/database** (ensuring a fresh start).
    *   Building Podman images.
    *   Creating the Podman network.
    *   Launching the Gateway and Hello World containers.
    *   Bootstrapping the admin user and API token.
    *   Running integration tests.
*   `CLEAN_INSTALL.md`: Detailed step-by-step guide for a clean installation.
*   `agent_gateway_guide.md`: User guide for connecting agents to the Gateway.
*   `reset_password.py`: Helper script to manually reset the admin password.

## Prerequisites (WSL/Linux)

*   **Podman**: Must be installed and running (`podman system service` or `podman machine start`).
*   **Python 3**: Required for running the setup script.
*   **Make**: Required for build targets.
*   **Environment Variables**:
    *   You must have `.env` configured (see `.env.example`).
    *   **CRITICAL**: `PLATFORM_ADMIN_EMAIL` and `PLATFORM_ADMIN_PASSWORD` must be set in your shell environment (e.g., `.zshrc`) or `.env` file. The `Makefile` has been updated to specifically pass these variables to the container.
    *   **Token Refresh**: When `recreate_gateway.py` runs, it generates a **new** `MCPGATEWAY_BEARER_TOKEN` and saves it to `.env`. 
        1.  Update your Windows User Environment Variable `MCPGATEWAY_BEARER_TOKEN` with this new value.
        2.  **Ensure your `WSLENV` variable includes `MCPGATEWAY_BEARER_TOKEN/u`**. This creates the "bridge" that allows the token to pass from Windows to WSL.
        Failing to do this will cause "401 Unauthorized" errors because the old token remains in your environment.

## Usage

Run the setup script from the project root:

```bash
python3 setup/recreate_gateway.py
```

This will perform a full reset and install. The admin user will be created with the credentials from your environment variables.

## Troubleshooting

### 401 Unauthorized / Invalid Authentication
If you receive "401 Unauthorized" errors or "Invalid authentication credentials" after running setup:
1.  **Check `.env`**: Confirm `recreate_gateway.py` updated the `MCPGATEWAY_BEARER_TOKEN` in your `.env` file.
2.  **Update Windows Env**: Copy this new token to your Windows User Environment Variable `MCPGATEWAY_BEARER_TOKEN`.
3.  **Check WSLENV**: Ensure `WSLENV` includes `MCPGATEWAY_BEARER_TOKEN/u`.
4.  **Verify Quoting**: Ensure the token in `.env` does not have double quotes (e.g., `""eyJ...""`). It should look like `MCPGATEWAY_BEARER_TOKEN="eyJ..."`.

### 503 Service Unavailable / "Unable to connect to gateway"
If you receive a 503 error when `verify_hello_world_rpc.py` runs, it means the Gateway cannot reach the Hello World server.
*   **Cause**: On WSL2/Podman, containers on different networks cannot communicate due to `slirp4netns` limitations.
*   **Fix**: Ensure the Gateway is launched with `--network=sanctuary_network` (or whatever network the servers are on).
    *   In `Makefile`, update the `podman-run-ssl` (or `container-run-ssl`) target to include `--network=sanctuary_network`.

## Prerequisites (macOS)

*   **Podman**: Install via Homebrew (`brew install podman`). Initialize with `podman machine init && podman machine start`.
*   **Python 3**: Ships with macOS or install via Homebrew.
*   **Make**: Comes with Xcode Command Line Tools (`xcode-select --install`).
*   **Environment Variables**: Same as WSL. Token syncs to `~/.zshrc` automatically.

## Verification Scripts

After setup, you can verify the installation:

*   `python3 setup/verify_hello_world_rpc.py` - Tests gateway registration and tool invocation via JSON-RPC.
*   `scripts/verify_jwt_auth.py` - Validates JWT token authentication.

## Cross-Platform Considerations

| Issue | macOS | WSL2/Windows |
|-------|-------|--------------|
| Network Mode | `podman network connect` works | May fail with `slirp4netns` error |
| Token Storage | `~/.zshrc` | Windows User Env Vars + WSLENV bridge |
| Quote Handling | Standard | May cause double-quoting (fixed in `env_utils.py`) |

## Recent Fixes

*   **`--network=sanctuary_network`**: Added to `container-run-ssl` Makefile target for cross-platform compatibility.
*   **Quote stripping**: `env_utils.py` now strips existing quotes before writing to prevent `TOKEN=""value""` issues on Windows.
*   **Non-fatal network connect**: `recreate_gateway.py` treats `podman network connect` failures as warnings, not errors.