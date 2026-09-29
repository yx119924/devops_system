# XwOps · 已上线环境增量更新手册

> - **从零部署** → [`DEPLOY.md`](DEPLOY.md)
> - **本手册** → 环境**已经跑起来**之后，要打一次「只改代码、不动数据」的更新时看这份
> - 全文以 **2026-09-29「告警规则双源共存 + 首页卡片修正」** 这一批改动为实例写，可以照着敲

**占位符约定**（按你环境替换，本文不写真实值）：

| 占位符 | 含义 | 备注 |
|---|---|---|
| `<部署目录>` | 目标机上仓库的位置 | 例：`~/xwops` |
| `<内网IP>` | 目标机的内网地址 | 例：`192.0.2.163` |
| `<Prom规则目录>` | Prometheus `rule_files` 指向的目录 | 例：`/opt/prometheus/rules`（Prom **主机部署**时是宿主机路径） |
| `<AM配置目录>` | Alertmanager 配置所在目录 | 例：`/opt/alertmanager` |

---

## 0. 先判断：你该走哪条通道

更新只有两件麻烦事 —— **代码怎么进目标机** 和 **前端产物怎么进目标机**。先跑 3 条命令定方向：

```bash
# ① 目标机能不能直连 GitHub？
git -C <部署目录> ls-remote origin HEAD        # 通 → 通道 A；报 GnuTLS/timed out → 通道 B/C

# ② 有没有一台「能上外网 + 装了 docker」的机器？（构建前端镜像用）
docker version                                   # 该机执行

# ③ 本批有没有改 web/ ？
git -C <部署目录> diff --name-only <旧提交> <新提交> -- web/
```

决策表：

| 情况 | 走哪条通道 | 前端怎么办 |
|---|---|---|
| ①通 | **通道 A**（`git pull`） | 外网机重建镜像 → save → load（§4 办法 1） |
| ①不通，有外网机 | **通道 B**（离线包 + scp） | 同上（外网机顺手构建） |
| ①不通，没外网 docker 机 | 通道 B + 应急 | **§4 办法 2**（只换 `dist`，不重建镜像） |
| 想长期省事 | **通道 C**（给目标机配 SSH key） | —— |

> ★ **本批改动了 4 个 `web/src/**` 文件 ⇒ 前端必须重建**，这一步绕不过去。

---

## 1. 本批改动清单（15 个文件 → 4 类动作）

| 类别 | 文件 | 需要的动作 |
|---|---|---|
| **后端源码** | `backend/dvadmin/alert/models.py`<br>`backend/dvadmin/alert/services.py`<br>`backend/dvadmin/alert/views/rule.py`<br>`backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py` | 拷进 `<部署目录>/backend/` → **跑迁移** → 重启 django + celery |
| **前端源码** | `web/src/views/alert/rule/crud.tsx`<br>`web/src/views/alert/rule/index.vue`<br>`web/src/views/alert/manage/index.vue`<br>`web/src/views/system/home/index.vue` | **必须重建 web 镜像**（§4） |
| **参考配置** | `docker_env/alertmanager/alertmanager.yml`<br>`backend/conf/env.example.py` | **不动线上**。前者是 AM 配置的**样例与注释说明**，线上 AM 请按 §2 第 6 步手工改 |
| **工程杂项** | `.gitignore`、`DEPLOY.md`、`CHANGELOG.md` | 无动作（`.gitignore` 只影响下次提交） |
| **运行时产物** | `backend/dvadmin/alert/rules/devops_rules.yml`（**删除跟踪**）<br>`backend/dvadmin/alert/rules/.gitkeep`（**新增**） | **无动作**。磁盘上的规则文件保持原样，平台照常读写 |

> ★ 本批**没有**改 `requirements.txt` ⇒ **django / celery 镜像不用重建**，只重启容器即可。

---

## 2. 标准执行顺序（照抄，8 步）

### 第 0 步 · 备份（唯一的安全网，不能跳）

```bash
cd <部署目录>
docker exec dvadmin3-mysql sh -c \
  'mysqldump -h127.0.0.1 --protocol=TCP -uroot -p"$MYSQL_ROOT_PASSWORD" \
   --single-transaction --routines --triggers django-vue3-admin' \
  > backup_$(date +%F_%H%M).sql
ls -l backup_*.sql          # 确认文件非 0 字节
```

### 第 1 步 · 取代码

