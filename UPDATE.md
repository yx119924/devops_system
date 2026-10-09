# XwOps · 已上线环境增量更新手册

> **这份文档解决什么问题**：环境**已经跑起来**之后，要打一次「只改代码、不动数据」的更新 ——
> 怎么一步步做完、怎么确认没做坏、出问题怎么退。
>
> **从零部署请走** [`DEPLOY.md`](DEPLOY.md)（那是「装机」；本文是「换件」）。

**本批标识**（下文所有「本批」都指它）

| 项 | 值 |
|---|---|
| 版本 | **v1.1.0**（Release 附件 `xwops-images-v1.1.0.tar`） |
| 功能基线提交 | **`d11565d`**（历史：v1.0.0 的功能基线是 `4b0a80e`） |
| 内容 | **新增「可视化发布流水线」** —— 新 app `dvadmin/release/`（4 张表 / 6 种节点 / 状态机）+ 前端编排与运行面板 + 菜单/按钮注册脚本；<br>修**日志检索**「一选时间范围就 400」（时间戳空格 → `T` 归一化）+ 前端显式超时 + ES 往返计时埋点；<br>修 **DRF 校验错误的中文提示被吃成乱码**（字符串值被当列表逐字符遍历） |
| 日期 | 2026-10-09 |
| 影响面 | **18 个后端文件**（含 **2 个新迁移**）+ **11 个前端文件** ⇒ **前端必须重建镜像**；<br>另需**跑一次菜单/按钮注册脚本**（§3 第 3 步③），否则新菜单不出现或按钮全没 |

> ★ **换一批改动也能用这份文档**。通用步骤（§1 / §3 / §4 / §6 / §7）长期有效；
> 只有「本批专属」的部分需要替换 —— **怎么替换见 §2.2**。

**怎么读这份文档**

| 你现在想干什么 | 看哪节 |
|---|---|
| 第一次打更新、要照着做 | **§1 → §2 → §3 → §4** |
| 想先搞懂原理再动手 | §0（5 分钟心智模型） |
| 做到一半卡住了 | **§6**（按现象查） |
| 想确认某个现象是不是 bug | §5 |
| 要回滚 | §7 |
| 想知道「为什么这么设计」 | §8 / §9 |

**占位符约定**（本文不写真实值，按你环境替换）

| 占位符 | 含义 | 示例 |
|---|---|---|
| `<部署目录>` | 目标机上仓库的位置 | `~/xwops` |
| `<仓库根目录>` | 在有外网的机器上 clone 出来的仓库 | `/tmp/xwops_src` |
| `<内网IP>` | 目标机的内网地址 | `192.0.2.163` |
| `<Prom规则目录>` | Prometheus `rule_files` 指向的目录 | `/opt/prometheus/rules`（Prom **主机部署**时是宿主机路径） |
| `<AM配置目录>` | Alertmanager 配置所在目录 | `/opt/alertmanager` |

---

## 0. 5 分钟心智模型（先看懂这个，后面就不用死记）

### 0.1 目标机上跑着什么

5 个容器。**关键是"代码怎么进入容器"不一样** —— 这直接决定了「改完要不要重建镜像」：

| 容器 | 作用 | 代码怎么进去 | 改了要重建镜像吗 |
|---|---|---|---|
| `dvadmin3-web` | nginx：前端静态文件 + 反向代理 | **编译进镜像**（`/usr/share/nginx/html`） | **要** |
| `dvadmin3-django` | 后端 API（uvicorn，**没开 `--reload`**） | 挂载 `./backend:/backend` | 不用，**重启**即可 |
| `dvadmin3-celery` | 异步任务（webhook 落库、通知分发） | 同上挂载 | 不用，**重启**即可 |
| `dvadmin3-mysql` | 数据库（数据落在 `docker_env/mysql/data/`） | —— | —— |
| `dvadmin3-redis` | 缓存 / 队列 | —— | —— |

> ★ 后端**没开 `--reload`** ⇒ 改了 `.py` **必须重启容器**，否则跑的还是旧代码。
> ★ 前端**编译进镜像** ⇒ 只更新源码**页面不会变**。这是本手册最容易漏的一步。

### 0.2 一次更新总共只会动三样东西

1. **代码文件** —— 挂载的（`backend/`）拷进去就行；编译进镜像的（`web/`）**必须重建镜像**
2. **镜像** —— ★ **不会跟着代码自己更新**。只 `git pull`，页面永远是旧的
3. **数据库结构** —— 有新的 `migrations/` 文件时，加一步 `migrate`

### 0.3 「改什么 → 做什么」速查（最重要的一张表）

| 你改了 | 要重建镜像吗 | 生效方式 |
|---|---|---|
| `backend/**` 的 `.py` | **不用** | 重启 django + celery（§3 第 7 步） |
| `backend/**/migrations/**` | 不用 | 多一步 `manage.py migrate`（§3 第 3 步） |
| `backend/requirements.txt` | **要**：django **和** celery **两个镜像** | 重建 → `save` → 搬 → `load` → `up -d --no-build` |
| `web/**` | **要**：web 一个镜像 | §3 第 4 步（探测 → 就地构建 / 外网机搬运） |
| `docker_env/nginx/my.conf` | 不用 | `docker exec dvadmin3-web nginx -s reload` ★ **不 reload 不生效** |
| `docker-compose.yml`、`.env`、`backend/conf/env.py` | 不用 | `docker compose up -d --no-build`（**重建容器**才读到新值） |
| `docker_env/alertmanager/alertmanager.yml` | 不用 | 它是**样例**；线上 AM 要手工改 + `POST /-/reload`（§3 第 6 步） |
| `*.md`、`.gitignore` | 不用 | 无动作 |

### 0.4 全流程一条线

```
① 备份数据库          §3 第 0 步     ← 唯一的安全网，不能跳
② 把新代码弄到目标机   §3 第 1 步     ← 三条通道选一条
③ 后端源码就位         §3 第 2 步     ← 通道 A 的话自动完成
④ 数据库迁移           §3 第 3 步     ← 有迁移文件时才做
⑤ 重建前端镜像         §3 第 4 步     ← 改了 web/ 时必须
⑥ 配规则投递挂载       §3 第 5 步     ← 本批专属
⑦ Alertmanager 手工改  §3 第 6 步     ← 本批专属
⑧ 重启 + 自检          §3 第 7 步
⑨ 逐项验收             §4
     任何一步不对 → §6 按现象查；想退 → §7
```

---

## 1. 开始之前

### 1.1 前置条件（逐条都能验证）

```bash
# ① 确保你站在仓库根目录（能看到 docker-compose.yml）
pwd && ls -d docker-compose.yml

# ② 确认 compose 是 v2（命令是 `docker compose`，中间有空格）
docker compose version

# ③ 确认 5 个容器都在跑
docker compose ps

# ④ 磁盘至少留 3 GB（重建/加载镜像要用）
df -h . | tail -1
```

> ★ **关于 v1 / v2**：本文所有命令都用 **v2 写法 `docker compose`**（带空格）。
> 若你的机器只有老版 `docker-compose`（**带横线**），就把全文的 `docker compose` 换成 `docker-compose`；
> ★ **但不要混用** —— 两者读配置的行为有差异。有条件就升到 v2。

### 1.2 三条探测：决定走哪条通道

更新只有两件麻烦事 —— **代码怎么进目标机**、**前端镜像怎么进目标机**。先跑 3 条命令定方向：

```bash
# ① 目标机能不能直连 GitHub？（在【目标机】上执行）
git -C <部署目录> ls-remote origin HEAD        # 通 → 通道 A；报 GnuTLS/timed out → 通道 B/C

# ② 有没有一台「能上外网 + 装了 docker」的机器？
docker version                                  # ★ 换到那台机器上执行；没有就是没有

# ③ 本批有没有改 web/ ？（决定前端要不要重建；先 fetch 再比，不需要先知道新提交号）
git -C <部署目录> fetch origin && git -C <部署目录> diff --name-only HEAD origin/main -- web/
#   有输出 ⇒ 前端必须重建（§3 第 4 步）；无输出 ⇒ 前端不用动
```

决策表：

| 情况 | 走哪条通道 | 前端怎么办 |
|---|---|---|
| ①通 | **通道 A**（`git pull`） | **§3 第 4 步**：先探测，能就地构建走 ②A，否则走 ②B |
| ①不通，有外网机 | **通道 B**（离线包 + scp） | 同上；外网机顺手把镜像也构建了（②B） |
| ①不通，没外网 docker 机 | 通道 B + 应急 | **§8.3**（只换 `dist`，不重建镜像） |
| 想长期省事 | **通道 C**（给目标机配 SSH key） | —— |

> ★ **本批改动了 4 个 `web/src/**` 文件 ⇒ 前端必须重建**，这一步绕不过去。
> ★ **镜像不会"跟着代码自己更新"** —— 只 `git pull` 的话，页面永远是旧的。
> 这是最容易漏的一步，所以 §3 第 4 步把它做成了**自包含的三段**（探测 → 构建 → 核验）。

