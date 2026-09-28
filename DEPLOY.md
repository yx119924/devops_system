# XwOps 平台 · 从零部署手册

> 本仓库**只有这一份部署文档**。后续所有部署相关的变更都直接改这一份。
>
> 适用场景：一台全新的 Linux 服务器，从零把 XwOps 平台跑起来。

---

## 使用前请先确认（30 秒）

本仓库的源码基线 = **线上运行版本 + 内网必需的安全加固集**，与 `docker/` 里的镜像同源同代，
按本文档部署即可跑起来。

> ⚠️ **v1.0.0 已于 2026-09-29 重新发行**（合入加固集 + 清理上游模板残留）。
> 若你手上是 09-28 那一版，请**重新拉代码 + 重新下镜像包** —— 两者必须配对，
> 混用会导致告警渠道页字段异常。变更明细见 `CHANGELOG.md`。

**部署时比一般项目多两个动作**（本文档第 4、6 节都有详细步骤）：

| # | 动作 | 在哪一步 |
|---|---|---|
| 1 | 配置 `ALERT_WEBHOOK_SECRET`（≥32 字符），否则 Webhook 接收端一律 **503** | 第 4 步 |
| 2 | 初始化数据库后执行 `python manage.py migrate_secrets --apply`（密钥加密迁移） | 第 6 步 |

部署完成后建议跑一次体检：`python manage.py security_preflight`（见第 7 步）。

已合入 / 主动跳过的加固项全表见 `CHANGELOG.md` 的「v1.0.0 重新发行说明」。

---

## 0. 部署前

### 0.1 这套东西由什么组成

| 组件 | 容器名 | 作用 |
|---|---|---|
| 前端 + 反向代理 | `dvadmin3-web` | nginx，对外唯一入口，**前端已编译进镜像** |
| 后端 | `dvadmin3-django` | Django + DRF，uvicorn 承载 ASGI |
| 异步任务 | `dvadmin3-celery` | Celery worker + beat |
| 数据库 | `dvadmin3-mysql` | MySQL 8.0 |
| 缓存 | `dvadmin3-redis` | Redis 6.2.6（缓存 / Celery broker / WebSocket 层） |

对外只暴露 **8080** 一个端口；MySQL 与 Redis 只绑 `127.0.0.1`，不对公网开放。

### 0.2 前置条件（不满足请先处理）

| 项 | 要求 | 怎么确认 |
|---|---|---|
| 操作系统 | Linux（CentOS 7+/Ubuntu 20.04+/麒麟等） | `cat /etc/os-release` |
| Docker | 20.10 或更高 | `docker -v` |
| Docker Compose | v2（`docker compose` 子命令） | `docker compose version` |
| 内存 | ≥ 4 GB（推荐 8 GB） | `free -h` |
| 磁盘 | ≥ 50 GB 可用 | `df -h` |
| 网络 | 能访问 GitHub（拉代码 / 下镜像包） | `curl -I https://github.com` |

> **关于外网**：镜像、依赖都已打包装进镜像包，**部署过程不需要拉取 npm / pip 包**。
> 只有「拉代码」和「下镜像包」两步需要外网。若目标机完全无外网，
> 请在本机下载好源码目录和镜像包，再整体拷进去。

### 0.3 端口占用

| 端口 | 用途 | 是否必须 |
|---|---|---|
| 8080 | 平台访问入口 | **必须** |
| 8000 | 后端直连（调试用） | 可选；**默认只绑 `127.0.0.1`**，不对外 |
| 3306 / 6379 | MySQL / Redis（仅本机） | 内部 |

> ★ `docker-compose.yml` 里 Django 写的是 `127.0.0.1:8000:8000`（**不是** `8000:8000`）。
> 这样后端绕过 nginx 也只在服务器本机可达；`DEBUG=True` 时免认证的 API 文档不会被公网翻到。
> 需要远程调试请走 SSH 隧道：`ssh -L 8000:127.0.0.1:8000 root@<服务器>`。

---

## 1. 第一步：安装 Docker

**CentOS / RHEL / 麒麟**：

```bash
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
systemctl enable --now docker
```

**Ubuntu / Debian**：

