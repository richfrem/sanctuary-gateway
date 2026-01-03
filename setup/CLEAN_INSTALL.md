# Sanctuary Gateway - Clean Install Instructions

This guide provides the definitive steps to perform a clean installation and verification of the Sanctuary Gateway.

## 1. Prerequisites

Ensure you have the following installed on your system:

*   **Podman**: Required for container runtime.
    *   *Check*: `podman --version`
    *   *Note*: Ensure your Podman machine is running.
        *   If it doesn't exist: `podman machine init`
        *   Start it: `podman machine start`
*   **Python 3**: Required for setup scripts.
    *   *Check*: `python3 --version`
*   **Make**: Required for build orchestration.
    *   *Check*: `make --version`

## 2. Configuration

1.  **Environment File**:
    Ensure you have an `.env` file in the project root.
    
    *   **If you already have an `.env` file**: DO NOT overwrite it. Ensure it contains the required variables below.
    *   **If starting fresh**: Create a new `.env` file and populate it with the required variables manually or by safely copying specific values from `.env.example`.
    *Required Variables* (defaults are usually fine for local dev):
    *   `PORT=4444`
    *   `CONTAINER_TOOL=podman`


## 3. SSL Certificate Trust (One-Time Setup)

**Goal:** Enable encrypted HTTPS traffic and trust the certificate locally.

1.  **Generate Certificates (if not done automatically):**
    *   *Wrapper Command:* `make certs`
    *   *Actual Command (OpenSSL):*
        ```bash
        openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
            -keyout certs/key.pem -out certs/cert.pem \
            -subj "/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
        ```
    *   *Details:* Generates a 4096-bit RSA key and a self-signed certificate valid for localhost (1 year).

2.  **Trust Configuration (macOS):**
    *   *Observation:* `curl https://localhost:4444` failed with certificate errors.
    *   *Diagnosis:* Certificate is valid but Self-Signed.
    *   *Action:* Added certificate to macOS System Keychain.
    *   *Command:* `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/cert.pem`
    *   *Result:* Browser accepts connection as Secure.

## 4. JWT Key Generation (One-Time Setup)

**Goal:** Generate RSA keys for signing API tokens.

1.  **Generate Keys (if not done automatically):**
    *   *Wrapper Command:* `make certs-jwt`
    *   *Details:* Generates 4096-bit RSA private and public keys in `certs/jwt/`.

2.  **Configuration Note:**
    *   The Gateway container requires **absolute paths** for these keys within the container.
    *   The `recreate_gateway.py` script handles this, but ensure your `.env` (if manually edited) uses:
        *   `JWT_PUBLIC_KEY_PATH=/app/certs/jwt/public.pem`
        *   `JWT_PRIVATE_KEY_PATH=/app/certs/jwt/private.pem`

## 5. Execution (The "One-Click" Setup)

We have consolidated the teardown, build, run, and verification into a single script.

**Run the Setup Script:**

```bash
python3 setup/recreate_gateway.py
```

### What this script does:
1.  **Prerequisites Check**: Verifies tools and `.env` exist.
2.  **Teardown**: Stops and removes any existing `mcpgateway` container.
3.  **Certificates**: Generates self-signed SSL certs and JWT keys if missing (`make certs`, `make certs-jwt`).
4.  **Podman Volume**: Ensures the data volume (`mcp_gateway_data`) exists.
5.  **Build**: Rebuilds the container image (`localhost/mcpgateway/mcpgateway:latest`) using Podman.
6.  **Launch**: Starts the container with SSL enabled.
7.  **Readiness**: Waits for the `/health` endpoint to return 200 OK.
8.  **Provisioning**: Generates a valid API token inside the container and updates your local `.env` file with `MCPGATEWAY_BEARER_TOKEN`.
9.  **Verification**:
    *   Runs `scripts/verify_jwt_auth.py` (Simple API connectivity check).
    *   Runs `tests/mcp_servers/gateway/integration/test_gateway_blackbox.py` (Integration tests).

## 5. Manual Verification

After the script completes successfully, you can verify connectivity manually:

**Check Health (Public):**
```bash
curl -k https://localhost:4444/health
```

**Check Tools (Authenticated):**
```bash
# Ensure MCPGATEWAY_BEARER_TOKEN is set in your current shell
source .env
curl -k -H "Authorization: Bearer $MCPGATEWAY_BEARER_TOKEN" https://localhost:4444/tools
```

## Troubleshooting

*   **Docker Daemon Errors**: If you see errors about connecting to the Docker daemon, ensure you are using the provided `recreate_gateway.py` script, which explicitly enforces Podman usage.
*   **Podman Hangs**: If `podman` commands hang (including inside the script), your Podman VM might be frozen.
    *   *Fix*: Run `podman machine stop` followed by `podman machine start`.

## Appendix: Technical Reference

### Makefile Configuration (Podman Compatibility)
The `Makefile` in this repository includes specific flags to support rootless Podman execution, which are critical for the correct operation of the setup scripts:

*   **Target:** `container-run-ssl` (used by `podman-run-ssl`)
*   **Volume Mounting:** Uses `:Z,U` suffixes for the data volume (`-v mcp_gateway_data:/app/data:Z,U`).
    *   `:Z`: Relabels the volume for private SELinux context (prevents "Permission Denied" from SELinux).
    *   `:U`: Recursively changes ownership of the volume to the container's user (UID 1001), resolving filesystem permission issues in rootless mode.
