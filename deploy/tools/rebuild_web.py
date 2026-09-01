#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 web 镜像并重启容器（长超时，流式输出）"""
import sys
import paramiko

HOST = "YOUR_SERVER_IP"
USER = "root"
PASSWORD = "YOUR_SSH_PASSWORD"
PORT = 22

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=20)

cmd = "cd /opt/devops-platform && docker compose build dvadmin3-web 2>&1"
stdin, stdout, stderr = client.exec_command(cmd, timeout=1800)
for line in iter(stdout.readline, ""):
    sys.stdout.write(line)
    sys.stdout.flush()
code = stdout.channel.recv_exit_status()
err = stderr.read().decode("utf-8", errors="replace")
if err:
    sys.stdout.write("\n[STDERR]\n" + err)
sys.stdout.write(f"\n[BUILD EXIT] {code}\n")
client.close()
sys.exit(code)
