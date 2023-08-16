import codecs
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization


def create():
        key = X25519PrivateKey.generate()
        
        pubkey = key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
        )

        bytes = key.private_bytes(  
                encoding=serialization.Encoding.Raw,  
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
        )

        print(codecs.encode(bytes, 'base64').decode('utf8').strip())
        print(codecs.encode(pubkey, 'base64').decode('utf8').strip())
