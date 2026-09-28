# 部署架构说明

> 配套文档：[`DEPLOY.md`](DEPLOY.md)（部署步骤）、[`PRODUCT-ARCHITECTURE.md`](PRODUCT-ARCHITECTURE.md)（产品架构）

---

## 一、整体拓扑

```
                        用户浏览器
                             │  http://<服务器IP>:8080
                             ▼
        ┌────────────────────────────────────────────┐
        │  Docker 自定义网络  network  172.31.0.0/16  │
        │                                            │
        │   dvadmin3-web      172.31.0.11            │
        │   ┌──────────────────────────────────┐     │
        │   │ nginx                            │     │
        │   │  · 静态资源（前端已编译进镜像）    │     │
        │   │  · /api/(.*) → 剥掉首层 /api 转发 │     │
        │   └───────────────┬──────────────────┘     │
        │                   │ http://172.31.0.12:8000 │
        │                   ▼                         │
        │   dvadmin3-django   172.31.0.12            │
        │   ┌──────────────────────────────────┐     │
        │   │ uvicorn (ASGI)  ×4 workers       │     │
        │   │ Django + DRF + Channels          │     │
        │   │ 代码来自挂载 ./backend:/backend   │     │
        │   └───┬───────────────────────┬──────┘     │
        │       │                       │             │
        │       ▼                       ▼             │
        │  mysql 172.31.0.13      redis 172.31.0.15  │
        │  （数据落盘到宿主机）      （AOF 持久化）     │
        │       ▲                       ▲             │
        │       │                       │             │
        │   dvadmin3-celery   172.31.0.14            │
        │   （worker + beat，同样挂载 backend）        │
        └────────────────────────────────────────────┘
                             │ SSH(22) 出站
                             ▼
             被管服务器 / Jenkins / Prometheus / ES …
```

**关键点**：平台自身只暴露 8080；对外的所有「主动连接」（SSH、Jenkins API、Prometheus 查询、ES 检索）都是**从 django 容器出站**发起的。

---

## 二、容器网络（静态 IP 分配）

| 服务 | 静态 IP | 容器名 | 说明 |
|---|---|---|---|
| web | `172.31.0.11` | `dvadmin3-web` | 对外入口 |
| django | `172.31.0.12` | `dvadmin3-django` | nginx 通过此 IP 回源 |
| mysql | `172.31.0.13` | `dvadmin3-mysql` | |
| celery | `172.31.0.14` | `dvadmin3-celery` | |
| redis | `172.31.0.15` | `dvadmin3-redis` | |

**为什么用静态 IP 而不是服务名？**

nginx 在 `proxy_pass` 时如果写服务名，容器启动顺序或 DNS 抖动会影响解析；
静态 IP 让配置**完全确定**，也便于排查。
代价是：`docker_env/nginx/my.conf` 里的 `proxy_pass` 与 `docker-compose.yml`
里的 `ipv4_address` **必须成对修改**，改一个不改另一个就会 502。

> 网段选 `172.31.0.0/16` 而不是常见的 `172.17` / `172.18`，是为了降低与
> 企业办公网、机房网段冲突的概率。若仍冲突，两处一起改。

---

## 三、端口暴露策略

| 端口 | 映射 | 暴露范围 | 理由 |
|---|---|---|---|
| 8080 | `8080:8080` | **公网可达** | 平台唯一入口 |
| 8000 | `8000:8000` | 公网可达 | 便于直连后端排查；**生产环境建议去掉此映射** |
| 3306 | `127.0.0.1:3306:3306` | 仅本机 | 数据库不外露 |
| 6379 | `127.0.0.1:6379:6379` | 仅本机 | 缓存不外露 |

> 若不希望 8000 对外，删掉 `docker-compose.yml` 中 `dvadmin3-django` 的
> `ports` 段落即可，容器间通信不受影响（走容器网络）。

---

## 四、数据落盘位置

所有持久化数据都在**宿主机目录**，容器删除不丢数据：

| 数据 | 宿主机路径 | 是否入库 |
|---|---|---|
| MySQL 数据 | `docker_env/mysql/data/` | ❌ gitignore |
| MySQL 配置 | `docker_env/mysql/conf.d/my.cnf` | ✅ |
| Redis 数据 | `docker_env/redis/data/` | ❌ gitignore |
| Redis 配置 | `docker_env/redis/redis.conf` | ✅ |
| 上传附件 | `backend/media/` | ❌ gitignore |
| 应用日志 | `logs/log/` | ❌ gitignore |
| nginx 配置 | `docker_env/nginx/my.conf` | ✅ |