见 §3 通道 A / B / C。**取完先核对版本**：

```bash
git -C <部署目录> log --oneline -1
# 本批期望：5bfc62d feat(alert): 规则双源共存(source/labels) + 下发回读校验；修首页卡片跳转；…
```

### 第 2 步 · 后端源码就位（`.py` 是挂载的，拷进去即生效）

走通道 A（`git pull`）的话本步**已经完成**，跳过。走通道 B 手工拷的话：

```bash
cd <部署目录>
# 只覆盖这几个文件，别整目录覆盖（目标机上可能有本地改动）
cp -v <补丁包>/backend/dvadmin/alert/models.py            backend/dvadmin/alert/
cp -v <补丁包>/backend/dvadmin/alert/services.py          backend/dvadmin/alert/
cp -v <补丁包>/backend/dvadmin/alert/views/rule.py        backend/dvadmin/alert/views/
cp -v <补丁包>/backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py \
      backend/dvadmin/alert/migrations/

python3 -m py_compile backend/dvadmin/alert/models.py \
                      backend/dvadmin/alert/services.py \
                      backend/dvadmin/alert/views/rule.py \
                      backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py \
  && echo "语法 OK"
```

### 第 3 步 · 数据库迁移（★ 本批必做）

```bash
# 先看会执行什么，只读，不改库
docker exec dvadmin3-django python manage.py showmigrations alert

# 执行
docker exec dvadmin3-django python manage.py migrate alert
```

期望输出包含：

```
Applying alert.0007_alertrule_source_labels... OK
```

**验证迁移真的生效了**（别只看 `OK`）：

```bash
docker exec dvadmin3-django python manage.py shell -c "
from dvadmin.alert.models import AlertRule
vals = set(AlertRule.objects.values_list('source', flat=True))
print('source 取值集合:', vals)          # 期望 {'prom'}（存量规则全被标为 prom）
print('总规则数:', AlertRule.objects.count())
"
```

> ★ 为什么存量规则要标成 `prom`：这批改动引入「**双源共存**」——
> `source=platform` 的规则会被平台下发到 Prometheus，`source=prom` 的规则只做纳管展示、**不下发**。
> 升级前的规则全都只存在于 Prometheus 侧，若不明文标成 `prom`，升级后第一次点「同步规则」
> 会把它们**再下发一遍**，与 Prometheus 原有规则**重复触发**。迁移里的 `RunPython` 就是干这个的。

### 第 4 步 · 前端（必须重建镜像，内网不能就地构建）

完整步骤见 **§4**。最小路径（在内网目标机上执行）：

```bash
cd <部署目录>
cd docker && md5sum -c checksums.txt && cd ..     # 校验刚拷进来的镜像包
docker load -i docker/xwops-web-1.0.0.tar         # 同 tag 覆盖旧镜像
docker compose up -d --no-build dvadmin3-web
```

> ★ 一定要 `--no-build`：`docker-compose.yml` 里 `image:` 与 `build:` 是**并存**的，
> 不加这个参数会把「容器起来」和「是否又触发了一次（内网必然失败的）构建」混在一起，事后说不清跑的是哪个版本。

### 第 5 步 · 打通规则投递（★ 本批新增，不配的话「同步规则」会明确报错）

平台写规则文件写在**自己容器里**，而 Prometheus 读的是**宿主机**目录。两者同机，所以**一行 bind mount** 解决：

```bash
cd <部署目录>
cat > docker-compose.override.yml <<'YAML'
# 本机专用（已 gitignore）：把 Prometheus 的规则目录直接挂进后端容器
services:
  dvadmin3-django:
    volumes:
      - /opt/prometheus/rules:/backend/dvadmin/alert/rules
  dvadmin3-celery:
    volumes:
      - /opt/prometheus/rules:/backend/dvadmin/alert/rules
YAML
```

> ★ 把 `/opt/prometheus/rules` 换成你环境里 **Prometheus `rule_files` 真正指向的目录**。
> ★ compose 对 `volumes` 是**追加合并**：原来的 `./backend:/backend` 仍在，新增的这条**更深**，
> 容器内 `/backend/dvadmin/alert/rules` 由它接管 —— 所以**不用改 `RULES_DIR`，不用改一行代码**。

生效并验证**挂载真的进去了**：

