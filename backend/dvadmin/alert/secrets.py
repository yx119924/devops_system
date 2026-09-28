"""Versioned encryption for channel secrets; legacy plaintext requires migration."""
from dvadmin.bastion.crypto import decrypt, encrypt

SECRET_FIELDS = ('webhook', 'secret', 'password')
PREFIX = 'fernet:v1:'


def encrypt_config(config):
    result = dict(config)
    for key in SECRET_FIELDS:
        if result.get(key):
            result[key] = PREFIX + encrypt(result[key])
    return result


def decrypt_config(config):
    result = dict(config or {})
    for key in SECRET_FIELDS:
        value = result.get(key)
        if value:
            if not isinstance(value, str) or not value.startswith(PREFIX):
                raise ValueError('渠道密钥尚未迁移，请运行 migrate_secrets')
            result[key] = decrypt(value[len(PREFIX):])
    return result