---

## 2. 这次要更新什么

### 2.1 本批文件清单（**v1.1.0 / 2026-10-09** —— 31 个文件 = 29 代码 + 2 文档）

| 类别 | 文件 | 需要的动作 |
|---|---|---|
| **后端源码·新增模块** | `backend/dvadmin/release/`（10 个文件：`__init__.py`、`apps.py`、`models.py`、`engine.py`、`ssh_sftp.py`、`urls.py`、`views/__init__.py`、`views/pipeline.py`、`migrations/__init__.py`、`migrations/0001_initial.py`）<br>`backend/register_release.py`（菜单/按钮注册脚本）<br>`backend/verify_release.py`（离线门禁） | 拷进 `<部署目录>/backend/` → **跑迁移** → **跑一次注册脚本**（§3 第 3 步③）→ 重启 django + celery |
| **后端源码·改动** | `backend/application/settings.py`（注册新 app）<br>`backend/application/urls.py`（挂 `/api/release/`）<br>`backend/dvadmin/bastion/models.py`（`CommandLog.source` 加 `release` 取值）<br>`backend/dvadmin/bastion/migrations/0005_alter_commandlog_source.py`<br>`backend/dvadmin/log/views/source.py`（时间戳归一化 + ES 计时埋点）<br>`backend/dvadmin/utils/exception.py`（DRF 错误详情解析） | 同上（`bastion` **也要跑迁移**） |
| **前端源码** | `web/src/views/release/`（10 个文件：`pipeline/` 6 个 + `run/` 4 个）<br>`web/src/views/log/search/api.ts`（显式 `timeout`） | **必须重建 web 镜像**（§3 第 4 步） |
| **工程杂项** | `CHANGELOG.md`、`UPDATE.md`（**本文档**） | 无动作（随仓库一起更新即可） |

> ★ 本批**没有**改 `requirements.txt` ⇒ **django / celery 镜像不用重建**，只重启容器即可。
> ★ 本批**改了 `web/`** ⇒ **web 镜像必须重建** —— 这是 v1.1.0 相对 v1.0.0 **唯一**的镜像变化。
> ★ 本批有 **2 个 app 要迁移**（`release` 建 4 张表、`bastion` 给 `CommandLog.source` 加取值）
> ⇒ §3 第 3 步要跑**两次** `migrate`。
> ★ 本批**新增 2 个菜单**（发布管理 → 流水线编排 / 执行记录）+ 16 个按钮，
> 要跑 §3 第 3 步③ 的注册脚本才看得见。

> 📎 **上一批（09-29）的文件清单，保留备查** —— 若你的环境**还没做过那一次升级**，这批文件同样要拷：
> 后端 `backend/dvadmin/alert/{models,services,views/rule}.py`、
> `backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py`、
> `backend/dvadmin/utils/import_export.py`、`backend/dvadmin/utils/import_export_mixin.py`；
> 前端 `web/src/views/alert/rule/{crud.tsx,index.vue}`、`web/src/views/alert/manage/index.vue`、
> `web/src/views/system/home/index.vue`、`web/src/components/importExcel/index.vue`；
> 参考配置 `docker_env/alertmanager/alertmanager.yml`、`backend/conf/env.example.py`
> （两者都是**样例与说明**，不动线上）；运行时产物
> `backend/dvadmin/alert/rules/devops_rules.yml`（**仅**移出版本控制，磁盘文件保持原样）。

### 2.2 换一批改动怎么套这份文档

（本节是为「下次更新」准备的 —— 不用重新读全文，照下面两步就能把本文的问题定位到具体动作。）

**第一步：看清这次到底变了哪些文件**

```bash
# 在任意一台能访问 GitHub 的机器上
git -C <仓库根目录> fetch origin
git -C <仓库根目录> diff --name-status HEAD..origin/main | sort
```

**第二步：按下面这张表把文件归类，得到你要做的动作**

| diff 里出现的路径 | 归类 | 你要做的事 |
|---|---|---|
| `backend/**` 的 `.py`（非 `migrations/`） | 后端源码 | 拷进去 + 重启（§3 第 2 步 + §3 第 7 步） |
| `backend/**/migrations/*.py` | 数据库迁移 | 多一步 `migrate <app>`（§3 第 3 步） |
| `backend/requirements.txt` | 依赖 | ★ django **和** celery **两个**镜像都要重建 |
| `web/**` | 前端 | 重建 web 镜像（§3 第 4 步） |
| `docker_env/nginx/my.conf` | nginx | `docker exec dvadmin3-web nginx -s reload`（★ 不 reload 不生效） |
| `docker-compose.yml`、`.env`、`backend/conf/env.py` | 配置 | `docker compose up -d --no-build`（重建容器才读到新值） |
| `*.md`、`.gitignore`、`docker/**` | 文档/工具 | 无动作 |

**第三步：把本文里「本批专属」的部分替换掉** —— 只有这 4 处：

| 位置 | 本批（v1.1.0 / 2026-10-09）的内容 | 换一批时 |
|---|---|---|
| §3 第 3 步 | 两个 app：`release`（`0001_initial`）+ `bastion`（`0005_*`）；外加菜单注册脚本 | 换成你这次的 app 名与迁移文件（`ls backend/dvadmin/*/migrations/`） |
| §3 第 5 步 | 规则投递挂载 —— **本批已标注「跳过」** | 只有改了告警规则下发相关的代码才需要 |
| §3 第 6 步 | Alertmanager `team` 标签 —— **本批已标注「跳过」** | 同上 |
| §4.2 | 功能验收项 1~8（v1.1.0） | 换成你这批改动的验收点 |

> ★ 判断"哪批改动算功能基线"的办法：**看哪个提交动了 `backend/` 或 `web/`**。
> 之后的纯 `*.md` 提交不影响功能，不用管 —— 所以本文只认功能基线 hash，不认"最新提交"。

---

## 3. 执行步骤（照着敲）

> 每步格式统一：**做什么 → 敲什么 → 做完应该看到什么**。
> 出错不要硬往下走 —— 先看 §6。

### 第 0 步 · 备份数据库（唯一的安全网，不能跳）

```bash
cd <部署目录>
docker exec dvadmin3-mysql sh -c \
  'mysqldump -h127.0.0.1 --protocol=TCP -uroot -p"$MYSQL_ROOT_PASSWORD" \
   --single-transaction --routines --triggers django-vue3-admin' \
  > backup_$(date +%F_%H%M).sql
ls -l backup_*.sql
```

**应该看到**：一个非 0 字节的 `backup_<日期时间>.sql`。

> ★ 备份文件里含全部业务数据与**已加密的凭据**，注意保管。
> ★ 恢复时必须用**同一个** `CREDENTIAL_ENCRYPTION_KEY`，否则凭据解不开。

### 第 1 步 · 取代码

按 §1.2 的探测结果**选一条**，命令直接贴下面。

**【通道 A】目标机能直连 GitHub**

先用一条命令分清是哪种情况：

```bash
cd <部署目录>
git status --short                      # 空 = 本地干净；有输出 = 有本地改动
```

**情况 1 · 本地干净** ⇒ 直接前进：

```bash
git pull --ff-only origin main
```

**情况 2 · 本地有改动，但你确认都不要了**（内网最常见：现场调过的参数、手改过的文件）
⇒ 丢弃本地改动、对齐远端：

```bash
cd <部署目录>

# ① 先看清改了什么（★ 被跟踪的文件才会丢；gitignore 的不会 —— 对照下方表）
git diff --stat

# ② 保险动作，一行，成本极低：把本地改动导出成 patch，万一有意外还能捞回来
git diff > /tmp/xwops_local_$(date +%F_%H%M).patch

# ③ 取回远端最新，然后丢弃本地改动、对齐远端（★ 不是 merge，也不是 rebase）
git fetch origin
git reset --hard origin/main
```

> 想知道**为什么会分叉**（普通分叉 / 远端历史被重写），§9.2 有一条分辨命令。

> ⚠️ 只看 `git pull` 的报错还不够：报 `fatal: Not possible to fast-forward` ⇒ **先按 §9.2 那条命令分辨原因，
> 不要照 git 提示做 merge / rebase** —— 远端被强推过时，那样会把已有修复**退回去**。

**`reset --hard` 对三类文件的差别** —— 「内网改过的文件不用管」到底指什么：

| 你改过的文件 | reset 之后 |
|---|---|
| **被 gitignore 的**：`backend/conf/env.py`、`.env`、`docker_env/*/data/`（**数据库在这儿**）、`backend/media/`、`logs/`、`docker-compose.override.yml` | **原样保留，一个字都不动** |
| 被跟踪、**且本批也改了**（见 §2.1 清单） | 变成**官方新版** ← 这正是你想要的 |
| 被跟踪、**但本批没动** | **退回 09-28 的原始内容** ⇒ 你的改动被丢弃 ← **只有这一类会真的丢** |