```bash
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
systemctl enable --now docker
```

验证（两条都要有输出）：

```bash
docker -v
docker compose version
```

> ❌ 如果 `docker compose version` 报错，说明只有老的 `docker-compose`（v1）。
> 请升级到 v2，本文档全部命令使用 `docker compose`。

---

## 2. 第二步：拉取代码

```bash
mkdir -p /opt && cd /opt
git clone https://github.com/yx119924/devops_system.git xwops
cd xwops
```

目录一览（确认这 5 项都在）：

```
xwops/
├── backend/              # 后端源码（★ 运行必需品，见第 5 节说明）
├── web/                  # 前端源码
├── docker_env/           # nginx / mysql / redis 等配置
├── init/01_seed_config.sql   # 初始化数据（菜单、角色、权限、字典）
├── docker/               # 镜像加载脚本与校验清单
├── docker-compose.yml
└── .env.example
```

---

## 3. 第三步：获取并加载镜像

**3.1 下载镜像包**

镜像包 **491 MB**，超出 GitHub 单文件 100 MB 上限，**不在 Git 仓库里**，需从本仓库
**Releases** 页面单独下载：

> Releases 页面：<https://github.com/yx119924/devops_system/releases>

在**仓库根目录**下执行（一条命令直接下载到位）：

```bash
curl -L --retry 3 -o docker/xwops-images-v1.0.0.tar \
  https://github.com/yx119924/devops_system/releases/download/v1.0.0/xwops-images-v1.0.0.tar
```

确认大小对得上：

```bash
ls -l docker/xwops-images-v1.0.0.tar
# 期望大小：514598912 字节（约 490.8 MB）
```

**3.2 校验（必做）**

```bash
cd docker && md5sum -c checksums.txt && cd ..
# 期望输出：xwops-images-v1.0.0.tar: OK
# 期望 MD5：3bc78c4191306387f4016c1ad3765ef5
```

> 若目标机没装 `md5sum`（如部分精简镜像），用 `sha256sum` 比对：
> `sha256sum docker/xwops-images-v1.0.0.tar`
> 期望值：`b79d75e0b3e12c7364c725cd6edad26ba334b85271c472facaaa0c8c69230f61`

**3.3 加载镜像**

```bash
bash docker/load-images.sh
```

等价的手动命令：

```bash
docker load -i docker/xwops-images-v1.0.0.tar
```

**3.4 确认 5 个镜像都在**

```bash
docker images | grep -E 'xwops/|mysql:8.0|redis:6.2.6'
```

期望：

```
xwops/web      1.0.0
xwops/django   1.0.0
xwops/celery   1.0.0
mysql          8.0
redis          6.2.6-alpine
```

---

## 4. 第四步：改配置（★ 部署的核心动作）

只有 **2 个文件**需要改。

### 4.1 根目录 `.env`（compose 变量）

```bash
cp .env.example .env
vi .env
```

改这三个值（自己定，别用示例值）：

| 变量 | 含义 |
|---|---|
| `MYSQL_PASSWORD` | MySQL root 密码 |
| `REDIS_PASSWORD` | Redis 密码 |
| `ALERT_WEBHOOK_SECRET` | **告警 Webhook 接收密钥，≥32 字符**。Alertmanager 推告警时带的 Bearer 令牌，两边必须一致 |

`ALERT_WEBHOOK_SECRET` 生成一个：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# 或借镜像里的 Python：
docker run --rm --entrypoint python xwops/django:1.0.0 -c \
  "import secrets; print(secrets.token_urlsafe(32))"
