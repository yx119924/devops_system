# -*- coding: utf-8 -*-
"""发布流水线的 SFTP 上传能力（「上传制品」节点用）。

为什么不直接改 `bastion/ssh_client.py`
--------------------------------------
堡垒机那条链路已经在线上跑了，本模块**只读地复用**它的两个内部件
（`verified_client` / `_load_private_key`）而不是往里加东西：

  · 本模块出任何问题，改 `release/` 一个目录就能回滚，不必碰堡垒机代码；
  · `bastion/ssh_client.py` 一行不动 ⇒ 命令下发/Web SSH 完全零风险。

★★ 为什么「本地路径」必须被白名单夹住（这是本模块唯一的安全关口）
------------------------------------------------------------------
`local_path` 是用户在页面上填的**任意字符串**。如果直接 `open()` 它再推到目标机，
那么一个只有「发布」权限的人就能：

    把 /backend/conf/env.py（含数据库密码、密钥）或 /etc/shadow
    上传到一台他自己控制的机器上 —— 这是一条完整的**越权读文件**通道。

所以：**只允许上传制品目录内的文件**，目录由 `settings.RELEASE_UPLOAD_ROOT` 指定，
默认 `<MEDIA_ROOT>/release_artifacts`。校验用 `os.path.realpath` 归一后再判前缀，
挡掉 `../` 与符号链接两种穿越。
"""
import os
import stat
import time

from django.conf import settings

from dvadmin.bastion.ssh_client import _load_private_key, verified_client

# 单次上传上限（制品包通常几十 MB，给到 512 MiB 足够，且能挡住"上传整块磁盘"）
MAX_UPLOAD_BYTES = 512 * 1024 * 1024


def upload_root():
    """制品目录的**绝对**路径。

    ★ 不能直接用 `settings.MEDIA_ROOT`：它是相对值 `"media"`（铁律 30），
      相对值会随进程 CWD 漂移 ⇒ 校验用的路径和实际读到的文件不是同一个。
      这里按 `abspath()` 归一，与上传/`consumers.py`/`session.py` 同一口径。
    """
    configured = getattr(settings, 'RELEASE_UPLOAD_ROOT', '') or ''
    if configured:
        return os.path.abspath(configured)
    return os.path.join(os.path.abspath(settings.MEDIA_ROOT), 'release_artifacts')


def resolve_local_path(local_path):
    """把用户填的本地路径解析成允许上传的绝对路径；不合法则抛 ValueError。

    返回 `(abs_path, size)`。
    """
    raw = (local_path or '').strip()
    if not raw:
        raise ValueError('请填写制品文件路径')
    root = upload_root()
    # 相对路径按制品目录解释（用户最常写的就是一个文件名）
    candidate = raw if os.path.isabs(raw) else os.path.join(root, raw)
    real = os.path.realpath(candidate)
    real_root = os.path.realpath(root)
    if real != real_root and not real.startswith(real_root + os.sep):
        raise ValueError(
            '制品文件必须放在服务器上的制品目录内：%s（当前填的是 %s）。'
            '这是刻意的限制：否则「发布」权限会变成任意文件读取权限' % (root, raw))
    if not os.path.isfile(real):
        raise ValueError('制品文件不存在：%s' % real)
    size = os.path.getsize(real)
    if size > MAX_UPLOAD_BYTES:
        raise ValueError('制品文件过大（%d 字节，上限 %d 字节）' % (size, MAX_UPLOAD_BYTES))
    return real, size


def sftp_put(host, port, username, auth_type, password=None, private_key=None,
             local_path=None, remote_path=None, timeout=60, connect_timeout=10):
    """把一个本地文件通过 SFTP 推送到目标机。

    返回 dict: ``{ok, bytes, error, duration}``（与 `ssh_client.ssh_exec` 同风格：
    调用方不需要再写 try/except）。
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
    try:
        if auth_type == 'private_key':
            kwargs['pkey'] = _load_private_key(private_key)
        else:
            kwargs['password'] = password
    except Exception as exc:                                       # noqa: BLE001
        return {'ok': False, 'bytes': 0, 'error': '凭据加载失败：%s' % exc,
                'duration': round(time.time() - started, 3)}

    remote = (remote_path or '').strip()
    if not remote:
        return {'ok': False, 'bytes': 0, 'error': '请填写目标机上的存放路径',
                'duration': round(time.time() - started, 3)}

    sftp = None
    try:
        client.connect(**kwargs)
        client.get_transport().set_keepalive(15)
        sftp = client.open_sftp()
        sftp.get_channel().settimeout(max(10, int(timeout or 60)))
        # 目标目录不存在时不给"自动 mkdir -p"——那会把"路径写错"掩盖成"成功了"，
        # 用户下次看目录结构才发现不对。宁可报错让他明确建目录。
        sftp.put(local_path, remote)
        size = os.path.getsize(local_path)
        return {'ok': True, 'bytes': size, 'error': '',
                'duration': round(time.time() - started, 3)}
    except Exception as exc:                                       # noqa: BLE001
        msg = str(exc) or exc.__class__.__name__
        if 'No such file' in msg or 'not exist' in msg.lower():
            msg = '目标机上目录不存在或不可写：%s（%s）' % (remote, msg)
        return {'ok': False, 'bytes': 0, 'error': msg[:500],
                'duration': round(time.time() - started, 3)}
    finally:
        for closer in (sftp, client):
            try:
                if closer is not None:
                    closer.close()
            except Exception:                                      # noqa: BLE001
                pass


def ensure_upload_root():
    """确保制品目录存在（部署/注册脚本调用，不在请求路径里做 IO 副作用）。"""
    root = upload_root()
    os.makedirs(root, exist_ok=True)
    try:
        os.chmod(root, stat.S_IRWXU)
    except OSError:
        pass
    return root