> ★★ **这个文件必须先备份**：`backend/dvadmin/alert/rules/devops_rules.yml` ——
> 旧历史里它被跟踪、新历史里已移出版本控制 ⇒ `reset --hard` 会**连文件带内容一起删**。
>
> ⚠️ **不要默认它是"平台生成的运行时产物"**。若里面是**人工维护的规则**（内网常见：
> PostgreSQL / Kafka / 中间件那一整套），删掉就是**真丢** —— 因为 `generate_rules()`
> 只会写回「数据库里 `source='platform'` 的那部分」，**内容与原来不一样**，覆盖 ≠ 恢复。
>
> ⇒ reset 之前先留底，一行：
> `cp backend/dvadmin/alert/rules/devops_rules.yml ~/devops_rules.yml.bak_$(date +%F_%H%M)`
> 真的丢了也别慌：这份文件在**旧提交**里，可从 git 历史取回（见 §6 故障表最后一行）。

> ⚠️ **这三个是现场最可能被改过、丢了会疼的被跟踪文件**，reset 前扫一眼
> `git diff --stat` 里有没有它们：`docker-compose.yml`（静态 IP / 端口 / 挂载）、
> `docker_env/nginx/my.conf`（`proxy_pass` 的容器 IP —— **改错会整站 502**）、
> `init/01_seed_config.sql`。

> 🚫 **高危，千万别做**：`git clean -xfd`（或任何带 **`-x`** 的 clean）会把
> **gitignore 的文件一起删掉** ⇒ `conf/env.py`、`.env`、**数据库目录**全没。
> 未跟踪文件本来就不会被 `reset --hard` 影响，**完全不需要 clean**。

**【通道 B】目标机不能上网（离线补丁包）** —— 用 §1.2 第 ① 条探测确认走不通时才是这条

```bash
# ── ① 在一台能访问 GitHub 的机器上打补丁包 ──
git clone --depth 1 https://github.com/yx119924/devops_system.git /tmp/xwops_src
cd /tmp/xwops_src && git format-patch -1 HEAD -o /tmp/xwops_patch
tar czf xwops_update_20260929.tar.gz -C /tmp/xwops_patch .
# 把 xwops_update_20260929.tar.gz 拷到目标机（scp / U 盘 / 跳板机都行）
```

```bash
# ── ② 在目标机上应用 ──
cd <部署目录>
tar xzf /tmp/xwops_update_20260929.tar.gz -C /tmp/xwops_update/
git apply --check /tmp/xwops_update/0001-*.patch && echo "可以干净应用"   # 先干跑
git diff > /tmp/xwops_before_backup.patch        # 应用前留一份现状，便于回退
git apply /tmp/xwops_update/0001-*.patch
```

> ★ **本地改动不要了、而 `--check` 报冲突**时：`git checkout -- .` 只丢弃**被跟踪文件**的
> 改动（gitignore 的一律不碰），清干净再重新 `git apply`。
> 注意它和 `reset --hard` 的差别：`checkout -- .` **只回退被跟踪文件的内容**、不动 HEAD。

**【通道 C】配一条能用的拉取通道** —— 命令见 §9.4（SSH over 443 / 代理 / jsDelivr 单文件）。

**取完必须核对，两项都对上才能进第 2 步**

```bash
# ① 功能基线提交到位了吗
#   ★ 只认 d11565d 这一个 hash（v1.1.0 的功能基线）—— 别写成「最新提交」，
#     因为本批之后还会陆续有「纯文档提交」，那样写每提交一次文档就过期一次。
#     历史：v1.0.0 的功能基线是 4b0a80e。
git merge-base --is-ancestor d11565d HEAD && echo "功能基线已到位"
git log --oneline --grep="中文提示被吃成乱码" -1
# 期望：d11565d fix(utils): DRF 校验错误的中文提示被吃成乱码 —— 字符串值不该当列表遍历
```

```bash
# ② 15 个关键文件的 md5（补丁漏拷/漏改会在这里暴露）
md5sum backend/application/settings.py \
       backend/application/urls.py \
       backend/dvadmin/bastion/models.py \
       backend/dvadmin/bastion/migrations/0005_alter_commandlog_source.py \
       backend/dvadmin/log/views/source.py \
       backend/dvadmin/release/models.py \
       backend/dvadmin/release/engine.py \
       backend/dvadmin/release/views/pipeline.py \
       backend/dvadmin/release/ssh_sftp.py \
       backend/dvadmin/release/urls.py \
       backend/dvadmin/release/migrations/0001_initial.py \
       backend/dvadmin/utils/exception.py \
       backend/register_release.py \
       backend/verify_release.py \
       web/src/views/log/search/api.ts
```

期望输出（前 14 个是后端，最后 1 个是前端）：

```
b0f12cd4b8fb3c75fdbb4c317dfa6c92  backend/application/settings.py
05a12e488031693a112acd1b7e655b08  backend/application/urls.py
bd480d6549ed54174401578e5360ff9f  backend/dvadmin/bastion/models.py
122eb02a8444c19fd0cd18fe5f9d02e4  backend/dvadmin/bastion/migrations/0005_alter_commandlog_source.py
d997dbbe7420c0649f9cd76100b41b4f  backend/dvadmin/log/views/source.py
d594fd542a7e2526b8256d01c089f510  backend/dvadmin/release/models.py
bb3e7ada4332ba41eaa514fb62c4c5ef  backend/dvadmin/release/engine.py
506f119b96d1be1ecee619a06121f780  backend/dvadmin/release/views/pipeline.py
d6df1440458067dc1f3586eda4b34f46  backend/dvadmin/release/ssh_sftp.py
77bbb346674389f4d9b5ebca0e846455  backend/dvadmin/release/urls.py
2c03e6bd7d9d3fb87a78dd0513699f4d  backend/dvadmin/release/migrations/0001_initial.py
9c9edb47a3b02b28c9d32f13f75adbdf  backend/dvadmin/utils/exception.py
20c0e82e14c0deee82b30741856f47b7  backend/register_release.py
a638f4b370c528c7cb59a9a4bea26ac5  backend/verify_release.py
63f5c558febecc90222929be847d2b1b  web/src/views/log/search/api.ts
```

**应该看到**：15 行 md5 与上面完全一致。

> ★ `md5sum` 默认输出是 `<md5>␠␠<文件>`（两个空格）；若你的输出带 `*` 前缀
> （如 `758188…  *models.py`），那是 binary 模式标记，比对时忽略即可。
>
> ★ **上面这 11 个值都是「LF 行尾」下的值** —— 仓库 `.gitattributes` 已统一 `eol=lf`，目标机检出即 LF。
> 若你在 **Windows** 上核对、且恰好只有个别文件对不上，先查行尾：
> `file <该文件>` —— 报 `CRLF` 就是历史遗留的行尾，`rm <该文件> && git checkout -- <该文件>`
> 让它按 `.gitattributes` 重新检出即可，**别去改文档**。
>
> ★ **只认 `d11565d` 这一个 hash（v1.1.0 的功能基线）—— 所有影响运行时的改动都在它里面。**
> 它之后可能还有若干个**纯文档提交**（只动 `*.md`、`*.gitignore`），**不影响功能**。所以：
> - `merge-base` 返回 0（该提交是 HEAD 的祖先）⇒ 功能代码已到位；
> - 通道 B 打补丁时**要打到 `d11565d`** —— 本批的功能改动分布在 3 个提交里：
>   `2d30bc8`（日志检索修复）→ `fe08591`（可视化流水线）→ `d11565d`（DRF 错误解析）。
>   只打到 `2d30bc8` 会缺掉整条发布流水线，只到 `fe08591` 会缺 DRF 错误提示修复；
> - **md5 对不上 ⇒ 代码没到位，别往下走。**
> - 历史：v1.0.0 的功能基线是 `4b0a80e`（其祖先含 `1d8db6b`、`2eeea68`、`5bfc62d`）。

### 第 2 步 · 后端源码就位（`.py` 是挂载的，拷进去即生效）

走通道 A（`git pull`）的话本步**已经完成**，跳到第 3 步。走通道 B 手工拷的话：

```bash
cd <部署目录>
# 只覆盖这几个文件，别整目录覆盖（目标机上可能有本地改动）
cp -v <补丁包>/backend/dvadmin/alert/models.py            backend/dvadmin/alert/
cp -v <补丁包>/backend/dvadmin/alert/services.py          backend/dvadmin/alert/
cp -v <补丁包>/backend/dvadmin/alert/views/rule.py        backend/dvadmin/alert/views/
cp -v <补丁包>/backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py \
      backend/dvadmin/alert/migrations/
cp -v <补丁包>/backend/dvadmin/utils/import_export_mixin.py  backend/dvadmin/utils/
cp -v <补丁包>/backend/dvadmin/utils/import_export.py        backend/dvadmin/utils/

python3 -m py_compile backend/dvadmin/alert/models.py \
                      backend/dvadmin/alert/services.py \
                      backend/dvadmin/alert/views/rule.py \
                      backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py \
                      backend/dvadmin/utils/import_export_mixin.py \
                      backend/dvadmin/utils/import_export.py \
  && echo "语法 OK"
```