> **备份时至少覆盖**：`docker_env/mysql/data/`（或用 `mysqldump`）、
> `backend/media/`、以及 `backend/conf/env.py` 里的 `CREDENTIAL_ENCRYPTION_KEY`。

---

## 五、启动依赖

```
mysql ──┐
        ├─→ django ──→ (web 通过静态 IP 回源，无强依赖声明)
        └─→ celery
redis ──┘
```

`docker-compose.yml` 里 `django` / `celery` 声明了 `depends_on: mysql`。
注意 `depends_on` **只保证容器启动顺序，不保证 MySQL 已就绪**。
MySQL 首次初始化需要 10–30 秒，若此时 django 已启动并报连接失败，
等 MySQL 就绪后 django 会自行重连；若未恢复，重启一次即可：

```bash
docker compose restart dvadmin3-django
```

---

## 六、故障域与恢复

| 故障 | 影响 | 恢复 |
|---|---|---|
| django 容器挂 | 所有接口 502，前端页面能打开但无数据 | `docker compose restart dvadmin3-django` |
| web 容器挂 | 整站不可访问 | `docker compose restart dvadmin3-web` |
| MySQL 挂 | 全站不可用 | `docker compose restart dvadmin3-mysql` |
| Redis 挂 | 缓存失效、Celery 停摆、WebSocket 断开；**登录态也可能受影响** | `docker compose restart dvadmin3-redis` |
| celery 挂 | 定时任务不执行；**同步类接口不受影响** | `docker compose restart dvadmin3-celery` |
| 宿主机重启 | 全部容器 | 所有服务均设 `restart: always`，开机自动拉起 |

---

## 七、备份与恢复

### 备份

```bash
# 1) 数据库
docker exec dvadmin3-mysql sh -c \
  'mysqldump -h127.0.0.1 --protocol=TCP -uroot -p"$MYSQL_ROOT_PASSWORD" \
   --single-transaction --routines --triggers django-vue3-admin' \
  > backup_db_$(date +%F).sql

# 2) 上传附件
tar czf backup_media_$(date +%F).tar.gz backend/media

# 3) ★ 加密密钥（丢了就解不开已保存的凭据，务必单独妥善保管）
grep CREDENTIAL_ENCRYPTION_KEY backend/conf/env.py
```

### 恢复

```bash
# 1) 起库
docker compose up -d dvadmin3-mysql
# 2) 导回
docker exec -i dvadmin3-mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" django-vue3-admin' \
  < backup_db_2026-09-28.sql
# 3) 附件解包
tar xzf backup_media_2026-09-28.tar.gz
```

> 🔴 **恢复的前提**：`CREDENTIAL_ENCRYPTION_KEY` 与备份时一致。
> 否则所有堡垒机凭据、Jenkins Token、日志源密码都要重新录入。

---

## 八、升级路径

| 改动类型 | 操作 | 是否重建镜像 |
|---|---|---|
| 改后端 Python 代码 | `git pull` → `docker compose restart dvadmin3-django` | ❌ 不需要（挂载生效） |
| 改前端 `.vue` | `git pull` → `docker compose up -d --build dvadmin3-web` | ✅ 需要 |
| 改 `requirements.txt` | `docker compose up -d --build dvadmin3-django dvadmin3-celery` | ✅ 需要 |
| 改 nginx 配置 | 改文件 → `docker exec dvadmin3-web nginx -s reload` | ❌ 不需要 |
| 换整套镜像 | 加载新 tar → 改 compose 里的 tag → `up -d` | — |
| 新增数据库表 | `git pull` → `docker compose restart dvadmin3-django` → `migrate` | ❌ 不需要 |

**前端为什么必须重建镜像**：前端产物是 `npm run build` 后 COPY 进 nginx 镜像的，
容器里**没有源码也没有 node 环境**，无法热更新。

---

## 九、可逆性设计

部署新平台时最怕「装上了却退不回去」。本方案的可逆点：

| 动作 | 回退方式 |
|---|---|
| 部署整栈 | `docker compose down` + 删除目录，宿主机无残留（除 Docker 本身） |
| 换数据库数据 | 保留部署前的 `mysqldump` 备份，导回即可 |
| 接内网 Prometheus | 监控栈是**独立组件**，不接入即零影响；接入前先备份原 Prometheus 配置 |
| 改 nginx 配置 | 配置在宿主机文件里，改回旧版 + `nginx -s reload` 即恢复 |

> 本平台的监控配置（`docker_env/prometheus/`、`docker_env/alertmanager/`）
> **不在 compose 内**，意味着「不部署监控」是默认状态，不会被动影响既有监控体系。
