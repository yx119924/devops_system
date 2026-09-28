# XwOps · 企业级 DevOps 平台

一套面向中小规模运维团队自建的 DevOps 平台，把 **CMDB、堡垒机、监控告警、日志检索、发布管理、AI 运维助手** 收进同一个控制台，替代「JumpServer + 一堆散落脚本 + 多个监控面板」的组合。

> 底座为开源项目 **DVAdmin3**（Django 4.2 + DRF + Vue3），在其之上做业务定制。
> 详见 `NOTICE` 与 `LICENSE`。

---

## 版本基线

本仓库是一条**完整、自包含**的工程快照：`backend/` + `web/` + `docker_env/` + `docker-compose.yml`
全在，`git clone` 之后即可构建、部署、启动，不依赖任何外部增量包。

源码基线 = **线上运行版本 + 内网部署必需的安全加固集**，与 `docker/` 下的镜像制品**同源、同代、必须配对使用**。

已合入的加固项（凭据 Fernet 加密、模板渲染沙箱、Webhook 请求鉴权、资产授权闸、录像鉴权、
审计归属、共享 Redis 缓存、部署前体检命令）：

- ✅ 已合入本仓库
- ✅ 已通过**离线验证**（后端 95 条断言 + 前端 50 条断言全绿）
- ⚠️ **尚未在真机跑通**（数据库迁移与页面端到端需在目标环境完成）

**主动跳过**的加固项（避免引入未验证的破坏性变更）：Web SSH 一次性票据整链、Grafana SSO、
`known_hosts` 强校验（`bastion/ssh_client.py` 内附「一行收紧」改法）。
命令下发的**「手动 IP」兜底**按内网应急需求**保留**。

> ⚠️ **升级须知**：这些加固会改变前后端契约（后端不再下发通知渠道敏感字段），
> 因此**必须同步使用重新构建的前端镜像**，不能用旧前端配新后端。
> 完整清单与前置条件见 `CHANGELOG.md` 的「v1.0.0 重新发行说明」。

---

## 功能模块

| 模块 | 能力 |
|---|---|
| **CMDB** | 机房 / 环境 / 业务线 / 服务器资产管理，Excel 批量导入 |
| **堡垒机** | Web SSH 终端、会话录像、命令审计、批量命令下发（CMDB 多选 + 手动 IP 兜底） |
| **监控** | Prometheus 数据源接入、指标查询、Grafana 大屏嵌入 |
| **告警** | 告警规则、通知渠道（邮件 / 企微 / 飞书）、告警组、告警事件、模板 |
| **日志** | 日志源管理、filebeat 采集配置下发与回显、日志检索 |
| **发布** | Jenkins 服务器接入、Job 目录树、构建发布、按角色的 Job 可见性授权 |
| **AI 运维助手** | 多供应商模型配置（BYOK）、智能问答、工具调用（只读优先 + 四道安全闸） |
| **系统管理** | 用户 / 角色 / 菜单 / 按钮权限 / 部门 / 字典 / 系统配置（DVAdmin 原生能力） |

---

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 · Django 4.2.14 · DRF 3.15 · Channels 4.1 · Celery · uvicorn |
| 前端 | Vue 3 · Vite · TypeScript · Element Plus · fast-crud 1.21.2 · Pinia |
| 数据库 | MySQL 8.0 |
| 缓存 / 队列 | Redis 6.2.6 |
| 网关 | nginx（容器内） |
| 部署 | Docker Compose（5 个容器） |

---

## 目录结构

```
.
├── backend/                     # 后端源码
│   ├── application/             # Django 工程配置（settings / urls / asgi）
│   ├── conf/                    # 环境配置（env.example.py 为模板）
│   ├── dvadmin/
│   │   ├── system/              # DVAdmin 系统管理（上游）
│   │   ├── cmdb/ bastion/ monitor/ alert/ log/ jenkins/ aiagent/
│   │   │                        # ↑ 自研业务模块
│   │   └── utils/               # 公共基类 / 过滤器 / 中间件
│   ├── register_*.py            # 菜单按钮注册脚本（历史工具，见下方说明）
│   └── requirements.txt
├── web/                         # 前端源码（Vue3 + Vite）
├── docker_env/                  # nginx / mysql / redis / 监控 配置
├── init/01_seed_config.sql      # 初始化数据：菜单、角色、权限、字典、系统配置
├── docker/                      # 镜像加载脚本 + 校验清单（镜像本体走 Releases）
├── docker-compose.yml           # 5 个服务的编排
├── DEPLOY.md                    # ★ 从零部署手册（唯一的部署文档）
├── DEPLOY-ARCHITECTURE.md       # 部署架构说明
├── PRODUCT-ARCHITECTURE.md      # 产品架构说明
├── .env.example                 # compose 变量模板
└── .gitattributes               # 强制 LF 换行（Windows 编辑 / Linux 部署）
```

