import requests
import os
import urllib3

# Suppress InsecureRequestWarning for self-signed certs (Localhost/Podman)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TestGatewayBlackBox:
    """
    "Black Box" verification suite for the decoupled Sanctuary Gateway.
    Simplified "Hello World" API test.
    """

    @property
    def config(self):
        """Lazy load config."""
        return {
            "URL": os.getenv("MCP_GATEWAY_URL", "https://localhost:4444"),
            "API_TOKEN": os.getenv("MCPGATEWAY_BEARER_TOKEN", "")
        }

    def test_pulse_check(self):
        """
        1. The 'Pulse' Check
        Target: GET /health
        Expectation: 200 OK
        """
        url = f"{self.config['URL']}/health"
        print(f"\n[Pulse] Checking heartbeat at: {url}")

        try:
            response = requests.get(url, verify=False, timeout=5)
            # Simple assertion for standalone run
            if response.status_code != 200:
                 raise Exception(f"Pulse Check Failed: Expected 200 OK, got {response.status_code}. Body: {response.text}")
            print("  -> PASS")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Pulse Check Failed: Connection refused to {url}")

    def test_circuit_breaker(self):
        """
        2. The 'Circuit Breaker' Check
        Target: GET /tools
        Condition: Invalid API Token
        Expectation: 401 Unauthorized or 403 Forbidden
        """
        url = f"{self.config['URL']}/tools"
        headers = {"Authorization": "Bearer invalid-token-should-be-rejected"}
        
        print(f"\n[Circuit Breaker] Testing security with invalid token at: {url}")
        response = requests.get(url, headers=headers, verify=False, timeout=5)

        if response.status_code not in [401, 403]:
             raise Exception(f"Circuit Breaker Failed! Gateway accepted invalid token. Status: {response.status_code}")
        print("  -> PASS")

    def test_handshake(self):
        """
        3. The 'Handshake' Check
        Target: GET /tools
        Condition: Valid API Token
        Expectation: 200 OK
        """
        if not self.config['API_TOKEN']:
            print("Skipping Handshake: MCPGATEWAY_BEARER_TOKEN not set")
            return
        
        url = f"{self.config['URL']}/tools"
        headers = {"Authorization": f"Bearer {self.config['API_TOKEN']}"}
        
        print(f"\n[Handshake] Authenticating with API token at: {url}")

        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code != 200:
                raise Exception(f"Handshake Failed: Token rejected. Status: {response.status_code}. Body: {response.text}")
            print("  -> PASS")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Handshake Failed: Connection refused at {url}")

if __name__ == "__main__":
    test = TestGatewayBlackBox()
    try:
        test.test_pulse_check()
        test.test_circuit_breaker()
        test.test_handshake()
        print("\n\u2705 ALL TESTS PASSED")
    except Exception as e:
        print(f"\n\u274c FAILED: {e}")
        exit(1)