**应该看到**：6 行 `cp` 记录 + 最后一行 `语法 OK`。

> ★ 注意：这一步**只把文件放到位**，还没生效 —— 生效靠第 7 步重启容器。
> 迁移（第 3 步）可以先跑，因为 `docker exec` 会新起一个 Python 进程，读到的是磁盘上的新代码。

### 第 3 步 · 数据库迁移 + 菜单按钮注册（有迁移文件时必做）

本批有 **2 个 app** 要迁移。

```bash
# 先看会执行什么，只读，不改库
docker exec dvadmin3-django python manage.py showmigrations release bastion

# 执行（★ 两条都要跑）
docker exec dvadmin3-django python manage.py migrate release
docker exec dvadmin3-django python manage.py migrate bastion
```

**应该看到**：`Applying release.0001_initial... OK` 与
`Applying bastion.0005_alter_commandlog_source... OK`

**验证迁移真的生效了**（别只看 `OK`）：

```bash
docker exec dvadmin3-django python manage.py shell -c "
from django.db import connection
t = set(connection.introspection.table_names())
print('release 四表:', sorted(x for x in t if x.startswith('release_')))
print('bastion 新列:', 'source' in [f.name for f in __import__('dvadmin.bastion.models', fromlist=['CommandLog']).CommandLog._meta.get_fields()])
"
```

**应该看到**：`release` 的 **4 张表**都在（`release_pipeline` / `release_node` / `release_run` / `release_node_log`），
且 `bastion 新列: True`。

**③ 注册菜单与按钮**（本批新增；不跑这一步 →「发布管理」的两个子菜单不出现，或页面在但按钮全没）：

```bash
# 先 dry-run 看要做什么（只读）
docker cp backend/register_release.py dvadmin3-django:/backend/register_release.py
docker exec dvadmin3-django python /backend/register_release.py --dry-run

# 确认无误后执行
docker exec dvadmin3-django python /backend/register_release.py --apply
```

**应该看到**：dry-run 列出「菜单 2 条 + 按钮 16 条」的增改计划；`--apply` 后提示已授权。

> ★ **为什么每个 `@action` 都必须登记**：DVAdmin 的 `CustomPermission` 是拿 (api 路径, HTTP method)
> 去 `RoleMenuButtonPermission` 里**逐条** `re.match` 的。漏登记任一 action ⇒ 那条接口对非超管
> **恒返回业务码 4000**（注意：是 **HTTP 200 + code 4000**，不是 401/403，看日志极易误判成"没登录"）。
> 只建按钮、不授 `RoleMenuButtonPermission` ⇒ 连超管都「页面在、按钮全没」
> （前端按钮显隐拿的是"当前角色的按钮数据"，`is_superuser` **不作数**）。

> ★ **app 名怎么确认**：`migrate` 后面跟的是 Django app label。
> `backend/dvadmin/release/apps.py` 的 `name = 'dvadmin.release'` ⇒ label 是 **`release`**。
> 报 `No installed app with label 'xxx'` 就是这里写错了。

> 📎 **上一批（09-29）第 3 步的记录，保留备查**：那次是迁移 `alert.0007_alertrule_source_labels`，
> 给 `AlertRule` 加 `source` / `labels` 两列，并把**存量规则一律标成 `prom`** ——
> 因为 `source=platform` 的规则会被平台下发到 Prometheus，而存量规则此前只存在于 Prometheus 侧，
> 不明文标成 `prom` 的话，升级后第一次点「同步规则」会把它们**再下发一遍**，与原规则**重复触发**。
> **若你的环境还没做过那次升级，先补一条** `docker exec dvadmin3-django python manage.py migrate alert`。

### 第 4 步 · 前端（改了 `web/` 就必须重建镜像）

> ★ **先记住一件事**：`xwops/web:1.0.0` 是把前端**编译进镜像**的。
> 代码拉下来了，**镜像不重建就永远是旧的** —— 目标机上现在跑的还是上次构建出来的那份。
> 所以这一步是「**要么就地构建、要么在外网机构建后把 tar 搬进来**」，二选一，绕不开。

**① 先探测：这台机器能不能就地构建？**

```bash
curl -s -o /dev/null -w 'npm源=%{http_code}\n' --max-time 8 https://registry.npmmirror.com/
docker pull node:20-alpine && docker pull nginx:alpine     # 构建要用的两个基础镜像
```

**应该看到**：`npm源=200`，且两个 `docker pull` 都完成。

> `npm源=200` 且两个 pull 都成功 ⇒ 走 **②A**；
> 任一条失败（超时 / 拉不动）⇒ 走 **②B**。

**②A 就地构建（最省事）**

```bash
cd <部署目录>
docker compose up -d --build dvadmin3-web
```

**应该看到**：构建日志以 `Successfully built` / `Built` 结束，最后容器重建完成。

**②B 外网机构建 → 导出 → 搬进来 → 加载**（目标机不能构建时）

```bash
# —— 在外网机执行（要能访问 npm 源、装了 docker）——
cd <仓库根目录>
docker build -f docker_env/web/Dockerfile -t xwops/web:1.0.0 .
bash docker/save-images.sh --web-only        # 产出 docker/xwops-web-1.1.0.tar

# 把下面【两个】文件一起拷到目标机（scp / U 盘 / 跳板机都行）：
#   docker/xwops-web-1.1.0.tar
#   docker/checksums.txt     ★ 必须一起拷！save-images.sh 会把它覆盖成本次包的校验值，
#                              下一步的 md5sum -c 就是拿它来对
```

```bash
# —— 在目标机执行 ——
cd <部署目录>
cd docker && md5sum -c checksums.txt && cd ..     # 校验搬运过程有没有损坏
docker load -i docker/xwops-web-1.1.0.tar         # 同 tag 覆盖旧镜像
docker compose up -d --no-build dvadmin3-web
```

**应该看到**：`checksums.txt: OK` + `Loaded image: xwops/web:1.0.0` + 容器重建完成。

> ★ 一定要 `--no-build`：`docker-compose.yml` 里 `image:` 与 `build:` 是**并存**的，
> 不加这个参数会把「容器起来」和「是否又触发了一次构建」混在一起，事后说不清跑的是哪个版本。

**③ 怎么确认容器真换成了新镜像**（只看「容器 Up」判断不出来）

```bash
docker inspect dvadmin3-web --format '{{.Image}}'          # 容器引用的镜像 ID
docker image inspect xwops/web:1.0.0 --format '{{.Id}}'    # 该 tag 现在的镜像 ID
curl -s -o /dev/null -w 'HTTP=%{http_code}\n' http://127.0.0.1:8080/    # 期望 200
```

**应该看到**：两个 ID 对应（`docker inspect` 给的是容器引用的那个镜像 ID），且 `HTTP=200`。

> `HTTP=200` 且**页面不是旧的**才算换成功。前端只改一个 `.vue` 也可能因构建报错产出空 `dist`，
> 届时 8080 会返回 404 或空白页。
>
> ★ 想在**上线前**先把产物验一遍（推荐），见 §8.2 的产物核验清单。
> ★ 没有外网 docker 机、又急着上 ⇒ §8.3 的应急办法（只换 `dist`，不重建镜像）。

### 第 5 步 · 打通规则投递（**上一批（09-29）专属 —— 本批（v1.1.0）跳过这一步**）

> 🚨 **动手前先做这两件事，顺序不能反** —— 本步骤会把 Prometheus 的规则目录接给平台，
> 而平台会**全量重写** `<Prom规则目录>/devops_rules.yml`（**不是追加**）。
>
> ★★ **触发点有两个，第二个才是最容易中招的**：
> 1. 点「同步规则」按钮；
> 2. **在平台上新建 / 编辑 / 删除任何一条告警规则** —— 这三个动作**都会自动触发**一次
>    全量重写（`perform_create` / `perform_update` / `perform_destroy` 里都调了同步）。
>    ⇒ 也就是说，**哪怕你只是删掉平台上一条测试规则，也会把同名的人工文件清空**。
>
> ```bash
> # ① 备份整个规则目录（一条命令，是唯一的后悔药）
> cp -a <Prom规则目录> ~/prom_rules.bak_$(date +%F_%H%M)
> ls -l ~/prom_rules.bak_*/                 # 确认里面有东西
>
> # ② 记下平台里现在有多少条规则 —— 「同步规则」写出来的就是这些
> ```
>
> ⚠️ **为什么必须备份**：平台的下发文件名**固定**叫 `devops_rules.yml`。若你的
> `<Prom规则目录>` 里**已有同名文件承载着人工规则**，第一次点「同步规则」就会把它
> **整份替换**成平台数据库里 `source='platform'` 的那些。**人工写的规则不在数据库里，
> 就不会被写回** —— 丢了之后重载 Prometheus 也救不回来。

