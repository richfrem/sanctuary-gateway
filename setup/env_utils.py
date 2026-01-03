#!/usr/bin/env python3
"""Shared utilities for .env file manipulation.

Used by recreate_gateway.py, generate_oauth_credentials.py, and other setup scripts.
"""
import os
import re


def load_env(file_path=".env"):
    """Parse .env file and return key-value dictionary.
    
    Args:
        file_path: Path to .env file (default: ".env")
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^\s*([\w.-]+)\s*=\s*(.*)$", line)
            if match:
                key = match.group(1)
                value = match.group(2).split("#")[0].strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


def update_env_file(key, value, file_path=".env"):
    """Update or add a key/value pair in .env file.
    
    Args:
        key: Environment variable name
        value: Value to set
        file_path: Path to .env file (default: ".env")
    """
    # Strip any existing quotes from value to prevent double-quoting
    value = str(value).strip()
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write(f'{key}="{value}"\n')
        return

    lines = []
    found = False
    with open(file_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f'{key}="{value}"\n'
            found = True
            break
    
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f'{key}="{value}"\n')

    with open(file_path, "w") as f:
        f.writelines(lines)

