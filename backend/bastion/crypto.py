# -*- coding: utf-8 -*-
"""
凭据加密工具：Fernet 对称加密
密钥来自 conf/env.py 的 CREDENTIAL_ENCRYPTION_KEY
"""
from cryptography.fernet import Fernet

from conf.env import CREDENTIAL_ENCRYPTION_KEY


def _fernet():
    return Fernet(CREDENTIAL_ENCRYPTION_KEY.encode())


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
