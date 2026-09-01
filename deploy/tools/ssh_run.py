#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用 SSH 执行辅助脚本：通过 paramiko 密码登录远程服务器执行命令。
用法：
    python ssh_run.py "命令"
    echo "命令" | python ssh_run.py     # 从 stdin 读取（支持多行）
环境变量覆盖：
    SSH_HOST / SSH_USER / SSH_PASSWORD
"""
import os
import sys

import paramiko

HOST = os.environ.get("SSH_HOST", "YOUR_SERVER_IP")
USER = os.environ.get("SSH_USER", "root")
PASSWORD = os.environ.get("SSH_PASSWORD", "YOUR_SSH_PASSWORD")
PORT = int(os.environ.get("SSH_PORT", "22"))


def run(command, timeout=180):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()
    return code, out, err


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = sys.stdin.read()
    command = command.strip()
    if not command:
        print("用法: python ssh_run.py \"命令\" 或 echo \"命令\" | python ssh_run.py")
        sys.exit(2)
    code, out, err = run(command)
    sys.stdout.write(out)
    if err:
        sys.stderr.write("\n[STDERR]\n" + err)
    sys.exit(code)
