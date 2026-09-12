import base64
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import hashlib

class DeterministicFernet(Fernet):
    def encrypt(self, data: bytes) -> bytes:
        import hashlib
        iv = hashlib.md5(data).digest()
        return self._encrypt_from_parts(data, 0, iv)

def get_cipher():
    key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return DeterministicFernet(fernet_key)

class EncryptedCharField(models.CharField):
    """
    Custom field that encrypts data before saving to the DB, 
    and decrypts it when retrieving. Uses Fernet symmetric encryption.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"
        
    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value is not None and value != '':
            cipher = get_cipher()
            # Encrypt and return as string
            encrypted = cipher.encrypt(value.encode('utf-8'))
            return encrypted.decode('utf-8')
        return value

    def from_db_value(self, value, expression, connection):
        if value is not None and value != '':
            cipher = get_cipher()
            try:
                decrypted = cipher.decrypt(value.encode('utf-8'))
                return decrypted.decode('utf-8')
            except Exception:
                # In case it's not encrypted (e.g., existing data)
                return value
        return value

    def to_python(self, value):
        # We don't decrypt here because to_python is called during validation 
        # of already-decrypted values as well. from_db_value handles the DB read.
        return super().to_python(value)