> ★★ **推荐做法：给平台单独开一个子目录**，让它永远碰不到你的人工规则：
>
> ```bash
> mkdir -p <Prom规则目录>/platform
> ```
>
> override 里挂 **`<Prom规则目录>/platform`**（而不是整个 `<Prom规则目录>`），
> 并让 Prometheus 两边都读 —— `prometheus.yml` 里：
>
> ```yaml
> rule_files:
>   - "rules/*.yml"             # 你人工维护的（保持不动）
>   - "rules/platform/*.yml"    # 平台下发的
> ```
>
> 改完 `curl -X POST http://127.0.0.1:9090/-/reload` 生效。
> ⇒ 此后平台**无论怎么全量重写，都只发生在自己那个子目录里**，人工文件零风险。
>
> 图省事直接挂整个 `<Prom规则目录>` 也能用，但**必须先做上面的备份**。

**原理**：平台把规则文件写在**自己的容器里**，而 Prometheus 读的是**宿主机的目录**。
两者在同一台机器上，所以**一行 bind mount** 就能把两者接起来：

```bash
cd <部署目录>

# ★ 先看这个文件在不在 —— 第 4 步的应急办法(§8.3)也会写它，别把已有的冲掉
ls -l docker-compose.override.yml 2>/dev/null \
  && echo ">>> 已存在！不要用下面的 cat >，会整份覆盖 —— 请手工编辑，只补两个 volumes 条目" \
  || echo ">>> 不存在，可以放心用下面这段创建"
```

**文件不存在时**，用这段一次性写全：

```bash
cat > docker-compose.override.yml <<'YAML'
# 本机专用（已 gitignore）：把 Prometheus 的规则目录直接挂进后端容器
services:
  dvadmin3-django:
    volumes:
      - /opt/prometheus/rules/platform:/backend/dvadmin/alert/rules
  dvadmin3-celery:
    volumes:
      - /opt/prometheus/rules/platform:/backend/dvadmin/alert/rules
YAML
```

**文件已存在时**，手工编辑，最终内容形如（把两个新条目补进去，**保留原有内容**）：

```yaml
services:
  dvadmin3-django:
    volumes:
      - /opt/prometheus/rules/platform:/backend/dvadmin/alert/rules
  dvadmin3-celery:
    volumes:
      - /opt/prometheus/rules/platform:/backend/dvadmin/alert/rules
  # ...你原有的其它服务/挂载保持不动
```

> ★ 把 `/opt/prometheus/rules/platform` 换成你环境里 **`<Prom规则目录>/platform`**
> （先 `mkdir -p` 建出来；这就是上面推荐的"子目录隔离"）。
> ★ 若你**就是想直接挂整个 `<Prom规则目录>`**（老做法）：把上面两处的
> `/platform` 去掉即可 —— 但**务必先做第 5 步开头的备份**，否则第一次「同步规则」
> 就会把你的人工 `devops_rules.yml` 整份换掉。
> ★ compose 对 `volumes` 是**追加合并**：原来的 `./backend:/backend` 仍在，新增的这条**更深**，
> 容器内 `/backend/dvadmin/alert/rules` 由它接管 —— 所以**不用改 `RULES_DIR`，不用改一行代码**。
> ★ `docker-compose.override.yml` 里 **`services:` 这个顶层键只能有一个**，
> 服务名也只能出现一次 —— 否则 compose 会报错或静默丢掉其中一个。

**先校验 YAML 语法，再让挂载生效**：

```bash
docker compose config >/dev/null && echo "compose 配置语法 OK"
docker compose up -d --no-build dvadmin3-django dvadmin3-celery
```

**应该看到**：`compose 配置语法 OK` + 两个容器重建完成。

> ★ **为什么要先 `docker compose config`**：它会把 override 与主 compose 合并后完整解析一遍。
> YAML 写错（缩进错、`services:` 漏了、服务名写重）会在这里**立刻报错**，
> 而不是等到某个容器起不来再猜。

**验证挂载真的进去了**：

```bash
docker inspect dvadmin3-django --format '{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' \
  | grep alert/rules
# 期望输出：/backend/dvadmin/alert/rules
```

**再验「容器里写的，宿主机看得到」**（这是**唯一**能证明投递链路通了的判据）：

```bash
docker exec dvadmin3-django sh -c \
  'echo probe > /backend/dvadmin/alert/rules/.write_probe && ls -l /backend/dvadmin/alert/rules/.write_probe'
ls -l /opt/prometheus/rules/platform/.write_probe   # 宿主机必须也能看到这个文件
rm -f /opt/prometheus/rules/platform/.write_probe
```

**应该看到**：两条 `ls -l` 都能列出 `.write_probe`。

> `.write_probe` 不以 `.yml` 结尾，不会被 Prometheus 的 glob 解析到，可安全创建删除。

### 第 6 步 · Alertmanager 侧（**上一批（09-29）专属 —— 本批（v1.1.0）跳过这一步**）

**先找到 AM 的配置文件**（不同部署方式路径不同）：

```bash
ps -ef | grep -v grep | grep alertmanager          # 看 --config.file= 指向哪
systemctl cat alertmanager 2>/dev/null | grep -i config.file   # 若用 systemd 管理
```

1. **兜底 receiver 改成平台** —— 否则平台建的规则触发后，告警落到默认 receiver 就丢了：

```yaml
# <AM配置目录>/alertmanager.yml
route:
  receiver: xwops          # 原来是别的（如 default / null）
```

2. **给平台规则加上与既有路由一致的标签** —— 页面「告警规则 → 编辑 → 附加标签」填：

```json
{"team": "ops"}
```

> 两件事是**互补**的：第 1 条保证「没人认领的告警也有地方去」，第 2 条保证
> 「平台规则能命中你原有的 `team` 路由」。建议都做。
>
> ★ `severity` 由「级别」字段统一生成，写在「附加标签」里会被忽略（后台已过滤）。

**改完重载并确认生效**：

```bash
curl -s -X POST http://<内网IP>:9093/-/reload -o /dev/null -w 'HTTP=%{http_code}\n'   # 期望 200
# 若 AM 未开 --web.enable-lifecycle，则用：
# docker restart <am容器>  /  systemctl restart alertmanager
```

**应该看到**：`HTTP=200`。

### 第 7 步 · 重启服务 + 自检

```bash
cd <部署目录>

# 后端改了 .py ⇒ 必须重启（uvicorn 没开 --reload）
docker compose restart dvadmin3-django dvadmin3-celery

# 等 10 秒，自检三件事
sleep 10
docker compose ps
curl -s -o /dev/null -w 'home=%{http_code}\n' http://127.0.0.1:8080/
curl -s -o /dev/null -w 'api=%{http_code}\n'  http://127.0.0.1:8080/api/api/
```

**应该看到**：5 个容器 `Up`、`home=200`、`api=200`。

> ★ **`api` 的地址是双层的 `/api/api/`** —— 这是设计如此（nginx 有一层 rewrite），
> 单层 `/api/...` 恒 404，不是故障。详见 §6。
>
> ★ 第 4、5 步的 `up -d` 其实已经重建过相关容器，这一步是**兜底确认** ——
> 尤其是你走了通道 B 手工拷文件、没重建容器的情况。

---

## 4. 回归验收清单（逐项打勾再收工）

### 4.1 服务层

见第 7 步的自检三件事（`docker compose ps` + 两个 `curl`）。

> ★ 前端只改一个 `.vue` 也可能因构建报错产出空 `dist`，届时 8080 会 404 或空白页 ——
> **只看「容器 Up」判断不出问题**，必须走 8080 复验。

### 4.2 功能层（浏览器里点）

| # | 检查项 | 期望 |
|---|---|---|
| 1 | 左侧出现 **发布管理 → 流水线编排 / 执行记录** 两个菜单 | 菜单在、按钮在（新建/编辑/删除/设计流程都可点）。★ 缺了就回去跑 §3 第 3 步③ |
| 2 | 新建一条流水线 → 点「设计流程」 | 能加 6 种节点（参数化 / 环境检查 / 上传制品 / 执行命令 / 构建 / 通知），能排序；保存后重开还在 |
| 3 | 设计器里选「发布服务器」 | 候选来自 **CMDB 资产列表**（不是手输 IP） |
| 4 | 执行记录 → 点「运行」→ 在运行面板反复点「推进」 | 节点逐个推进到成功；★ **前端不会在第 5 秒报超时**（`run/api.ts` 已显式 `timeout: 900000`） |
| 5 | 运行面板 → 节点日志 | 每个节点的输出可见；命令节点在目标机上留痕 |
| 6 | 堡垒机 → **命令审计** | `source` 列能筛出 **「流水线发布」** ⇒ 迁移 `bastion/0005` 生效的证据 |
| 7 | 日志检索 → 选索引 → **选一个时间范围** → 查询 | ★ **不再报错**（本批修的：时间戳由「空格」归一化成 `T`；此前一选时间范围必 400） |
| 8 | 日志检索 → 触发一次表单校验失败 | 错误提示是**完整中文**，不是 `节点:）` 这种乱码（本批修的 DRF 错误详情解析） |

### 4.3 链路层（可选，但强烈建议做一次）