```bash
docker compose up -d --no-build dvadmin3-django dvadmin3-celery

docker inspect dvadmin3-django --format '{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' \
  | grep alert/rules
# 期望输出：/backend/dvadmin/alert/rules
```

再验「容器里写的，宿主机看得到」（这是**唯一**能证明投递链路通了的判据）：

```bash
docker exec dvadmin3-django sh -c \
  'echo probe > /backend/dvadmin/alert/rules/.write_probe && ls -l /backend/dvadmin/alert/rules/.write_probe'
ls -l /opt/prometheus/rules/.write_probe          # 宿主机必须也能看到这个文件
rm -f /opt/prometheus/rules/.write_probe
```

> `.write_probe` 不以 `.yml` 结尾，不会被 Prometheus 的 glob 解析到，可安全创建删除。

### 第 6 步 · Alertmanager 侧（**手工**，两个小改动）

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

改完重载并确认生效：

```bash
curl -s -X POST http://<内网IP>:9093/-/reload -o /dev/null -w 'HTTP=%{http_code}\n'   # 期望 200
# 若 AM 未开 --web.enable-lifecycle，则用：
# docker restart <am容器>  /  systemctl restart alertmanager
```

### 第 7 步 · 回归验收

见 **§5**，逐项打勾再收工。

---

## 3. 通道详解：代码怎么进目标机

### 通道 A · 目标机能直连 GitHub（最省事）

```bash
cd <部署目录>
git fetch origin && git status          # 先看有没有本地改动没提交，有就先 stash
git pull --ff-only origin main
```

### 通道 B · 目标机不能上网（离线包）★ 最常见

目标机连不上 `github.com:443`（报 `GnuTLS recv error (-110)` 之类）时用这条。
本批改动总共 **15 个文件**（1 个新增迁移、1 个新增 `.gitkeep`、1 个删除跟踪），用补丁包最小：

```bash
# —— 在一台能访问 GitHub 的机器上 ——
git clone --depth 1 https://github.com/yx119924/devops_system.git
cd devops_system
git format-patch -1 HEAD -o ../patch/           # 产出 0001-*.patch
tar czf xwops_update_20260929.tar.gz -C ../patch .
```

把 `xwops_update_20260929.tar.gz` 拷到目标机（scp / U 盘 / 跳板机都行），然后：

```bash
cd <部署目录>
tar xzf /tmp/xwops_update_20260929.tar.gz -C /tmp/xwops_update/

# ★ 先干跑一次，看它到底会改哪些文件（不改工作区）
git apply --check /tmp/xwops_update/0001-*.patch && echo "可以干净应用"

# ★ 应用前先备份当前工作区差异（万一要回退）
git diff > /tmp/xwops_before_backup.patch

git apply /tmp/xwops_update/0001-*.patch
git status --short          # 应看到 15 个文件发生变化
```

**核对改对了** —— 本批 8 个关键文件的 md5，对不上就是没拷全：

```bash
md5sum backend/dvadmin/alert/models.py \
       backend/dvadmin/alert/services.py \
       backend/dvadmin/alert/views/rule.py \
       backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py \
       web/src/views/alert/rule/crud.tsx \
       web/src/views/alert/rule/index.vue \
       web/src/views/alert/manage/index.vue \
       web/src/views/system/home/index.vue
```

期望输出（前 4 个是后端，后 4 个是前端）：

```
758188633cc2c781ff0e68c5af8a884e  backend/dvadmin/alert/models.py
f769c01f6293c956dc5bce5a0b610b8d  backend/dvadmin/alert/services.py
59c9b5b8e7a41b5978fcbd997073218f  backend/dvadmin/alert/views/rule.py
7d2700f10b14e4c73bd6336a7a721ee3  backend/dvadmin/alert/migrations/0007_alertrule_source_labels.py
415363a6a5421d657ab2b1c32614dd75  web/src/views/alert/rule/crud.tsx
2cef6f29a1c2c014f5be7fcbcbb0e6ed  web/src/views/alert/rule/index.vue
9c25c3010ac155b3904cbe0933f73308  web/src/views/alert/manage/index.vue
a0a417ea40b9f2030aa40306cd37d466  web/src/views/system/home/index.vue
```

> ★ `md5sum` 默认输出是 `<md5>␠␠<文件>`（两个空格），上面按这个格式列的；
> 若你的 `md5sum` 输出带 `*` 前缀（如 `758188…  *models.py`），是 binary 模式标记，比对时忽略即可。