---

## 快速开始

**完整步骤见 [`DEPLOY.md`](DEPLOY.md)**，这里只给最简路径：

```bash
# 1. 拉代码
git clone https://github.com/yx119924/devops_system.git xwops && cd xwops

# 2. 下载镜像包（490 MB，走 Releases 附件）并加载
curl -L --retry 3 -o docker/xwops-images-v1.0.0.tar \
  https://github.com/yx119924/devops_system/releases/download/v1.0.0/xwops-images-v1.0.0.tar
bash docker/load-images.sh

# 3. 改两个配置文件
cp .env.example .env                              # 改 MYSQL_PASSWORD / REDIS_PASSWORD / ALERT_WEBHOOK_SECRET
cp backend/conf/env.example.py backend/conf/env.py  # 改密码 + 生成 CREDENTIAL_ENCRYPTION_KEY / SECRET_KEY

# 4. 启动
docker compose up -d

# 5. 初始化数据库（仅首次）
docker exec dvadmin3-django python manage.py migrate
docker exec dvadmin3-django python manage.py init -y
docker exec -i dvadmin3-mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" django-vue3-admin' \
  < init/01_seed_config.sql
docker exec dvadmin3-django python manage.py migrate_secrets --apply   # 凭据加密迁移

# 6. 体检（应输出「配置、表字段、接口挂载及运行时导入检查通过。」）
docker exec dvadmin3-django python manage.py security_preflight
```

> 🔴 `ALERT_WEBHOOK_SECRET` 至少 32 字符，且要与 `docker_env/alertmanager/alertmanager.yml`
> 里的 Bearer 值一致；不配的话告警 Webhook 一律返回 **503**。

访问 `http://<服务器IP>:8080`，初始账号 `superadmin / admin123456`（**登录后立即修改**）。

---

## 关于镜像

镜像 **不在本 Git 仓库内**（490 MB，超出 GitHub 单文件 100 MB 上限），
通过 **Releases 附件**分发。打包内容与加载方式见 [`docker/README.md`](docker/README.md)。

| 镜像 | 说明 |
|---|---|
| `xwops/web:1.0.0` | 前端 nginx（**前端已编译进镜像**） |
| `xwops/django:1.0.0` | 后端运行环境（**不含业务代码**，靠 `./backend:/backend` 挂载） |
| `xwops/celery:1.0.0` | 异步任务运行环境（同上） |
| `mysql:8.0` / `redis:6.2.6-alpine` | 数据库 / 缓存（官方镜像） |

> ⚠️ 因为 `django` / `celery` 镜像不含业务代码，**`backend/` 源码目录是运行必需品**，
> 不能只拿镜像不要源码。

---

## 关于 `register_*.py`

`backend/` 下有几个 `register_*.py` / `reg_*.py`，用于把菜单、按钮权限写进数据库。

**正常从零部署不需要执行它们** —— `init/01_seed_config.sql` 已经包含完整的
菜单（51 条）、按钮（207 条）、授权（667 条）数据。

保留它们是为了：以后新增模块时，可以照抄其中的写法生成菜单与按钮权限
（DVAdmin 的按钮权限必须逐条登记，否则非超管用户看不到按钮）。

---

## 文档索引

| 文档 | 内容 |
|---|---|
| [`DEPLOY.md`](DEPLOY.md) | **从零部署手册** —— 装 Docker 到验证通过，逐步命令 |
| [`DEPLOY-ARCHITECTURE.md`](DEPLOY-ARCHITECTURE.md) | 部署架构：容器拓扑、网络、端口、数据落盘、备份与恢复 |
| [`PRODUCT-ARCHITECTURE.md`](PRODUCT-ARCHITECTURE.md) | 产品架构：模块划分、权限模型、关键设计取舍 |
| [`docker/README.md`](docker/README.md) | 镜像清单、下载与加载方式 |
| [`CHANGELOG.md`](CHANGELOG.md) | 变更记录 |

---

## 许可

本项目基于 DVAdmin3（Apache License 2.0）二次开发，遵循同一许可。
上游声明见 `LICENSE` 与 `NOTICE`。