在平台上新建一条**必然触发**的规则（如 `up == 0`），确认整条链路：

```
Prometheus → Alertmanager → 平台 webhook(202) → Celery → 告警事件页出现记录 → 通知渠道收到
```

---

## 5. 预期行为变化（**别当成新 bug**）

> 📎 本节各条**都是上一批（09-29：告警规则 / CMDB 导入）的行为变化**，保留备查。
> 若你的环境只做本批（v1.1.0）改动，本节大多用不上。

| 现象 | 为什么 | 怎么办 |
|---|---|---|
| 升级后第一次点「同步规则」，**存量规则没被下发** | 迁移把存量规则标成了 `prom`（只纳管不下发），这是**防双发**的设计 | 正常。要让平台接管某条，把它的「来源」改成「平台」 |
| 点「同步规则」**直接报错**，说读不到 N 条规则 | **回读校验**发现 Prometheus 里没读到 —— 说明投递没打通 | 做 §3 第 5 步（bind mount） |
| 点完「同步规则」，`<Prom规则目录>` 里的**人工规则不见了** | 平台是**全量写**固定文件名 `devops_rules.yml`（不是追加）⇒ 把同名的人工文件整份替换了 | ⚠️ 按 §6 故障表最后一行的办法**从 git 历史取回**；之后改用「子目录隔离」（§3 第 5 步）防复发 |
| 平台规则触发了但**收不到告警** | 平台规则 labels 只有 `severity`，命中不了 AM 里 `match: {team: ops}` 的路由 | 做 §3 第 6 步 |
| 「活跃告警」里同一个任务名出现 19 行 | 规则是 `sum by (process_name) ... > 0` ⇒ **每个不同 `process_name` 一条独立序列**，Alertmanager 按标签指纹去重，标签不同就是不同告警 | 正常。详情弹窗新增的「指纹」行可以自证：指纹不同 = 两条独立告警 |
| `backend/dvadmin/alert/rules/devops_rules.yml` 在 `git status` 里显示为已删除跟踪 | 该文件已移出版本控制（磁盘上还在）—— ★ **注意：它里面可能是人工维护的规则，不是"程序生成的"** | 现象正常；**别 `git add` 它**，也**别让平台全量覆盖它**（见 §3 第 5 步） |
| `git pull` 报 `Not possible to fast-forward` | 远端历史被重写过（有人 `amend` / 强推），本地指向一个远端已不存在的提交 | §9.2 有一条命令分辨；**别照 git 提示做 merge / rebase** |

---

## 6. 故障处理（按现象查）

| 现象 | 最可能的原因 | 处置 |
|---|---|---|
| `git pull` 报 **`Not possible to fast-forward`** | 本地有改动／远端历史被重写 | 先跑 §9.2 的分辨命令；按 §3 第 1 步「情况 2」对齐 |
| `git clean -xfd` 之后 **配置和数据库没了** | `-x` 会把 gitignore 的文件一起删（`conf/env.py`、`.env`、`docker_env/*/data/`） | 从第 0 步的备份恢复数据库；重新 `cp backend/conf/env.example.py backend/conf/env.py` 并填值。★ **这个动作永远不要做** |
| `docker compose` 报 **unsupported top-level key** / **no services** | `docker-compose.override.yml` 写坏了（常见：只追加了带缩进的服务块，漏了 `services:`） | `docker compose config` 看报错行；按 §3 第 5 步的完整内容重写 |
| 第 5 步做完，**规则挂载不见了** | 用了 `cat >`（整份覆盖）把之前的内容冲掉 | 手工把缺的服务/挂载补回去，再 `docker compose config` 校验 |
| 访问 8080 报 **502** | django 没起来，或 nginx 的 `proxy_pass` 指向的容器 IP 不对 | `docker logs dvadmin3-django` 看报错；核对 `docker_env/nginx/my.conf` 的 IP 与 compose 里 django 的 `ipv4_address` 是否都是 `172.31.0.12` |
| 8080 返回 **404 / 空白页** | 前端镜像没换（`dist` 是空的或旧的） | 回到 §3 第 4 步 ③ 比对镜像 ID；重新构建 |
| 访问 `/api/xxx` 直接 **404** | 用了**单层** `/api` | 改成**双层** `/api/api/xxx`（nginx 有一层 rewrite，这是设计如此） |
| 后端容器**起不来 / 立刻退出** | `backend/conf/env.py` 不存在或格式错 | `cp backend/conf/env.example.py backend/conf/env.py` 并填值；`docker logs dvadmin3-django` 看 ImportError |
| 后端报 **Can't connect to MySQL** | `.env` 与 `conf/env.py` 的密码不一致 | 两处密码必须完全相同 |
| `migrate` 报 **No installed app with label 'xxx'** | app label 写错 | `ls backend/dvadmin/` 看真实目录名；`alert` 的 label 就是 `alert` |
| `migrate` 之后页面**仍然报错缺字段** | 迁移没真的跑成功，或跑在了错的库上 | `docker exec dvadmin3-django python manage.py showmigrations alert` 看 `0007` 前是不是 `[X]` |
| 登录后部分页面 **500** | 数据未初始化 / 超管部门引用悬空 / 全局中间件抛异常 | `docker logs dvadmin3-django` 看 traceback；新版 `redaction.py` 已修「未登录 POST 全站 500」这个 P0，确认你拿到的 md5 与 §3 第 1 步一致 |
| §3 第 1 步的 11 个 md5 里**只有个别对不上** | ① 该文件被本地改过；② 该文件是 CRLF 行尾（在 Windows 上核对才会遇到）；③ 通道 B 漏拷 | 先 `file <该文件>` 看行尾；再 `git diff --stat <该文件>` 看是否被改过；都不是就按 §3 第 1 步重新取一次代码 |
| `md5sum -c checksums.txt` 报 **FAILED** | 镜像包传输不完整，或 `checksums.txt` 不是这个包的 | 重新传输；★ 确认 tar 与 `checksums.txt` 是**同一批**生成的（§3 第 4 步 ②B） |
| `docker load` 报 **no space left** | 磁盘不足 | 至少留 3 GB |
| 「同步规则」**提示成功但 Prometheus 里没有** | 平台把规则文件写在自己容器里，**从不投递**到 Prometheus 主机 | 本批起该按钮会**回读**校验，这种情况会直接报错；仍要确保做了 §3 第 5 步 |
| 「活跃告警」页报 **未配置 Alertmanager 地址** | 该页是**实时透传** `GET {AM}/api/v2/alerts`，与 webhook 落库是**两条独立通路** | 在「监控告警 → 数据源管理」建一条 `source_type=alertmanager` 且**状态启用**的记录 |
| 点完「同步规则」/ 在平台上动了一条规则后，下发文件**变成一个 47 字节的空文件** | 平台只导出数据库里 `source='platform'` 的规则；你的人工规则不在库里 ⇒ 导出结果为空（正好 47 字节：`groups: / - name: devops_alert_rules / rules: []`） | ★★ **先判断告警还灵不灵**：`curl -s http://127.0.0.1:9090/api/v1/rules \| grep -c '"name"'` —— **数量正常 ⇒ reload 没生效、内存里还在**；**接近 0 ⇒ 已经没了**。再按下一行恢复，然后做「子目录隔离」 |
| 点完「同步规则」，`<Prom规则目录>/devops_rules.yml` 里的**人工规则被覆盖没了** | 平台**全量写**这个固定文件名；人工规则不在数据库里，就不会被写回 | ① 先 `cp -a <Prom规则目录> ~/prom_rules.bad_$(date +%F_%H%M)` 留档；② 在**能上外网的机器**上取回旧版（它存在于提交 `d9b20ec`）：<br>`git show d9b20ec:backend/dvadmin/alert/rules/devops_rules.yml > devops_rules.yml`<br>或 `curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/d9b20ec/backend/dvadmin/alert/rules/devops_rules.yml -o devops_rules.yml`<br>（应为 **18214 字节 / 50 条 / md5 `98ac24469fb0d5c9184fc06afbff04f7`**）；③ 拷回 `<Prom规则目录>/devops_rules.yml`；④ `curl -X POST http://127.0.0.1:9090/-/reload`；⑤ 改用「子目录隔离」（§3 第 5 步）防复发。<br>★ 该文件在**公开仓库的历史**里 ⇒ 内容对外可见，建议尽快清理历史 |
| 点「下载导入模板」，提示**「导入任务已创建，请前往下载中心」**，但下载中心**没有任务**、模板**不下载** | 该按钮是**同步返回文件流**，不是异步任务。后端在生成 xlsx 时抛了 500（返回 JSON），而前端 `downloadFile()` 把**任何 JSON 响应**都当成「异步任务已创建」（`web/src/utils/service.ts`）⇒ 提示与事实相反 | **本批已修**（`1d8db6b`）。确认后端文件 md5 = §3 第 1 步那个 `import_export_mixin.py` 的值；`docker logs dvadmin3-django` 里若见到 `TypeError: expected string or bytes-like object` / `Cannot convert ... to Excel` ⇒ 就是这个（`gettext_lazy` 对象不能直接交给 openpyxl）。取到新代码 + 重启 django 即可 |
| 上传填好的模板后报 **`[Errno 2] No such file or directory: 'backend/media/files/…'`** | **上传落盘**与**回读解析**是两套路径口径：上传走 `MEDIA_ROOT="media"`（相对值）⇒ 真实位置是 `<进程 CWD>/media/…`；回读原来写 `os.path.join(settings.BASE_DIR, file_url)`。只要 `BASE_DIR ≠ CWD`（或 `BASE_DIR` 被 `conf/env.py` 覆盖成相对值），必然找不到 | **本批已修**（`4b0a80e`）。确认 `import_export.py` 的 md5 = §3 第 1 步的 `83c0ec91…`；取到新代码 + **重启 django** 即可。★ 若修完仍报同样的错，说明**文件真的不在磁盘上**（容器重建/清理过），**重新上传一次**即可；此时日志（`docker logs dvadmin3-django`）会打印**已尝试的候选路径**，按它就能看出实际落盘目录 |