```

> 🔴 **不配这个值，告警 Webhook 一律返回 503。**
> 也可以改由 `backend/conf/env.py` 的 `ALERT_WEBHOOK_SECRET` 提供（两者取其一，compose 环境变量优先）。

> ★ 同时记得改 **`docker_env/alertmanager/alertmanager.yml`** 里的
> `http_config.authorization.credentials`，填成同一个值，否则 Alertmanager 推过来会被 401。

### 4.2 后端 `backend/conf/env.py`（应用配置）

```bash
cp backend/conf/env.example.py backend/conf/env.py
vi backend/conf/env.py
```

逐项改：

| 配置项 | 改成什么 |
|---|---|
| `DATABASE_PASSWORD` | **必须**与 `.env` 的 `MYSQL_PASSWORD` 完全一致 |
| `REDIS_PASSWORD` | **必须**与 `.env` 的 `REDIS_PASSWORD` 完全一致 |
| `CREDENTIAL_ENCRYPTION_KEY` | 见下方生成命令，**必须自己生成** |
| `SECRET_KEY` | 见下方生成命令。**写在 `env.py` 里**（本版起优先取这里的值）；不写则退化为 `settings.py` 里的公开占位串 |
| `ALERT_WEBHOOK_SECRET` | 与 `.env` 里那个一致（二选一，见 4.1） |
| `DEBUG` | 保持 `False` |
| `DATABASE_HOST` | 保持 `dvadmin3-mysql`（容器名，不要改成 localhost） |
| `REDIS_HOST` | 保持 `dvadmin3-redis` |

**生成两个密钥**（借镜像里的 Python 执行，无需本机装环境）：

```bash
# 生成 CREDENTIAL_ENCRYPTION_KEY
docker run --rm xwops/django:1.0.0 python -c \
  "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 生成 SECRET_KEY
docker run --rm xwops/django:1.0.0 python -c \
  "import secrets; print('django-insecure-' + secrets.token_urlsafe(50))"
```

把输出分别填进 `env.py` 里的 `CREDENTIAL_ENCRYPTION_KEY` 与 `SECRET_KEY`。

> 🔴 **`CREDENTIAL_ENCRYPTION_KEY` 必须离线备份。**
> 堡垒机的 SSH 密码、Jenkins Token、告警渠道密钥、日志源 ES 密码都用它加密存储。
> **一旦更换，所有已保存的凭据全部无法解密**，表现为「凭据失效、连接被拒」。
>
> ⚠️ **`SECRET_KEY` 更换会让所有已签发的 JWT 立即失效**（用户需重新登录），
> 同时影响 WebSocket 的 token 解码（`consumers.py` 用同一个密钥）——两者同步失效，属预期。
> 它与 `CREDENTIAL_ENCRYPTION_KEY` 相互独立，更换不影响已保存的凭据。

> 💡 `backend/conf/env.py` 已被 `.gitignore` 排除，**不会**被提交，可以放心写真实密码。

### 4.3 准备数据目录

```bash
mkdir -p backend/media logs/log docker_env/mysql/data docker_env/redis/data
```

---

## 5. 第五步：启动容器

```bash
docker compose up -d
```

等 20 秒左右，确认 5 个容器都是 `Up`：

```bash
docker compose ps
```

期望 5 行，状态均为 `Up`（mysql 首次启动会初始化，可能多等 10-30 秒）。

> ⚠️ **本节最容易踩的坑：为什么 `backend/` 源码必须留着？**
>
> - `xwops/web` 镜像：前端已经编译进镜像，**不需要**源码。
> - `xwops/django`、`xwops/celery` 镜像：**只装了 Python 依赖，不含业务代码**。
>   代码是通过 `docker-compose.yml` 里的 `./backend:/backend` **挂载**进容器的。
>
> 所以：**删掉 `backend/` 目录，容器里的 `/backend` 就是空的，django 起不来。**
> 这是 DVAdmin 的既有设计，不是打包漏了。
>
> 好处是：以后改 Python 代码，`docker compose restart dvadmin3-django` 即生效，
> 不用重新构建镜像。

如果某台机器需要**从源码重新构建**镜像（例如你改了 `requirements.txt` 或 `web/` 下的前端代码）：

```bash
docker compose up -d --build
```

> ⚠️ **内网环境大概率会失败在这一步**：`docker_env/web/Dockerfile` 里有
> `RUN npm install --registry=https://registry.npmmirror.com`，`django/celery` 的 Dockerfile 同理要
> 访问 pip 源 —— **都需要外网**。
>
> 因此交付形态是「**在有外网的机器上构建 → 导出 tar → 内网 `docker load`**」，
> 而不是在内网就地构建。具体步骤见 **第 9 节「改前端代码」**。
>
> ★ 正常部署时**不要加 `--build`**：镜像已经从 tar 加载好了，
> `docker compose up -d` 会直接使用本地镜像；加 `--build` 反而会触发一次（很可能是失败的）构建。

