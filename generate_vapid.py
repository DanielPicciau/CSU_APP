#!/usr/bin/env python
"""Generate VAPID keys for Web Push notifications."""

from py_vapid import Vapid
import base64
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Generate a new VAPID key pair
v = Vapid()
v.generate_keys()

# Get private key in raw format
priv_numbers = v.private_key.private_numbers()
priv_bytes = priv_numbers.private_value.to_bytes(32, 'big')
priv_b64 = base64.urlsafe_b64encode(priv_bytes).decode().rstrip('=')

# Get public key
pub_bytes = v.public_key.public_bytes(
    encoding=Encoding.X962,
    format=PublicFormat.UncompressedPoint
)
pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode().rstrip('=')

print("=== NEW VAPID KEY PAIR FOR PRODUCTION ===")
print()
print("VAPID_PRIVATE_KEY=" + priv_b64)
print("VAPID_PUBLIC_KEY=" + pub_b64)
print()
print("IMPORTANT: After updating these keys on PythonAnywhere:")
print("1. All existing push subscriptions will be invalid")
print("2. Users must re-enable notifications in Settings")
