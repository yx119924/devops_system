# -*- coding: utf-8 -*-
"""
Web SSH 终端消费者：浏览器 <-> WebSocket <-> paramiko <-> 目标服务器
含会话录像（asciinema cast 格式）与命令审计
认证方式：URL 路径携带 JWT token（复用 DVAdmin3 的 SECRET_KEY 解码方案）
"""
import asyncio
import io
import json
import os
import time
from datetime import datetime

import jwt
import paramiko
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from application import settings
from dvadmin.bastion.models import CommandLog, Credential, SessionRecord, is_dangerous_command
from dvadmin.cmdb.models import Server
from dvadmin.system.models import Users


class SshConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self.scope['url_route']['kwargs'].get('token')
        self.server_id = self.scope['url_route']['kwargs'].get('server_id')
        credential_id = self.scope['url_route']['kwargs'].get('credential_id')
        self.credential_id = credential_id if credential_id not in ('0', '', 'null', None) else None

        # JWT 认证：解码 token 拿 user_id
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get('user_id')
            self.user = await sync_to_async(Users.objects.get)(id=user_id)
        except Exception:
            await self.close()
            return

        await self.accept()

        # 建立 SSH 连接（paramiko 阻塞操作放线程）
        try:
            self.ssh, self.server, self.credential = await asyncio.to_thread(self._connect_ssh)
            self.channel = self.ssh.invoke_shell(width=120, height=32)
            self.channel.settimeout(0.0)
        except Exception as e:
            import traceback
            print(f"[SSH连接失败] {traceback.format_exc()}", flush=True)
            msg = str(e) or e.__class__.__name__
            await self.send(text_data=json.dumps({'type': 'error', 'message': msg}))
            await self.close()
            return

        # 记录会话 + 初始化录像 + 命令审计状态
        self.session = await asyncio.to_thread(self._create_session)
        self.input_buffer = ''
        self.start_time = time.time()
        self.cast_path = ''
        await asyncio.to_thread(self._init_recording)

        self.read_task = asyncio.create_task(self._read_loop())

    def _connect_ssh(self):
        """同步：建立 paramiko SSH 连接"""
        try:
            server = Server.objects.get(id=self.server_id)
        except Server.DoesNotExist:
            raise Exception('服务器不存在')

        credential = None
        if self.credential_id:
            try:
                credential = Credential.objects.get(id=self.credential_id)
            except Credential.DoesNotExist:
                raise Exception('凭据不存在')

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {
            'username': credential.username if credential else 'root',
            'port': server.ssh_port or 22,
            'timeout': 15,
            'allow_agent': False,
            'look_for_keys': False,
        }
        if credential:
            if credential.auth_type == 'password':
                kwargs['password'] = credential.get_password()
            else:
                key_str = credential.get_private_key()
                last_err = None
                for kls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
                    try:
                        kwargs['pkey'] = kls.from_private_key(io.StringIO(key_str))
                        break
                    except Exception as e:
                        last_err = e
                else:
                    msg = str(last_err) if last_err else '未知错误'
                    if 'encrypt' in msg.lower() or 'password' in msg.lower():
                        raise Exception('私钥已加密（passphrase），暂不支持')
                    raise Exception(f'私钥加载失败：{msg}')

        client.connect(server.ip, **kwargs)
        return client, server, credential

    def _create_session(self):
        """同步：创建会话记录"""
        return SessionRecord.objects.create(
            creator=self.user,
            server=self.server,
            credential=self.credential,
            username=self.credential.username if self.credential else 'root',
            ip=self.server.ip,
            status='active',
        )

    def _init_recording(self):
        """同步：创建 asciinema cast 录像文件并写 header"""
        try:
            base = getattr(settings, 'MEDIA_ROOT', '/backend/media')
            session_dir = os.path.join(base, 'sessions')
            os.makedirs(session_dir, exist_ok=True)
            self.cast_path = os.path.join(session_dir, f'{self.session.id}.cast')
            header = {"version": 2, "width": 120, "height": 32, "timestamp": int(time.time())}
            with open(self.cast_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(header) + '\n')
            self.session.recording = self.cast_path
            self.session.save(update_fields=['recording'])
        except Exception as e:
            print(f"[录像初始化失败] {e}", flush=True)

    def _append_cast(self, event_type, data):
        """同步：追加录像事件"""
        if not self.cast_path:
            return
        try:
            t = round(time.time() - self.start_time, 6)
            with open(self.cast_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps([t, event_type, data], ensure_ascii=False) + '\n')
        except Exception:
            pass

    def _save_command(self, command):
        """同步：保存命令审计 + 判断高危"""
        dangerous = is_dangerous_command(command)
        CommandLog.objects.create(
            session=self.session,
            source='session',
            command=command,
            is_dangerous=dangerous,
        )

    def _extract_command(self, data):
        """同步：从输入流累积并提取命令，返回完整命令或 None"""
        result = None
        for ch in data:
            if ch in ('\r', '\n'):
                cmd = self.input_buffer.strip()
                if cmd:
                    result = cmd
                self.input_buffer = ''
            elif ch in ('\x7f', '\x08'):
                self.input_buffer = self.input_buffer[:-1]
            elif ch == '\x03':
                self.input_buffer = ''
            elif ord(ch) >= 32:
                self.input_buffer += ch
        return result

    async def _read_loop(self):
        """后台循环读取 SSH 输出，录像并推给浏览器"""
        try:
            while True:
                data = await asyncio.to_thread(self._read_channel)
                if data:
                    await asyncio.to_thread(self._append_cast, 'o', data)
                    await self.send(text_data=json.dumps({'type': 'stdout', 'data': data}))
                else:
                    await asyncio.sleep(0.01)
        except Exception:
            pass

    def _read_channel(self):
        """同步：非阻塞读 channel"""
        try:
            return self.channel.recv(65535).decode('utf-8', errors='replace')
        except Exception:
            return ''

    async def receive(self, text_data=None, bytes_data=None):
        """收到浏览器输入：录像 + 命令提取 + 转发到 SSH"""
        if not text_data:
            return
        try:
            msg = json.loads(text_data)
        except Exception:
            return
        try:
            if msg.get('type') == 'input':
                data = msg.get('data', '')
                # 录像（输入事件）
                await asyncio.to_thread(self._append_cast, 'i', data)
                # 命令提取
                cmd = self._extract_command(data)
                if cmd:
                    await asyncio.to_thread(self._save_command, cmd)
                # 转发到 SSH
                await asyncio.to_thread(self.channel.send, data.encode('utf-8'))
            elif msg.get('type') == 'resize':
                await asyncio.to_thread(self.channel.resize_pty, msg.get('cols', 120), msg.get('rows', 32))
        except Exception:
            pass

    async def disconnect(self, close_code):
        if hasattr(self, 'session'):
            try:
                await asyncio.to_thread(self._close_session)
            except Exception:
                pass
        if hasattr(self, 'read_task'):
            self.read_task.cancel()
        if hasattr(self, 'channel'):
            try:
                self.channel.close()
            except Exception:
                pass
        if hasattr(self, 'ssh'):
            try:
                self.ssh.close()
            except Exception:
                pass

    def _close_session(self):
        """同步：更新会话结束状态"""
        self.session.end_time = datetime.now()
        if self.session.start_time:
            self.session.duration = int((self.session.end_time - self.session.start_time).total_seconds())
        self.session.status = 'closed'
        self.session.save(update_fields=['end_time', 'duration', 'status'])