> ★ 若 `git apply` 报冲突（目标机上有本地改动），用 `git apply --reject` 看 `.rej` 文件，
> 按 §2 第 2 步逐文件手工拷，手工拷反而更可控。

### 通道 C · 一劳永逸：给目标机配一条能用的拉取通道

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

---

## 4. 前端产物怎么进目标机

### 办法 1 · 重建镜像 + save / load（**推荐**）

在**能上外网 + 有 docker** 的机器上（`docker_env/web/Dockerfile` 里的 `npm install` 需要外网）：

```bash
cd <仓库根目录>
docker build -f docker_env/web/Dockerfile -t xwops/web:1.0.0 .

# ★ 上线前先看产物，别急着打包
docker run --rm --entrypoint sh xwops/web:1.0.0 -c \
  'ls -la /usr/share/nginx/html && grep -o "<title>[^<]*</title>" /usr/share/nginx/html/index.html'

# 只打包 web 一个镜像
bash docker/save-images.sh --web-only        # 产出 docker/xwops-web-1.0.0.tar + checksums.txt
```

把 `docker/xwops-web-1.0.0.tar` 和 `checksums.txt` 拷到目标机，然后按 §2 第 4 步 `docker load` + `up -d --no-build`。

> ★ **沿用同一个 tag `xwops/web:1.0.0`**：`docker-compose.yml` 一个字都不用改，少一个出错点。
> 若确实换 tag，**必须同步改 `docker-compose.yml` 的 `image:` 行**，否则表现是「load 了新镜像，页面还是老的」。

### 办法 2 · 只替换 `dist`，不重建镜像（**应急 / 没有外网 docker 机时**）

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
cat >> docker-compose.override.yml <<'YAML'
  dvadmin3-web:
    volumes:
      - ./_dist_20260929:/usr/share/nginx/html
YAML

docker compose up -d --no-build dvadmin3-web
```

> ⚠️ `docker-compose.override.yml` 里 service 名**不要重复出现**。若第 5 步已经建过这个文件，
> 把 `dvadmin3-web:` 这一段**手工粘到同一个文件里**（与 `dvadmin3-django` 平级），别写两个 `services:` 键。
>
> ⚠️ 办法 2 的**回滚**最快：删掉那行挂载 → `docker compose up -d --no-build dvadmin3-web`，立刻回到镜像里的旧版。
> 但它是**运行时挂载**，下次别人 `docker compose up -d`（无 override）就会「无声回退」—— 只适合应急，别当长期方案。

---

## 5. 回归验收清单（逐项打勾）

### 5.1 服务层

```bash
docker compose ps                       # 5 个容器 Up
curl -s -o /dev/null -w 'home=%{http_code}\n' http://127.0.0.1:8080/          # 200
curl -s -o /dev/null -w 'api=%{http_code}\n'  http://127.0.0.1:8080/api/api/   # ★ 双层 /api
```

> ★ 前端只改一个 `.vue` 也可能因构建报错产出空 `dist`，届时 8080 会 404 或空白页 ——
> **只看「容器 Up」判断不出问题**，必须走 8080 复验。

### 5.2 功能层（浏览器里点）

| # | 检查项 | 期望 |
|---|---|---|
| 1 | 首页「活跃告警」卡 | 点击跳到 **`/alertManage`（活跃告警菜单）**，不再跳历史告警 |
| 2 | 首页卡片（原「严重告警(周)」） | 卡片名已变 **「历史告警」**，点击跳 `/alertEvent` |
| 3 | 首页卡片权限 | 无告警菜单权限的账号看到的是**占位卡**，不误跳 |
| 4 | 告警规则页 | 列表新增 **「来源」** 与 **「附加标签」** 两列；来源可选「平台（下发）」/「Prom 纳管」 |
| 5 | 告警规则 → 编辑 → 附加标签填非 JSON | 表单**当场报错**拦截（不会带着脏数据提交） |
| 6 | 「附加标签」留空提交 | 落库为 `{}`，不报错 |
| 7 | 活跃告警 → 详情弹窗 | 新增 **「指纹」** 一行 |
| 8 | 点「同步规则」（**未做 §2 第 5 步时**） | 明确报错说读不到规则 —— ★ **这是本批的预期行为，不是新 bug** |
| 9 | 点「同步规则」（**做完 §2 第 5 步后**） | 提示「已下发并确认生效」 |
| 10 | 「同步 Prom」拉进来的规则 | 「来源」列显示 **Prom 纳管** |
| 11 | 平台新建规则 → 同步规则 → 回读 | `curl -s http://<内网IP>:9090/api/v1/rules \| grep '"name":"<你的规则名>"'` 有输出 |

