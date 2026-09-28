# -*- coding: utf-8 -*-
"""
凭据加密工具：Fernet 对称加密
密钥来自 conf/env.py 的 CREDENTIAL_ENCRYPTION_KEY
"""
import os
from cryptography.fernet import Fernet


def _fernet():
    from conf import env
    key = os.environ.get('CREDENTIAL_ENCRYPTION_KEY') or getattr(env, 'CREDENTIAL_ENCRYPTION_KEY', '')
    if not key:
        raise RuntimeError('未配置 CREDENTIAL_ENCRYPTION_KEY；升级时必须保留原密钥')
    return Fernet(key.encode())


def encrypt(plain_text):
    """明文 -> 密文（字符串）"""
    if not plain_text:
        return ''
    return _fernet().encrypt(plain_text.encode()).decode()


def decrypt(cipher_text):
    """密文 -> 明文（字符串）"""
    if not cipher_text:
        return ''
    return _fernet().decrypt(cipher_text.encode()).decode()
