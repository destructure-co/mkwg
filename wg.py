import codecs
import secrets
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

"""wg is a python implementation of a subset of the utilities provided by the
"wg" command from the "wireguard-tools" package.
"""


def genkey() -> str:
    """Generates a random private key in base64 and returns it"""
    key = X25519PrivateKey.generate()

    # Do not use private_bytes_raw as it's missing from old cryptography versions
    bytes = key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption,
    )

    return codecs.encode(bytes, "base64").decode("utf-8").strip()


def pubkey(private_key: str) -> str:
    """Calculates a public key and returns it in base64 from a corresponding private key (generated with genkey) given in base64"""
    bytes_raw = codecs.decode(codecs.encode(private_key, "utf-8"), "base64")
    key = X25519PrivateKey.from_private_bytes(bytes_raw)

    # Do not use public_bytes_raw as it's missing from old cryptography versions
    pubkey_bytes = key.public_key().public_bytes(
        Encoding.Raw,
        PublicFormat.Raw
    )

    return codecs.encode(pubkey_bytes, "base64").decode("utf-8").strip()


def genpsk() -> str:
    """genpsk Generates a random preshared key in base64 and returns it"""
    return codecs.encode(secrets.token_bytes(32), "base64").decode("utf-8").strip()
