import base64
import hashlib
import secrets


def generate_random_hex_id(prefix: str) -> str:
    """Generates a random 16-character hex ID, e.g., 'usr_3c13309ba512a99b'"""
    # 8 bytes of entropy = 16 chars of hex
    return f"{prefix}_{secrets.token_hex(8)}"


def generate_deterministic_hex_id(prefix: str, data: str) -> str:
    """Generates a deterministic 16-character hex ID, e.g., 'instr_f1a2309ba512a99c'"""
    # Generate full hex string and slice the first 16 chars
    hash_string = hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{hash_string}"


def generate_random_base64_id(prefix: str) -> str:
    """Generates a random 16-character ID, e.g., 'usr_R5b_x8-P9wQwA1bC'"""
    # 12 bytes of entropy = exactly 16 chars of base64
    return f"{prefix}_{secrets.token_urlsafe(12)}"


def generate_deterministic_base64_id(prefix: str, data: str) -> str:
    """Generates a deterministic 16-character ID from data, e.g., 'instr_A1b_x8-P9wQwA1bC'"""
    # 1. Hash the string using SHA-256
    digest = hashlib.sha256(data.encode("utf-8")).digest()

    # 2. Take the first 12 bytes of the raw hash
    truncated_digest = digest[:12]

    # 3. Base64-URL encode it to match secrets.token_urlsafe
    encoded = base64.urlsafe_b64encode(truncated_digest).decode("ascii")

    # URL-safe base64 can contain padding (=). 12 bytes divides cleanly by 3, but we strip just to be perfectly safe.
    return f"{prefix}_{encoded.rstrip('=')}"