---

## 6. 第六步：初始化数据库（**仅首次执行**）

四个动作，**顺序不能颠倒**。

### 6.1 建表

```bash
docker exec dvadmin3-django python manage.py migrate
```

看到一串 `Applying ... OK` 即为正常。

### 6.2 创建超级管理员与基础数据

```bash
docker exec dvadmin3-django python manage.py init -y
```

这一步会创建超管账号 `superadmin`。

### 6.3 导入平台配置数据（菜单 / 角色 / 权限 / 字典）

```bash
docker exec -i dvadmin3-mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" django-vue3-admin' \
  < init/01_seed_config.sql
```

> 该脚本自带 `DELETE FROM` 后再插入，可重复执行；末尾还会自动修复
> 超管部门引用，避免登录后页面报错。

**验证数据是否导入成功**：

```bash
docker exec dvadmin3-django python manage.py shell -c "
from dvadmin.system.models import Menu, Role
print('菜单数:', Menu.objects.count())
print('角色数:', Role.objects.count())
"
```

期望：**菜单 49 个、角色 7 个**。数量对不上说明 seed 没导进去。

> ★ 这里**不是 51**：种子数据里菜单 id 是 `1~19` + `22~51`（**源环境已删掉 id 20、21**），
> 所以实际条数是 **49**。别拿 id 最大值 51 去对数。
> 其余对照值：按钮 207、按钮授权 667、字典 49。

### 6.4 凭据加密迁移（**本版新增，必做**）

加固后，告警渠道 / 日志源的密钥以 **Fernet 密文**落库。如果你的库里已经有明文密钥
（或导入了包含明文密钥的数据），需要跑一次迁移把它们转成密文。

**先 dry-run 看会改什么**（默认就是 dry-run，不写库）：

```bash
docker exec dvadmin3-django python manage.py migrate_secrets
```

确认输出无误后再真正执行：

```bash
docker exec dvadmin3-django python manage.py migrate_secrets --apply
```

> - 该命令**幂等**：已是密文的行会跳过；整批在一个事务里，失败则全部回滚。
> - 它**不会打印任何密钥内容**，日志可以放心留存。
> - 若报「解密失败；请恢复原密钥」：说明库里已有用**另一个** `CREDENTIAL_ENCRYPTION_KEY`
>   加密的数据，请换回原密钥再跑，**不要**直接 `--apply` 覆盖。
>
> 💡 全新部署且未导入任何渠道数据时，这条命令会跑通但改 0 行，属正常。

---

## 7. 第七步：验证

### 7.1 容器层

```bash
docker compose ps                                   # 5 个 Up
docker logs --tail 30 dvadmin3-django               # 无 Traceback
docker logs --tail 30 dvadmin3-web                  # 无 error
```

### 7.2 接口层

> ⚠️ **注意地址里的双 `/api`**：前端请求是 `/api/api/xxx/`，
> nginx 收到后把第一个 `/api` 剥掉再转发给 Django。
> **打单层 `/api/` 会 404，这是设计如此，不是故障。**

```bash
# 后端是否起来（应为 200）
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/health/

# 经 nginx 访问（应为 200，返回 HTML）
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/

# 登录接口（应返回 code 2000 与 token；密码错误返回业务码而非 404）
curl -s -X POST http://127.0.0.1:8080/api/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"admin123456"}'
```

### 7.3 页面层

浏览器打开 **`http://<服务器IP>:8080`**，用下面的账号登录：

| 账号 | 密码 |
|---|---|
| `superadmin` | `admin123456` |

> 🔴 **登录后第一件事：立刻改掉这个密码。**
> `admin123456` 是上游 DVAdmin 的公开默认密码，全世界都知道。
> 改密路径：右上角头像 → 个人中心 → 修改密码。

登录后检查左侧菜单是否齐全（应有 CMDB、堡垒机、监控、日志、告警、发布、AI 运维助手等）。