**深挖用的三条命令**（卡住时先跑这个，比猜快）：

```bash
docker compose ps                                          # 谁没起来
docker logs --tail 100 dvadmin3-django                      # 后端报什么
docker logs --tail 100 dvadmin3-celery                      # 异步任务报什么
```

---

## 7. 回滚

**后端**（最快）：把 §3 第 2 步拷进去的 6 个文件换回旧版，然后重启后端容器（§3 第 7 步）。

**前端**：换回旧镜像（`docker load` 上一版 tar）或删掉 §8.3 那行挂载，然后 `up -d --no-build dvadmin3-web`。

**数据库**：`0007` 只做 `AddField` + 一次 `UPDATE`，可安全 `migrate alert 0006` 回退结构，
但**回退前请先想清楚**：`source`/`labels` 两列一旦被删，页面会立刻报错（前端已引用），
所以**正常情况下不要回退迁移**，只回滚代码。

**整体回退**：从第 0 步的备份恢复：

```bash
docker exec -i dvadmin3-mysql sh -c \
  'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" django-vue3-admin' < backup_<时间戳>.sql
```

> ⚠️ 恢复必须用**同一个** `CREDENTIAL_ENCRYPTION_KEY`，否则已加密的渠道密钥解不开。

---

## 8. 详解：前端构建与备选

> ★ **本节不含"执行步骤"** —— 构建与交换镜像的命令在 **§3 第 4 步**（②A 就地 / ②B 外网机搬运）。
> 这里只讲**为什么**、**怎么验**、以及**没有外网 docker 机时的备选**。
> （同一个命令写在两处必然漂移 —— 所以本节只保留 §3 里没有的那部分。）

### 8.1 两个容易踩的点

- **沿用同一个 tag `xwops/web:1.0.0`**：`docker-compose.yml` 一个字都不用改，少一个出错点。
  若确实要换 tag（如 `1.1.0`），**必须同步改 `docker-compose.yml` 的 `image:` 行**，
  否则表现是「明明 load 了新镜像，页面还是老的」。
- **覆盖同一个 tag 只影响之后新建的容器**。正在跑的容器引用的是**镜像 ID**，不会被换掉
  ⇒ 必须 `docker compose up -d`（**重建容器**）才生效 —— 这也是 §3 第 4 步 ③ 要你去比对
  「容器引用的镜像 ID」和「tag 现在的镜像 ID」的原因。

### 8.2 产物核验清单（**上线前**做，建议固化进流程）

构建完、打包前先扫一遍镜像里的静态文件。以下几条是发版时实际跑过的，
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

> 注意这里求的是**命中数为 0**（负向检测），所以三类写法各有讲究：
> - **邮箱**用「任意邮箱」的通用正则 —— 不是把某个具体邮箱写进命令；
> - **图片**用 CDN 域名清单（`baidu` / `csdnimg` / …）—— 命中即说明产物里有外链；
> - `localhost:8000` / `admin123456` / `9ba8fc80` 是**上游公开默认值与占位标识**
>   （`admin123456` 见 `DEPLOY.md` §7.3，上游 DVAdmin 自带文档里就有），
>   写出来是为了「万一被编进产物就报警」。
>
> ★ **本项目自己的真实口令、密钥、内网 IP 一律不写进本文** —— 那才会让文档本身变成泄露渠道。

### 8.3 应急：只替换 `dist`，不重建镜像（**没有外网 docker 机时**）

思路：不动镜像，把新编译的静态文件**挂进** web 容器覆盖 `/usr/share/nginx/html`。

```bash
# —— 在任意一台有 Node 20 + 能访问 npmmirror 的机器上 ——
cd <仓库根目录>/web
npm install --registry=https://registry.npmmirror.com --no-audit --no-fund --legacy-peer-deps
npm run build                    # 产出 web/dist/
tar czf xwops_web_dist_20260929.tar.gz -C dist .
```

拷到目标机并解到独立目录（**别覆盖仓库里的 `web/`**）：

```bash
mkdir -p <部署目录>/_dist_20260929
tar xzf /tmp/xwops_web_dist_20260929.tar.gz -C <部署目录>/_dist_20260929
ls <部署目录>/_dist_20260929/index.html     # 必须有

cd <部署目录>
docker compose config >/dev/null && echo "compose 配置语法 OK"
docker compose up -d --no-build dvadmin3-web
```

> ⚠️ **`docker-compose.override.yml` 要手工编辑，不要用 `cat >>`** ——
> 往文件末尾追加以两个空格开头的服务块，会得到一个**没有 `services:` 顶层键**的文件，
> compose 直接报错。正确做法：在 `services:` 下、与其它服务**平级**的位置加上这一段：
>
> ```yaml
>   dvadmin3-web:
>     volumes:
>       - ./_dist_20260929:/usr/share/nginx/html
> ```
>
> 改完**一定**先跑 `docker compose config`（上面那条）再 `up`。
>
> ⚠️ 这个办法的**回滚**最快：删掉那行挂载 → `docker compose up -d --no-build dvadmin3-web`，立刻回到镜像里的旧版。
> 但它是**运行时挂载**，下次别人 `docker compose up -d`（无 override）就会「无声回退」—— 只适合应急，别当长期方案。

---

## 9. 详解：代码通道

> ★ 三条通道的**命令**分别在 **§3 第 1 步**（通道 A / B）与 **§9.4**（通道 C）。
> 本节不重复命令，只讲**判断依据**和**坑** —— 同一个命令写在两处必然漂移。

### 9.1 怎么判断走哪条

用 **§1.2 第 ① 条**那条探测命令，照下表读结果：

| 输出 | 结论 | 走 |
|---|---|---|
| 打出 40 位哈希 | 能直连 | **通道 A** |
| `GnuTLS recv error (-110)` / `TLS connection was non-properly terminated` | HTTPS 被干扰 | **通道 B**（或 C） |
| `Could not resolve host` / `timed out` | 根本没有外网 | **通道 B** |
| `Host key verification failed` | remote 走 SSH 但没配 key | **通道 B**（或 C-1） |

> ★ **`TLS connection was non-properly terminated` 与「这台机器能通外网」并不矛盾** ——
> 它可能能访问 npm / pip 源，只是 `github.com:443` 被干扰。实测就是这个情况。
> 所以**别用「能 ping 通外网」推断「能 git pull」**，这两件事要分开探。

> ★★ **可达性会变，必须以实测为准，别照搬昨天的结论**：
> 09-29 该机 `git fetch` 报 `GnuTLS recv error (-110)`（HTTPS 被干扰）；
> **09-30 实测已能正常 fetch** —— 输出里能看到 `remote: Enumerating objects…`、
> `Unpacking objects: 100%` ⇒ 该机现在走**通道 A**。
> 同一条链路昨天不通、今天通是常事，所以本节只给**判断方法**，不给结论。

### 9.2 通道 A：`Not possible to fast-forward` 的**两种**原因（处置相反）

`git status --short` 有输出 ⇒ 目标机上有本地改动（`conf/env.py`、`.env`、
`docker-compose.override.yml` 都不算，它们已 gitignore）。**先决定要不要**：

- **都不要了**（内网常见）⇒ 按 **§3 第 1 步「情况 2」**走（导 patch 留底 → `reset --hard`）；
- **想留着** ⇒ 先 `git stash push -u`，对齐后再 `git stash pop` 挑着看。

然后是本节重点。看到这条报错**别急着照 git 的提示做**，先跑**一条命令分辨**：

```bash
git -C <部署目录> merge-base HEAD origin/main
```

| 输出 | 病因 | 旁证 | 正确处置 |
|---|---|---|---|
| **没有任何输出** | ★★ **远端历史被重写**（有人 `amend` / 强推）⇒ 本地指向一个**远端已不存在**的提交，两边**没有共同祖先** | fetch 输出里那行以 `+` 开头、结尾带 **`(forced update)`** | 按 **§3 第 1 步「情况 2」**对齐远端 —— **不是 merge / rebase** |
| 打出一个 hash | **常规分叉**：本地有自己的提交 | `git log --oneline origin/main..HEAD` 有输出 | 逐个 `git show` 看清，再决定 `cherry-pick` 还是丢弃 |

