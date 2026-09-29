# 更新日志

本仓库基于开源项目 [DVAdmin3](https://gitee.com/huge-dream/django-vue3-admin) 二次开发，
上游更新日志保留在文末。

---

## 未发布 —— 告警规则「双源共存」+ 下发回读校验（2026-09-29）

### 背景

内网真机联调暴露两个现象：

1. 在平台新建告警规则、点「同步规则」提示成功，但 Prometheus 里**始终没有**这条规则；
2. 平台生成的规则即使触发了，也**收不到告警**。

根因与完整排查见 `DEPLOY.md` 附录 B 第 4 条。本次改动修掉「假成功」与「静默丢失」两侧。

### 变更

| 改动 | 文件 | 说明 |
|---|---|---|
| 规则新增「来源」 | `backend/dvadmin/alert/models.py`（+ 迁移 `alert/0007_alertrule_source_labels`） | `platform`=平台新建（会下发）／`prom`=从 Prometheus 反向同步（只纳管、不下发）。**迁移会把存量规则一律标为 `prom`** ⇒ 升级后不会突然整份下发造成告警双发 |
| 规则新增「附加标签」 | 同上 | 一个 JSON 对象，合并进 Prometheus 规则的 `labels`（如 `{"team":"ops"}`）；`severity` 仍由「级别」字段生成，不允许被覆盖 |
| 只下发平台规则 | `services.py::generate_rules` | 原来「全量导出」，现在加 `source='platform'` 过滤 |
| 「同步 Prom」建档标记来源 | `services.py::sync_rules_from_prometheus` | 新建规则标 `source='prom'`；命中已存在的只更新表达式/持续时间/级别/摘要/描述，**不动 `source`** |
| 「同步规则」新增回读校验 | `services.py::verify_rules_loaded` + `views/rule.py::reload_rules` | reload 后回读 `{prom}/api/v1/rules`；读不到就**返回错误并列出规则名**，不再假报成功 |
| 前端两列 + 修正假成功提示 | `web/src/views/alert/rule/crud.tsx`、`index.vue` | 新增「来源」「附加标签」两列；「同步规则」改为**回显后端 msg**（原来写死 `规则已同步并热加载`） |
| 首页卡片跳转修正 + 活跃告警「指纹」 | `web/src/views/system/home/index.vue`、`web/src/views/alert/manage/index.vue` | ① 「**活跃告警**」卡片原来跳的是 `/alertEvent`（历史告警）→ 改为 `/alertManage`（活跃告警菜单）；② 「**严重告警(周)**」卡片改名为「**历史告警**」，数值口径同步换成近 7 天总数，避免「标题写历史告警、数字是本周严重数」的名实不符；③ 活跃告警「详情」新增 **Alertmanager 指纹**，用于判断多条看似相同的告警到底是不是同一条 |
| 运行时产物移出版本控制 | `.gitignore`（+ `backend/dvadmin/alert/rules/.gitkeep`） | `backend/dvadmin/alert/rules/*.yml` 是 `generate_rules()` 的**运行时产物**，每次「同步规则」整份覆盖，内容是本环境真实的规则名/job/阈值 —— 之前被提交进了公开仓库。现在改为忽略，只保留 `.gitkeep` 占位 |
| 新增**增量更新手册** | `UPDATE.md`（+ `README.md` / `DEPLOY.md` 索引） | 把「环境已跑起来后怎么打一次更新」写成可照抄的 runbook：① 按「目标机能不能上网」分三条代码通道（`git pull` / 离线补丁包 / 配 SSH key）；② 目标机不能就地构建前端时的两种交付（重建镜像 `save`/`load`、应急只换 `dist` + bind mount）；③ 规则投递的 compose override 写法与「容器内写→宿主机看」验证法；④ Alertmanager 两个手工改动；⑤ 回归验收清单与回滚。附 8 个关键文件的 md5 供对账 |
| `.gitignore` 补 `docker-compose.override.yml` | `.gitignore` | 该文件里写的是**本机才有的宿主路径**（如 Prometheus 规则目录），换个环境就不一样，不进版本控制 |

> ⚠️ `devops_rules.yml` 已从索引移除，但**它仍存在于 v1.0.0 的提交历史里**（公开仓库）。
> 若要彻底清除，需重写历史后强推（与之前 amend + force-push 的做法一致），
> 或至少在下一次 push 时用新提交覆盖。

### 升级注意

> ★ **逐条命令见 [`UPDATE.md`](UPDATE.md) · 增量更新手册**。下面只是要点。

- 需要执行 **1 次数据库迁移**：`python manage.py migrate alert`（新增 2 列 + 1 步数据迁移）。
- ★ 改了前端源码 ⇒ **必须重建 web 镜像**（本项目前端是编译进镜像的，不是挂载）。
- 后端 `.py` 改动需**重启** `dvadmin3-django` / `dvadmin3-celery`（uvicorn 未开 `--reload`）。
- 规则要真正进 Prometheus，仍需按 `DEPLOY.md` 附录 B 第 4 条选一条「共享目录 / 投递」方案；
  本版本只保证**不再假报成功**，不能替代那条数据通路。
- 平台规则要能被 Alertmanager 路由到，还需给规则加 `team` 附加标签（推荐 `{"team":"ops"}`）、
  并把 Alertmanager 的 `route.receiver` 指向平台的 receiver。

---

## XwOps v1.0.0（2026-09-28 首发 / 2026-09-29 重新发行）

首个对外交付版本。

> ⚠️ **v1.0.0 已于 2026-09-29 重新发行**：合入了「内网部署必需」的安全加固集，
> 并清理了上游模板残留。**若你手上是 09-28 那一版，请重新下载源码与镜像包。**
> 详细变更见下方「v1.0.0 重新发行说明」。

### 新增模块

1. **CMDB** —— 机房 / 环境 / 业务线 / 服务器资产管理，Excel 批量导入，命令下发入口
2. **堡垒机** —— Web SSH 终端、会话录像、命令审计、批量命令下发（CMDB 多选 + 手动 IP 兜底）
3. **监控** —— Prometheus 数据源接入、指标即时查询、Grafana 大屏嵌入
4. **告警** —— 告警规则 / 通知渠道（邮件·企微·飞书）/ 告警组 / 告警事件 / 模板，Webhook 接收
5. **日志** —— 日志源管理、filebeat 采集配置生成与下发、日志检索
6. **发布** —— Jenkins 服务器接入、Job 目录树、构建发布、按角色的 Job 可见性授权
7. **AI 运维助手** —— 多供应商模型配置（BYOK）、智能问答、工具调用（四道安全闸）

### 本版本交付物

| 交付物 | 说明 |
|---|---|
| 后端源码 | `backend/` |
| 前端源码 | `web/` |
| 成品镜像 | 5 个容器镜像，490 MB，通过 Releases 分发（见 `docker/README.md`） |
| 初始化数据 | `init/01_seed_config.sql` —— 菜单 49 / 按钮 207 / 授权 667 / 角色 7 / 字典 49 |
| 部署文档 | `DEPLOY.md`（唯一部署文档） |
| 架构说明 | `DEPLOY-ARCHITECTURE.md`、`PRODUCT-ARCHITECTURE.md` |

### 重要说明

- **代码已脱敏**：真实公网 IP、内网 IP、域名、密码、业务标识均以占位符替代，
  完整清单见 `DEPLOY.md` 附录 A。
- **不含业务数据与用户数据**：`init/01_seed_config.sql` 只包含配置类数据
  （菜单 / 角色 / 权限 / 字典 / 系统配置），无任何资产、会话、日志等业务数据。
- **镜像不含业务代码**：`django` / `celery` 镜像只有运行环境，
  业务代码通过 `./backend:/backend` 挂载，因此 `backend/` 源码是运行必需品。

---

## v1.0.0 重新发行说明（2026-09-29）

### 背景

首次发行时，本仓库的源码基线**取自线上运行版本**（「源码 ↔ 镜像 ↔ 实际跑起来的系统」三者一致、开箱可部署），
因此**不含**开发侧在 2026-09-17 那一轮做的安全加固集 —— 即存在「仓库 = 已修复但从未跑过；
线上 = 在跑但未修」的两条血脉问题。

重新发行时按「**内网部署必需**」的口径评估，把必需的部分合入了 v1.0.0，其余主动跳过。

### 已合入（内网必需集）

| 项 | 落点 |
|---|---|
| 通知渠道密钥加密 | 渠道 `config` 内敏感字段以 **Fernet 版本前缀**加密落库（`dvadmin/alert/secrets.py`） |
| 历史密钥迁移命令 | 新增 `python manage.py migrate_secrets`（**默认 dry-run**，`--apply` 才写；幂等，失败即整体回滚） |
| 模板渲染沙箱 | 告警模板改**受限 Jinja 沙箱** + 纯 JSON 上下文 + 16384 字符上限（`dvadmin/alert/rendering.py`） |
| Webhook 接收鉴权 | 必须带 `Authorization: Bearer <ALERT_WEBHOOK_SECRET>`，`hmac.compare_digest` 定长比较；密钥 <32 字符直接 **503** |
| 通知渠道配置下发 | 不再向前端回显密钥明文，改为下发 `has_*` 状态位 |
| 资产授权闸 | 命令下发前逐台 `require_access(..., 'dispatch')` |
| 审计归属 | 任务创建人按调用者落库（`creator_id = actor.pk`） |
| 会话录像鉴权 | 录像改走**带鉴权的 Blob 下载**，不再拼接裸链接 |
| 部署前体检命令 | 新增 `python manage.py security_preflight`（**只读**校验配置 / 表字段 / 接口挂载 / 运行时依赖） |
| 缓存 | `CACHES` 显式指向**共享 Redis**（票据与去重依赖） |

### 未合入（已评估后主动跳过）

| 项 | 跳过原因 |
|---|---|
| Web SSH 一次性票据整链 | 前端 Web SSH 未同步改造，贸然合入会导致终端打不开 |
| Grafana SSO | 本交付未接入 Grafana 单点登录 |
| known_hosts 强校验 | 保留 `AutoAddPolicy`；`bastion/ssh_client.py` 内已附「一行收紧」改法 |

### 额外保留（与加固集不同）

- **命令下发「手动 IP」兜底**：加固集倾向移除，本版**保留**（内网应急场景需要）。

### 一并修复的高危项

| 项 | 原状 | 现状 |
|---|---|---|
| Django 端口暴露 | `8000:8000` 绑全网卡；`DEBUG=True` 时 `/api/swagger.json` 免认证可下载 | 改为 `127.0.0.1:8000:8000`，仅本机可达 |
| `SECRET_KEY` | `settings.py` 内硬编码真实密钥 | 改为占位符，要求写在 `conf/env.py`（已 `.gitignore`） |
| 前端第三方统计 | `web/index.html` 内嵌第三方统计脚本（内网会向公网发请求） | 已移除 |
| 通知渠道密钥 | 明文落库 | Fernet 加密（见上表） |

### 上游模板残留清理

对**编译产物**做全量外部域名扫描后，发现 5 处上游 [vue-next-admin](https://gitee.com/lyt-top/vue-next-admin) 模板残留。
它们在**内网（无外网）**环境下会裂图、或把用户引向无关第三方：

| # | 位置 | 原内容 | 现内容 |
|---|---|---|---|
| 1 | `web/src/layout/lockScreen/index.vue` | 锁屏头像指向 `img2.baidu.com` | 改为平台自带 `logo-mini.svg` |
| 2 | 同上 | 锁屏背景（CSS）指向 `img-blog.csdnimg.cn` | 改为平台自带 `login-bg.png` |
| 3 | `web/src/views/system/error/401.vue` | 401 插图指向 `img-blog.csdnimg.cn`（带图床水印参数） | 改为平台自带 `login-main.svg` |
| 4 | `web/src/views/system/login/component/scan.vue` | 扫码登录二维码内容为 `jq.qq.com`（**上游作者 QQ 群**） | 改为平台自身地址 |
| 5 | `web/index.html` | meta `keywords`/`description` 为 `django-vue3-admin` | 改为 XwOps 描述 |

> 说明：`@iconify/vue`、`jsoneditor` 等第三方依赖内仍含少量外部域名**字符串**，
> 但经核查图标已由本地 `e-icon-picker` 图标库提供、运行时不会发起请求，判定为库噪声，未处理。

### 现场部署修复（2026-09-29 内网从零部署实测）

**v1.0.0 重新发行后，在内网主机从零部署时暴露 1 个 P0：所有 POST/PUT/DELETE 请求全部 500，登录接口直接不可用。**

| 项 | 内容 |
|---|---|
| 受影响文件 | `backend/dvadmin/bastion/redaction.py`（本版新增的加固文件） |
| 触发条件 | `API_LOG_ENABLE = True`（本版默认开启）+ 任何写请求 |
| 根因 | `pre_save` 信号里用 `hasattr(instance, 'request_path')` 当"有值"判断 —— 而 **Django 模型实例的字段属性永远存在，值为 `None`**，`hasattr` 恒真 ⇒ `None.split('?', 1)[0]` 抛 `AttributeError`。该信号 `weak=False` 且**无 sender 过滤、无 try/except**，异常直接让 `save()` 失败，请求返回 500 |
| 为何登录也中招 | `LoginView` 继承链 `TokenObtainPairView → TokenViewBase → GenericAPIView`，**`GenericAPIView` 有 `queryset` 类属性**，中间件 `process_view` 的 `hasattr(view_func.cls, 'queryset')` 判定为真 ⇒ 登录 POST 同样经过 `log.save()` |
| 修复 | 改为值判断：`path = getattr(instance, 'request_path', None)` + `if isinstance(path, str):` |
| 验证 | 离线直调该 `pre_save` 处理器 **13 条断言全绿**，含 `None` / `''` / 正常值 / 敏感字段仍被抹除；且带**对照组**（用修复前写法跑同一 `None` 用例，断言必须抛 `AttributeError`），证明修复必要且测试有效 |
| 部署影响 | 该文件属**后端**，走 `./backend:/backend` **挂载**，**镜像内不含业务代码** ⇒ **无需重建或重新加载镜像**，更新文件后 `docker restart dvadmin3-django dvadmin3-celery` 即生效 |

> ★ 为什么此前「后端 95 断言全绿」没拦住它：那些断言是**静态/文本级**的（源码比对 + 桩），
> 而这个缺陷只在**运行时**、且只在**某个字段恰好为 `NULL`** 时才会抛出。
> 教训已固化为部署门禁：**凡新增「全局生效」的代码（中间件 / `pre_save` / `post_save` / `AppConfig.ready`），
> 部署前必须单独跑一次「传入含 `None` 字段的最小模型实例」的直调验证**——
> 一个异常就等于全站不可用，它的健壮性要求高于普通业务代码。

### ★ 升级到本版的前置条件

1. **必须重建 / 替换 `xwops/web` 前端镜像** —— 前端已编译进镜像，且加固后后端不再下发渠道配置明细，
   沿用旧前端会导致**告警渠道页字段异常**。
2. **必须执行密钥迁移**：`python manage.py migrate_secrets`（先 dry-run 确认，再 `--apply`）。
3. **必须配置 `ALERT_WEBHOOK_SECRET`**（≥32 字符），否则 Webhook 接收端一律 503。
4. 建议部署后跑一次 `python manage.py security_preflight` 做体检。

### 验证状态（诚实标注）

| 范围 | 状态 |
|---|---|
| 后端（合入的加固集） | ✅ 离线验证：95 条断言全绿（桩 `exec(compile(...))` 真跑，非文本比对） |
| 前端（渠道页 / 命令下发 / 录像 / 模板残留） | ✅ 离线验证：50 条断言全绿（真 `@vue/compiler-sfc` 解析 + 真 `esbuild` 转换） |
| 前端镜像 | ✅ 已用本仓库源码重建并通过产物扫描（无外链、无统计埋点、无真实邮箱） |
| **真机联调** | ⚠️ 已在内网从零部署跑通建库/迁移/菜单导入，**暴露并修复 1 个 P0**（全站 POST 500，见上「现场部署修复」）；修复后登录链路**待目标机复验** |

---

## 上游 DVAdmin3 更新日志

### 正式发布 v3.0.0 版本

1. 新增：列权限管理与授权
2. 新增：代码新版本发布后，进行升级提醒
3. 优化：角色管理中按钮权限的操作
4. 优化：websocket 连接状态显示
5. 优化：初始化获取系统配置与字典配置，进行动态渲染登录页面
6. 修复：登录页面中系统配置不生效问题
7. 其他优化