### 7.4 安全体检（**本版新增，建议必跑**）

一条命令校验「配置 / 表字段 / 接口挂载 / 运行时依赖」是否都到位：

```bash
docker exec dvadmin3-django python manage.py security_preflight
```

通过时输出：

```
配置、表字段、接口挂载及运行时导入检查通过。
```

不通过会**逐条列出**问题并以非零码退出（可直接接进部署流水线）。它检查：

| 项 | 判定 |
|---|---|
| `DEBUG` | 必须为 `False`（写在 `backend/conf/env.py`） |
| `ALLOWED_HOSTS` | 禁止 `*`，必须列出**实际访问用的主机名/IP**，如 `["192.168.1.50", "127.0.0.1", "localhost"]`。★ 端口不用写（Django 会自动忽略端口）；★ `127.0.0.1` 必须在列表里，否则容器内的健康检查会被判 Host 非法 |
| 缓存 | 必须指向共享 Redis（票据与去重依赖它） |
| `ALERT_WEBHOOK_SECRET` | 长度必须 ≥ 32 |
| 凭据加密密钥 | 能完成一轮 `encrypt`/`decrypt` 自检 |
| 表与字段 | 6 个业务 app 的模型表/字段必须与库一致（漏迁移会在这里暴露） |
| 接口挂载 | 命令下发 / 录像 / 下发候选 / Grafana 数据源 / 告警 Webhook 五条路由必须能 resolve |
| 运行时依赖 | `asgi` 可加载，`celery` / `paramiko` / `cryptography` 可导入 |
| 告警模板 | 已启用的模板必须能被沙箱语法接受（不兼容的只给**提示**，不判失败） |

> 该命令**只读**，不修改任何业务数据，可随时重复执行。

---

## 8. 第八步：部署完成的判断标准

逐项打勾，全部满足才算部署成功：

- [ ] `docker compose ps` 五个容器全部 `Up`
- [ ] `http://<IP>:8080` 能打开登录页
- [ ] `superadmin` 能登录
- [ ] 左侧菜单 ≥ 51 项，且包含自研模块（CMDB / 堡垒机 / 监控 / 日志 / 告警 / 发布 / AI）
- [ ] 任意进入一个列表页（如「服务器管理」）不发红、不报 500
- [ ] 已修改超管默认密码
- [ ] 已备份 `CREDENTIAL_ENCRYPTION_KEY`

---

## 9. 日常运维

### 改前端代码

前端是 **`npm run build` 出的静态文件，被 `COPY` 进镜像**的（`/usr/share/nginx/html`），
所以改了 `web/` 下的源码，**必须重新构建 web 镜像**。

#### 先判断：这次改动到底要不要重建？

| 你改的东西 | 要重建吗 | 怎么生效 |
|---|---|---|
| `web/src/**`、`web/index.html`、`web/public/**`、`web/package.json` | **要** | 见下方步骤 |
| `docker_env/nginx/my.conf` | **不用** | `docker exec dvadmin3-web nginx -s reload` |
| `backend/**` 的 `.py` | **不用** | `docker compose restart dvadmin3-django` |
| `backend/requirements.txt` | **要** | django 与 celery **两个**镜像都要重建 |
| 根目录 `.env`、`backend/conf/env.py` | **不用** | `docker compose up -d`（重建容器即读到新值） |

> ★ **nginx 配置是 bind mount**，改完**不 reload 不生效** —— 这一点最容易漏。

#### 步骤 1 · 构建（在**有外网**的机器上）

```bash
cd <仓库根目录>

# 只重建 web 镜像（约 3~15 分钟，首次要下 node_modules）
docker build -f docker_env/web/Dockerfile -t xwops/web:1.0.0 .
```

构建成功后 **先验证产物**，别急着上线 —— 不用启动容器，直接把镜像里的静态文件抽出来看：

```bash
# 看 dist 是否真的生成了，以及 index.html 里该有的东西在不在
docker run --rm --entrypoint sh xwops/web:1.0.0 -c \
  'ls -la /usr/share/nginx/html && grep -o "<title>[^<]*</title>" /usr/share/nginx/html/index.html'
```

