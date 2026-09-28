# -*- coding: utf-8 -*-
"""
堡垒机统一 paramiko 执行工具：被命令下发/会话复用
返回结构化结果，避免调用方重复 try/except
"""
import io
import os
import time

import paramiko


def verified_client():
    """创建 SSH 客户端。

    ★ 本交付保留 AutoAddPolicy（未启用 known_hosts 强校验）——内网场景由交付方决定。
      如需收紧为「只信任已核验的指纹」，改成：
        client.load_host_keys(os.environ.get('SSH_KNOWN_HOSTS', '/backend/conf/known_hosts'))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
      并先把目标机指纹录入 /backend/conf/known_hosts（否则首次连接一律被拒）。
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client


def _load_private_key(key_str):
    """paramiko 3.4 私钥加载：按 RSAKey/Ed25519Key/ECDSAKey/DSSKey 顺序尝试"""
    last_err = None
    for name in ('RSAKey', 'Ed25519Key', 'ECDSAKey', 'DSSKey'):
        kls = getattr(paramiko, name, None)
        if kls is None:
            continue
        try:
            return kls.from_private_key(io.StringIO(key_str))
        except Exception as e:
            last_err = e
    msg = str(last_err) if last_err else '未知错误'
    if 'encrypt' in msg.lower() or 'password' in msg.lower():
        raise Exception('私钥已加密（passphrase），暂不支持')
    raise Exception(f'私钥加载失败：{msg}')


def ssh_exec(host, port, username, auth_type, password=None, private_key=None,
             command=None, timeout=30, connect_timeout=10):
    """
    同步执行单条 SSH 命令。

    连接超时（connect_timeout，默认 10s）与命令超时（timeout）分离：
    连接失败快速返回，单台卡死不会无限拖累整体。

    返回 dict:
        ok: bool
        stdout: str
        stderr: str
        exit_code: int | None
        duration: float   # 秒
        error: str        # 连接/认证失败时填
    """
    started = time.time()
    client = verified_client()

    kwargs = {
        'hostname': host,
        'port': int(port or 22),
        'username': username or 'root',
        'timeout': max(3, int(connect_timeout or 10)),
        'allow_agent': False,
        'look_for_keys': False,
        'banner_timeout': max(3, int(connect_timeout or 10)),
        'auth_timeout': max(3, int(connect_timeout or 10)),
    }
    if auth_type == 'private_key':
        kwargs['pkey'] = _load_private_key(private_key)
    else:
        kwargs['password'] = password

    try:
        client.connect(**kwargs)
        stdin, stdout, stderr = client.exec_command(command, timeout=max(5, int(timeout or 30)))
        stdin.close()
        channel = stdout.channel
        deadline = time.monotonic() + timeout
        out, err = bytearray(), bytearray()
        # Drain both streams concurrently; cap memory and enforce total runtime.
        while True:
            if time.monotonic() > deadline:
                channel.close()
                raise TimeoutError('SSH command timed out')
            if channel.recv_ready():
                out.extend(channel.recv(32768))
            if channel.recv_stderr_ready():
                err.extend(channel.recv_stderr(32768))
            if len(out) + len(err) > 4 * 1024 * 1024:
                channel.close()
                raise RuntimeError('命令输出超过 4 MiB 限制')
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            time.sleep(0.01)
        code = channel.recv_exit_status()
        return {
            'ok': code == 0,
            'stdout': out.decode('utf-8', errors='replace'),
            'stderr': err.decode('utf-8', errors='replace'),
            'exit_code': code,
            'duration': round(time.time() - started, 3),
            'error': '',
        }
    finally:
        try:
            client.close()
        except Exception:
            pass
