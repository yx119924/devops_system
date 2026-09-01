#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
递归上传本地目录到远程服务器（SFTP），自动创建子目录、跳过 __pycache__。
用法：
    python deploy_dir.py <本地目录> <远程绝对路径>
"""
import os
import sys

import paramiko

HOST = os.environ.get("SSH_HOST", "YOUR_SERVER_IP")
USER = os.environ.get("SSH_USER", "root")
PASSWORD = os.environ.get("SSH_PASSWORD", "YOUR_SSH_PASSWORD")
PORT = int(os.environ.get("SSH_PORT", "22"))

SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".idea", ".vscode"}


def upload_dir(sftp, local_dir, remote_dir):
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for d in dirs:
            remote_sub = os.path.join(remote_dir, os.path.relpath(os.path.join(root, d), local_dir)).replace("\\", "/")
            try:
                sftp.mkdir(remote_sub)
            except OSError:
                pass
        for f in files:
            local_path = os.path.join(root, f)
            remote_path = os.path.join(remote_dir, os.path.relpath(local_path, local_dir)).replace("\\", "/")
            sftp.put(local_path, remote_path)
            print(f"  uploaded {remote_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python deploy_dir.py <本地目录> <远程绝对路径>")
        sys.exit(2)
    local_dir = sys.argv[1]
    remote_dir = sys.argv[2]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
    sftp = client.open_sftp()
    try:
        sftp.mkdir(remote_dir)
    except OSError:
        pass
    upload_dir(sftp, local_dir, remote_dir)
    sftp.close()
    client.close()
    print(f"done: {local_dir} -> {remote_dir}")