#### 步骤 2 · 让容器用上新镜像

```bash
docker compose up -d --no-build dvadmin3-web
```

> ★ **为什么要 `--no-build`**：compose 里 `image:` 与 `build:` 是**并存**的。
> 加 `--no-build` 表示「直接用我刚建好的 `xwops/web:1.0.0`，不要再触发一次构建」，
> 这样你确切知道容器跑的是哪一次构建的结果。
> （等价写法：`docker compose build dvadmin3-web && docker compose up -d dvadmin3-web`。）
> 若镜像不存在而你又加了 `--no-build`，compose 会直接报错 —— 这是**好事**，不会静默用旧镜像。

#### 步骤 3 · 回归验证

```bash
docker ps --filter name=dvadmin3-web --format '{{.Names}} {{.Status}}'
curl -s -o /dev/null -w 'HTTP=%{http_code}\n' http://127.0.0.1:8080/     # 期望 200
```

⚠️ **必须走 8080 复验**。前端只改了一个 `.vue` 也可能因为构建报错而产出空 `dist`，
届时 8080 会返回 404 或空白页 —— 只看「容器 Up」判断不出问题。

#### ★★ 内网机器**不能**就地构建

`docker_env/web/Dockerfile` 里有一行：

```dockerfile
RUN npm install --registry=https://registry.npmmirror.com --no-audit --no-fund --legacy-peer-deps
```

**必须有外网**。内网目标机上执行构建会在这一步失败（拉不到 npm 包）。

所以内网场景走「**外网构建 → 导出 tar → 拷进去 load**」：

```bash
# —— 有外网的机器（仓库根目录）——
# ★ 建议【沿用同一个 tag】覆盖，这样 docker-compose.yml 一个字都不用改。
docker build -f docker_env/web/Dockerfile -t xwops/web:1.0.0 .
bash docker/save-images.sh --web-only            # 产出 docker/xwops-web-1.0.0.tar + checksums.txt

# 把 docker/xwops-web-1.0.0.tar 与 checksums.txt 拷到内网目标机
```

```bash
# —— 内网目标机（仓库根目录）——
cd docker && md5sum -c checksums.txt && cd ..
docker load -i docker/xwops-web-1.0.0.tar         # 同 tag 直接覆盖旧镜像
docker compose up -d --no-build dvadmin3-web
```

> ★ **为什么建议沿用同一个 tag**：compose 里写的是 `image: xwops/web:1.0.0`，
> 覆盖同一 tag 后 `docker-compose.yml` 完全不用动，少一个出错点。
>
> 如果你确实要换 tag（例如 `xwops/web:1.1.0`），**必须同步改 `docker-compose.yml` 的
> `image:` 行**，否则 compose 仍会去找 `1.0.0` 那个旧镜像 —— 表现是「明明 load 了新镜像，
> 页面还是老的」。
>
> 注意：覆盖 tag 只影响**之后新建**的容器；正在跑的容器引用的是镜像 ID，不会被换掉。

#### 产物核验清单（建议固化进流程）

构建完成后**不要立刻上线**，先对镜像产物做一次扫描。以下几条是我们发版时实际跑过的，
能挡住「外链图片在内网裂图」「把内部邮箱/密钥编进前端」这类问题：

```bash
docker run --rm --entrypoint sh xwops/web:1.0.0 -c '
cd /usr/share/nginx/html
echo "— 关键元素 —"
grep -o "<title>[^<]*</title>" index.html
echo "— 外部图片链接（应全 0）—"
grep -r -o -E "https?://[A-Za-z0-9.-]+" . | grep -E "baidu|csdnimg|alicdn|qiniu|cloudfront|unsplash|gravatar" | wc -l
echo "— 邮箱样式串（应全 0，防止把内部邮箱编进前端）—"
grep -r -o -E "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" . | sort -u
echo "— 内网地址 / 默认口令（应全 0）—"
grep -r -o -E "localhost:8000|admin123456|9ba8fc80" . | sort -u | wc -l
'
```

> 注意这里用的是**正则匹配模式**（「任意邮箱」「任意图片 CDN 域名」），
> 而不是把具体的敏感串写进命令里 —— 否则文档本身就变成了泄露渠道。

