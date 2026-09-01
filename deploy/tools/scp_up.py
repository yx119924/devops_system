#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFTP 上传辅助脚本：把本地文件上传到远程服务器。
用法：
    python scp_up.py <本地文件> <远程绝对路径>
"""
import os
import sys

import paramiko

HOST = os.environ.get("SSH_HOST", "YOUR_SERVER_IP")
USER = os.environ.get("SSH_USER", "root")
PASSWORD = os.environ.get("SSH_PASSWORD", "YOUR_SSH_PASSWORD")
PORT = int(os.environ.get("SSH_PORT", "22"))


def upload(local_path, remote_path):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
    sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    client.close()
    print(f"uploaded {local_path} -> {remote_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python scp_up.py <本地文件> <远程绝对路径>")
        sys.exit(2)
    upload(sys.argv[1], sys.argv[2])