### 5.3 链路层（可选，但强烈建议做一次）

在平台上新建一条**必然触发**的规则（如 `up == 0`），确认：

```
Prometheus → Alertmanager → 平台 webhook(202) → Celery → 告警事件页出现记录 → 通知渠道收到
```

---

## 6. 本批的预期行为变化（**别当成新 bug**）

| 现象 | 为什么 | 怎么办 |
|---|---|---|
| 升级后第一次点「同步规则」，**存量规则没被下发** | 迁移把存量规则标成了 `prom`（只纳管不下发），这是**防双发**的设计 | 正常。要让平台接管某条，把它的「来源」改成「平台」 |
| 点「同步规则」**直接报错**，说读不到 N 条规则 | 回读校验发现 Prometheus 里没读到 —— 说明投递没打通 | 做 §2 第 5 步（bind mount） |
| 平台规则触发了但**收不到告警** | 平台规则 labels 只有 `severity`，命中不了 AM 里 `match: {team: ops}` 的路由 | 做 §2 第 6 步 |
| 「活跃告警」里同一个任务名出现 19 行 | 规则是 `sum by (process_name) ... > 0` ⇒ **每个不同 `process_name` 一条独立序列**，Alertmanager 按标签指纹去重，标签不同就是不同告警 | 正常。详情弹窗新增的「指纹」行可以自证：指纹不同 = 两条独立告警 |
| `backend/dvadmin/alert/rules/devops_rules.yml` 在 `git status` 里显示为已删除跟踪 | 该文件是**程序生成的运行时产物**，已移出版本控制（磁盘上还在） | 正常。别再 `git add` 它 |

---

## 7. 回滚

**后端**（最快）：把 §2 第 2 步拷进去的 4 个文件换回旧版，`docker compose restart dvadmin3-django dvadmin3-celery`。

**前端**：换回旧镜像（`docker load` 上一版 tar）或删掉 §4 办法 2 的挂载，然后 `up -d --no-build dvadmin3-web`。

**数据库**：`0007` 只做 `AddField` + 一次 `UPDATE`，可安全 `migrate alert 0006` 回退结构，
但**回退前请先想清楚**：`source`/`labels` 两列一旦被删，页面会立刻报错（前端已引用），
所以**正常情况下不要回退迁移**，只回滚代码。

**整体回退**：从 §2 第 0 步的备份恢复：

```bash
docker exec -i dvadmin3-mysql sh -c \
  'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" django-vue3-admin' < backup_<时间戳>.sql
```

> ⚠️ 恢复必须用**同一个** `CREDENTIAL_ENCRYPTION_KEY`，否则已加密的渠道密钥解不开。

---

## 8. 一张表记住「改什么 → 做什么」

| 你改了 | 要重建镜像吗 | 生效方式 |
|---|---|---|
| `backend/**` 的 `.py` | **不用** | `docker compose restart dvadmin3-django dvadmin3-celery` |
| `backend/dvadmin/*/migrations/**` | 不用 | 加一步 `manage.py migrate` |
| `backend/requirements.txt` | **要**（django + celery **两个**） | 重建 → save → load → `up -d --no-build` |
| `web/src/**`、`web/package.json` | **要**（web 一个） | 同上；内网不能就地构建，见 §4 |
| `docker_env/nginx/my.conf` | 不用 | `docker exec dvadmin3-web nginx -s reload`（★ 不 reload 不生效） |
| `docker-compose.yml` / `.env` / `backend/conf/env.py` | 不用 | `docker compose up -d --no-build`（重建容器才读到新值） |
| `docker_env/alertmanager/alertmanager.yml` | 不用 | 它是**样例**；线上 AM 手工改 + `POST /-/reload` |

---

**相关文档**：从零部署 → [`DEPLOY.md`](DEPLOY.md)（§9 日常运维、附录 B 监控栈）｜变更记录 → [`CHANGELOG.md`](CHANGELOG.md)｜架构 → [`DEPLOY-ARCHITECTURE.md`](DEPLOY-ARCHITECTURE.md)