> 更完整的一版见仓库 `.work/` 下的核验脚本；核心思想是
> **对「编译产物」而不是「源码」做断言** —— 只有产物才是真正会跑在用户浏览器里的东西。

#### 关于构建的可复现性（建议做一次）

`web/` 目录里**没有 `package-lock.json`**，Dockerfile 用的是 `npm install`，
所以**每次构建解析到的依赖版本可能不同**（上游发布新版本就会漂移）。

建议在有外网的机器上固定一次：

```bash
cd web && npm install --legacy-peer-deps && cd ..   # 生成 package-lock.json
git add web/package-lock.json && git commit -m "chore(web): 固定前端依赖版本"
```

之后可以把 Dockerfile 改成两段式（依赖层可被缓存，改业务代码时不再重装依赖）：

```dockerfile
COPY web/package.json web/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com --no-audit --no-fund --legacy-peer-deps
COPY web/ ./
RUN npm run build
```

> ★ `npm ci` **要求存在 lockfile**，没有 `package-lock.json` 时会直接失败 —— 所以先做上一步。

### 改后端代码

后端是**挂载**的（`./backend:/backend`），改完重启即可：

```bash
docker compose restart dvadmin3-django
```

> ★ Django 用 `uvicorn` 启动且**没有 `--reload`**，所以改 `.py` **必须重启**，不会自动生效。
> ★ 改的是 Celery 任务（`*/tasks.py`）时，重启 `dvadmin3-celery` 而不是 django。

### 改后端依赖（requirements.txt）

`requirements.txt` 是**打进镜像**的，改了必须重建 **django 与 celery 两个**镜像
（两者共用同依赖层，但各自有独立 tag）：

```bash
docker build -f docker_env/django/Dockerfile -t xwops/django:1.0.0 .
docker build -f docker_env/celery/Dockerfile -t xwops/celery:1.0.0 .
docker compose up -d --no-build dvadmin3-django dvadmin3-celery
```

> ★ 这是踩过的坑：只重建 django 忘了 celery，会出现「接口能跑、异步任务报 `ModuleNotFoundError`」。
> ★ 改完依赖后**两个镜像的 tag 都要带上**再 `docker save`，否则目标机 load 出来的 celery 还是旧的。

### 把改动送到目标机（打包镜像）

`docker/` 下有两个对称脚本：

```bash
bash docker/save-images.sh                    # 全量 5 个镜像 -> xwops-images-v<tag>.tar
bash docker/save-images.sh 1.1.0              # 指定 tag
bash docker/save-images.sh 1.1.0 --web-only   # 只打前端（改了前端最常用，包小很多）
```

脚本会：确认镜像存在且**带 tag**（避免把 `<none>` 匿名镜像一起导出）→ 检查磁盘 →
`docker save` → 生成 `checksums.txt`（md5）与 SHA256。

目标机上：

```bash
bash docker/load-images.sh docker/xwops-images-v1.1.0.tar
```

> ★ `docker save` 产出的是分层 tar，**远小于** `docker images` 显示的 SIZE
> （后者是解压后占用）。5 个镜像解压后约 3.2 GB，v1.0.0 的 tar 只有 490 MB。
> 所以**别对已压缩的 tar 再 gzip**，也别按 `docker images` 的 SIZE 去预估传输体积。

### 查看日志

```bash
docker logs -f dvadmin3-django      # 后端
docker logs -f dvadmin3-web         # nginx
docker logs -f dvadmin3-celery      # 异步任务
```

### 备份数据库

```bash
docker exec dvadmin3-mysql sh -c \
  'mysqldump -h127.0.0.1 --protocol=TCP -uroot -p"$MYSQL_ROOT_PASSWORD" \
   --single-transaction --routines --triggers django-vue3-admin' \
  > backup_$(date +%F).sql
```

> 备份文件里含全部业务数据与**已加密的凭据**，注意保管。
> 恢复时必须使用**同一个** `CREDENTIAL_ENCRYPTION_KEY`，否则凭据解不开。

### 停 / 起 / 重启

