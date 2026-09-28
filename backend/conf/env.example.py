# -*- coding: utf-8 -*-
"""
XwOps 环境配置模板。

用法：
    cp backend/conf/env.example.py backend/conf/env.py
然后把下面所有 CHANGE_ME 换成你自己的值。

★ 本文件必须存在，否则 backend 启动时会 ImportError
  （application/settings.py 里有 `from conf.env import *`，
    bastion/crypto.py 里有 `from conf.env import CREDENTIAL_ENCRYPTION_KEY`）。
★ 真实值只写在 conf/env.py，该文件已被 .gitignore 忽略，绝不要提交。
"""
import os

from application.settings import BASE_DIR

# ================================================= #
# *************** MySQL 数据库配置 ***************** #
# ================================================= #
DATABASE_ENGINE = "django.db.backends.mysql"
DATABASE_NAME = "django-vue3-admin"      # 库名（含连字符，SQL 里需用反引号）
DATABASE_HOST = "dvadmin3-mysql"         # ★ 容器间通信用 compose 服务名，不要写 localhost
DATABASE_PORT = 3306
DATABASE_USER = "root"
DATABASE_PASSWORD = "CHANGE_ME_DB_PASSWORD"   # ★ 必改：与 .env 的 MYSQL_PASSWORD 一致

TABLE_PREFIX = "dvadmin_"

# ================================================= #
# ******************* Redis 配置 ****************** #
# ================================================= #
REDIS_DB = 1
CELERY_BROKER_DB = 3
REDIS_PASSWORD = "CHANGE_ME_REDIS_PASSWORD"   # ★ 必改：与 .env 的 REDIS_PASSWORD 一致
REDIS_HOST = "dvadmin3-redis"                 # ★ 容器间通信用 compose 服务名
REDIS_URL = f'redis://:{REDIS_PASSWORD or ""}@{REDIS_HOST}:6379'

# ★★ REDIS_DB / REDIS_URL 还会被 application/settings.py 用来组装 CACHES
#    （平台默认缓存）。Webhook 的「短时去重 / 每分钟限流」依赖共享缓存：
#    若缓存退化为 LocMemCache，uvicorn 多个 worker 各有独立内存，去重与限流会
#    静默失效（不报错，但形同虚设）。可用 manage.py security_preflight 自检。

# ================================================= #
# ************* 告警 Webhook 认证密钥 ************** #
# ================================================= #
# ★ v1.1.0 起：/api/alert/webhook/receiver/ 要求 Bearer 认证。
#   长度必须 >= 32 字符，否则平台一律返回 503「告警接收密钥未配置」，
#   导致 Alertmanager 推来的告警被全部丢弃。
#   必须与 docker_env/alertmanager/alertmanager.yml 的
#   http_config.authorization.credentials 保持一致。
#   （也可改由 compose 环境变量 ALERT_WEBHOOK_SECRET 注入，两者取其一。）
#
#   生成一个：python -c "import secrets; print(secrets.token_urlsafe(32))"
ALERT_WEBHOOK_SECRET = "CHANGE_ME_AT_LEAST_32_CHARS_RANDOM"

# ================================================= #
# ******************* 会话密钥 ******************** #
# ================================================= #
# ★ v1.1.0 起 application/settings.py 的 SECRET_KEY 会优先取这里的值。
#   不配置则退化为仓库里的占位串（django-insecure-CHANGE-ME-...），
#   等于把签名密钥公开在源码里。
#   ★ 更换它会让所有已签发的 JWT 立即失效（用户需重新登录），
#     也会影响 WebSocket 的 token 解码（consumers.py 用同一个密钥），
#     两者同步失效，属预期行为。
#   ★ 它与 CREDENTIAL_ENCRYPTION_KEY 相互独立，更换不影响已保存的凭据。
#
#   生成一个：python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY = "CHANGE_ME_RANDOM_SECRET_KEY"

# ================================================= #
# ********** 凭据加密密钥（堡垒机 / Jenkins / 日志源）*******
# ================================================= #
# ★★★ 必改，且务必离线备份 —— 换了它，所有已保存的 SSH 密码 /
#     Jenkins Token / ES 密码都将无法解密（表现为「凭据失效」）。
# 生成方法（在 backend 容器内执行）：
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIAL_ENCRYPTION_KEY = "CHANGE_ME_FERNET_KEY_44_CHARS_BASE64"

# ================================================= #
# ****************** 功能启停 ********************* #
# ================================================= #
DEBUG = False                 # ★ 生产环境必须为 False
ENABLE_LOGIN_ANALYSIS_LOG = False   # 内网无外网时关闭，避免登录时卡住
LOGIN_NO_CAPTCHA_AUTH = False       # 正式环境建议保留验证码

# ★★ 必须改成实际访问用的主机名/IP，不能留 ["*"] —— `manage.py security_preflight` 会直接拦下。
#   例：ALLOWED_HOSTS = ["192.168.1.50", "xwops.example.com", "127.0.0.1", "localhost"]
#   ★ 端口不用写：nginx 用 `proxy_set_header Host $http_host` 原样透传浏览器地址（含端口），
#     而 Django 校验时会自动忽略端口。
#   ★ "127.0.0.1" 必须在列表里 —— 容器内的健康检查（curl/docker exec 打 127.0.0.1:8000）
#     带的 Host 就是它，不在列表会被判 Host 非法。
ALLOWED_HOSTS = ["*"]
COLUMN_EXCLUDE_APPS = []
