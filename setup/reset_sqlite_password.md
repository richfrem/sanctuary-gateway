# Resetting SQLite User Password

This guide explains how to reset the password for a user (e.g., `admin`) in the Sanctuary Gateway SQLite database.

## Prerequisites

- Access to the `mcp_gateway` container (where the database lives).
- The `reset_password.py` script (created alongside this file).

## Steps

1.  **Copy the Reset Script to the Container**
    We need to put the Python script inside the container so it can access the database file directly.

    ```bash
    podman cp setup/reset_password.py mcp_gateway:/tmp/reset_password.py
    ```

2.  **Execute the Script**
    Run the script inside the container. You need to specify the email of the user you want to update (usually `admin` or your email) and the new password.

    **Syntax:**
    `python3 /tmp/reset_password.py <email> <new_password>`

    **Example:**
    ```bash
    podman exec -e DATABASE_URL=sqlite:////app/data/mcp.db mcp_gateway python3 /tmp/reset_password.py admin newSafePassword123!
    ```

3.  **Verify Access**
    Try logging in to the Gateway UI or API with the new credentials.

## Troubleshooting

-   **User Not Found:** If the script says "User not found", verify the email address by listing all users:
    ```bash
    podman exec -e DATABASE_URL=sqlite:////app/data/mcp.db mcp_gateway python3 -c "from sqlalchemy import create_engine, text; print(create_engine('sqlite:////app/data/mcp.db').connect().execute(text('SELECT email FROM email_users')).fetchall())"
    ```