```bash
docker compose stop        # 停止（保留数据）
docker compose start       # 启动
docker compose restart     # 重启
docker compose down        # 删除容器（数据仍在 docker_env/ 下）
```

---

## 10. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 访问 8080 报 **502** | django 没起来，或 nginx 配置里的 proxy IP 与 compose 静态 IP 不一致 | `docker logs dvadmin3-django` 看报错；核对 `docker_env/nginx/my.conf` 的 `proxy_pass` 与 `docker-compose.yml` 中 django 的 `ipv4_address` 是否同为 `172.31.0.12` |
| 访问 `/api/xxx` 直接 **404** | 用了单层 `/api` | 改成**双层** `/api/api/xxx` |
| 后端容器 **起不来 / 立刻退出** | `backend/conf/env.py` 不存在或格式错 | 确认 `cp backend/conf/env.example.py backend/conf/env.py` 已执行；`docker logs dvadmin3-django` 看 ImportError |
| 后端报 **Can't connect to MySQL** | `.env` 与 `conf/env.py` 的密码不一致 | 两处密码必须完全相同 |
| 登录后部分页面 **500** | 数据未初始化，或超管部门引用悬空 | 确认第 6.3 步已执行（该 SQL 末尾自带部门修复） |
| `md5sum -c` 报 **FAILED** | 镜像包下载不完整 | 重新下载，别用传输中断的文件 |
| `docker load` 报 **no space left** | 磁盘不足 | 至少留 5 GB |

**改动 nginx 配置后必须重载才生效**：

```bash
docker exec dvadmin3-web nginx -s reload
```

---

## 附录 A. 脱敏占位符清单（**部署时按需替换**）

本仓库代码已脱敏，以下占位值**不代表你的真实环境**，请按实际情况替换：

| 占位值 | 出现位置 | 说明 |
|---|---|---|
| `203.0.113.10` | 文档 / 配置注释 | 原公网 IP → 换成你的服务器地址 |
| `192.0.2.x` | `backend/dvadmin/alert/rules/devops_rules.yml` | 原内网 IP → 换成你的被监控机 IP，否则告警规则匹配不到目标 |
| `172.31.0.x` | `docker-compose.yml` / `docker_env/nginx/my.conf` | 容器内网 IP，**多数情况无需改**；仅当与办公网段冲突时，两处一起改 |
| `ops@example.com` | `web/src/views/alert/channel/crud.tsx` | 邮件通知渠道的占位提示文案 |
| `myapp` | 日志采集相关页面与注释 | 原业务标识 → 换成你自己的应用名 |
| `CHANGE_ME_*` | `backend/conf/env.py` / `.env` | **必须**改成真实值 |

> `docker_env/prometheus/prometheus.yml` 与 `docker_env/alertmanager/alertmanager.yml`
> 里的 IP 同样是占位值。这两个文件属于**可选组件**，不在 `docker-compose.yml` 内。

## 附录 B. 可选组件：监控栈

`docker_env/prometheus/` 与 `docker_env/alertmanager/` 下是平台的监控与告警配置，
**不包含在 `docker-compose.yml` 内**，仅在需要独立部署 Prometheus + Alertmanager 时使用：

1. 按你的实际环境修改两份 `yml` 里的 IP（全部是占位值）；
2. `alertmanager.yml` 的 webhook 需指向 `http://172.31.0.12:8000/api/alert/webhook/receiver/`；
3. 若企业内网已有 Prometheus，建议直接复用，**不要重复部署**，避免告警双发。

## 附录 C. 目录职责速查

| 目录 | 职责 | 能否删 |
|---|---|---|
| `backend/` | 后端源码 | ❌ **不能**（容器靠它挂载运行） |
| `web/` | 前端源码 | ⚠️ 仅当永远不从源码构建时可删 |
| `docker_env/` | nginx / mysql / redis 配置 | ❌ 不能（compose 引用） |
| `init/` | 初始化 SQL | ⚠️ 仅首次部署用，部署完可留档 |
| `docker/` | 镜像加载脚本与校验值 | ⚠️ 部署完可留档 |
| `logs/` | 日志挂载点 | ❌ 不能 |