> ⚠️ **实测案例（2026-09-30，本文档诞生后第一次真机拉取）**：
> 目标机报 `+ 63773f1..8738310  main -> origin/main  (forced update)` + `fatal: Not possible to fast-forward`。
> 核查发现：`63773f1` 与 `d9b20ec` **都是根提交（父提交数 0）**，
> `merge-base` **无输出** —— 因为 v1.0.0 那次发布被 `amend` 过，`63773f1` 是修订前版本，
> 已被强推丢弃（本机可用 `git fsck --lost-found` 看到它是 `dangling commit`）。
> 结论：**这不是"有人改过目标机的代码"，纯粹是远端换了历史。**

> ★★ **为什么绝不能照 git 提示的 `git merge --no-ff` / `git rebase` 做** ——
> 本例里本地那个提交是**根提交**（`git rev-list --count HEAD` = 1），它背着**整棵树**
> （919 个文件），而那是 **09-28 的旧版**。`rebase` 会把它**重放**到新历史之上
> ⇒ `redaction.py` 的 P0 修复、告警双源改造、本次全部文档改动**一起被退回**；
> `merge` 同理会把旧的整棵树合进来。
> **git 给的只是基于「确实分叉了」的通用建议 —— 它不知道远端被人重写过。**
> 这正是本条必须单独写出来的原因。

**对齐后**，回到 **§3 第 1 步的核对①**确认已到功能基线 —— 命令在那里，这里不重复。

> ★ 顺带说一句：**`--ff-only` 拒绝你，是它在保护你。**
> 若这里用的是裸 `git pull`（默认 merge），Git 会因"无共同祖先"而拒绝并要求加
> `--allow-unrelated-histories`；**一旦有人照加了那个参数**，就会造出一个把
> 09-28 旧树合进来的 merge commit，而且**不报错**。`--ff-only` 把这条路彻底堵死。

### 9.3 通道 B 的三个注意点

- **`git apply --check` 必须先跑**：它不改工作区，只回答「能不能干净应用」。
  报冲突说明目标机上的文件与补丁的基线不一致 —— 这时**别硬套**。
- **冲突的正式处理是 `git apply --reject`**：在失败处生成 `.rej` 文件，
  然后按 §3 第 2 步**逐文件手工拷**。手工拷反而更可控。
- **补丁包为什么不直接打包整目录**：本批 22 个文件里有 1 个是**删除跟踪**
  （`devops_rules.yml`）、5 个是**新增**（`0007_*.py`、`rules/.gitkeep`、`LOG-COLLECT.md`、
  `UPDATE.md`、`docs/images/log-collect/README.md`），其余 16 个是**修改**。补丁能精确表达
  "删/增/改"三类动作，而整目录覆盖既表达不了"删除"，还会把目标机的本地改动一起抹掉。

### 9.4 通道 C · 一劳永逸：给目标机配一条能用的拉取通道

三选一（从简单到复杂）：

```bash
# C-1 走 SSH over 443（绕开 HTTPS 干扰）
ssh-keygen -t ed25519 -C "xwops@target"          # 生成后把公钥加到 GitHub 账号
git remote set-url origin ssh://git@ssh.github.com:443/yx119924/devops_system.git
git fetch origin

# C-2 走 http 代理（若有可用代理）
git config --global http.proxy http://<代理>:<端口>

# C-3 只取单文件（仓库是 public，走 CDN）
curl -fsSL https://cdn.jsdelivr.net/gh/yx119924/devops_system@main/<文件相对路径> -o <目标路径>
```

> ★ C-3 只适合**零星补几个文件**，不适合整批更新 —— 它不表达"删除"，也容易漏文件。
> 本批要走 C-3 的话，得把 §3 第 1 步 `md5sum` 那 10 个文件全拉一遍再逐个核对 md5。

---

## 10. 附录

### 附录 A · 名词与环境速查

| 名词 | 含义 |
|---|---|
| **目标机** | 要更新的那台机器（跑着那 5 个容器） |
| **外网机** | 一台能上外网、装了 docker 的机器，用于构建前端镜像 |
| **通道 A/B/C** | 把代码送进目标机的三种方式（§9） |
| **功能基线** | 本批里唯一影响运行时的那个提交（本批是 `4b0a80e`） |
| **override 文件** | `docker-compose.override.yml`，本机专用、已 gitignore，用来追加挂载 |
| **运行时产物** | 程序自己写出来的文件（生成的规则 yml、数据目录、日志、缓存）—— **不该进版本控制** |

容器与端口（默认栈）：

| 容器 | 端口 | 备注 |
|---|---|---|
| `dvadmin3-web` | `8080`（对外） | nginx：前端 + `/api` 反代 |
| `dvadmin3-django` | `127.0.0.1:8000`（**只绑回环**） | 远程调试用 SSH 隧道；**跨机不要用 8000** |
| `dvadmin3-mysql` | `127.0.0.1:3306`（只绑回环） | |
| `dvadmin3-redis` | —— | |
| `dvadmin3-celery` | —— | |

> ★ 8000 只绑 `127.0.0.1` 是**故意的**：历史版本写成 `0.0.0.0` 会让后端（含免认证的
> Swagger 文档）绕过 nginx 直接被外部访问。所以**跨机器只能走 8080**。

### 附录 B · 本批文件 md5 对账表

见 §3 第 1 步的核对② —— 那里给的是**可直接执行**的命令与期望输出。

### 附录 C · 规则以后加在哪？两边怎么同步？

> **一句话**：规则的**家只有一个 —— Prometheus 侧的 `<Prom规则目录>`**（你人工维护，文件想分几个就分几个）；
> **平台是"展示台 + 可选的另一个出口"**，想让它显示就点「**同步 Prom**」拉进来。

**四条路径，别搞混**（两个按钮**方向相反**，这是最容易踩的地方）：

| 你想做的事 | 在哪做 | 结果 |
|---|---|---|
| **加 / 改要告警的规则**（推荐主路径） | Prometheus 的 `<Prom规则目录>/*.yml`（**随便分文件**） | 写完 `curl -X POST http://127.0.0.1:9090/-/reload` ⇒ 立即生效 |
| **让平台里也能看到它** | 平台「告警规则 → **同步 Prom**」 | 拉进平台建档，来源 = **Prom 纳管**。★ 它**不会被下发**，所以不会双发 |
| **在平台上新建一条规则** | 平台页面（来源选「**平台（下发）**」） | 落库；**并自动全量重写** `<Prom规则目录>/devops_rules.yml` |
| **改一条「Prom 纳管」规则的阈值** | ⚠️ 在平台上改了**不生效** | `source='prom'` 的规则不参与下发；要生效得改成「平台」来源，或去 Prometheus 侧原文改 |

**两个按钮的方向**（务必分清）：

```
「同步 Prom」 ： Prometheus ──读 /api/v1/rules──▶ 平台数据库    （只纳管，不动你任何文件）
「同步规则」 ： 平台数据库 ──全量写文件────▶ <Prom规则目录>/devops_rules.yml  （会覆盖同名文件）
```

> ★ **「同步规则」的全量写 = 只写它自己那一个文件**。所以只要你的人工文件**不叫**
> `devops_rules.yml`，就永远不会被它碰到 —— 这正是下面「目录隔离」的依据。

**推荐落法（目录隔离）** —— 让平台独占一个子目录，你的人工文件零风险：

```
<Prom规则目录>/
├── node.yml / kafka.yml / pg.yml …   ← 你人工维护，随便分几个文件
└── platform/
    └── devops_rules.yml              ← 平台独占；被覆盖也只影响这里
```

`prometheus.yml`：

```yaml
rule_files:
  - "rules/*.yml"             # 人工的
  - "rules/platform/*.yml"    # 平台下发的
```

override 里的挂载源改成 `<Prom规则目录>/platform`（见 §3 第 5 步）。

⇒ 此后**平台随便增删改，你的人工文件一个字节都不会变**。

**三个常见误区**：

- ❌ **想把 Prometheus 的规则"同步"到平台，却点了「同步规则」** —— 方向反了，那是**下发**，
  而且会把同名的人工文件覆盖掉。**拉回来要用「同步 Prom」**。
- ❌ **在平台上删一条测试规则** —— 会**自动全量重写**下发文件；若人工规则恰好同名，就一起没了。
- ❌ **手工去改 `devops_rules.yml`** —— 下一次平台上的任何规则操作都会把它覆盖回去。

---

**相关文档**：从零部署 → [`DEPLOY.md`](DEPLOY.md)（§9 日常运维、附录 B 监控栈）｜
变更记录 → [`CHANGELOG.md`](CHANGELOG.md)｜架构 → [`DEPLOY-ARCHITECTURE.md`](DEPLOY-ARCHITECTURE.md)
