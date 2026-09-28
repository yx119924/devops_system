# 产品架构说明

> 配套文档：[`README.md`](README.md)（项目总览）、[`DEPLOY-ARCHITECTURE.md`](DEPLOY-ARCHITECTURE.md)（部署架构）

---

## 一、模块全景

平台在 DVAdmin 的「系统管理」底座之上，叠加 7 个自研模块：

| 模块 | 后端 app | 核心能力 | 关键数据模型 |
|---|---|---|---|
| **CMDB** | `dvadmin.cmdb` | 机房 / 环境 / 业务线 / 服务器资产管理；Excel 批量导入；命令下发入口 | `Idc` `Environment` `BusinessLine` `Server` |
| **堡垒机** | `dvadmin.bastion` | Web SSH 终端、会话录像、命令审计、批量命令下发 | `Credential` `Session` `CommandLog` |
| **监控** | `dvadmin.monitor` | Prometheus 数据源接入、指标即时查询、Grafana 大屏嵌入 | `MonitorSource` |
| **告警** | `dvadmin.alert` | 规则 / 通知渠道 / 告警组 / 告警事件 / 模板；Webhook 接收 | `AlertRule` `NotifyChannel` `AlertGroup` |
| **日志** | `dvadmin.log` | 日志源管理、filebeat 采集配置生成与下发、日志检索 | `LogSource` `LogCollectTask` `LogCollectRecord` |
| **发布** | `dvadmin.jenkins` | Jenkins 服务器接入、Job 目录树、构建发布、Job 级可见性授权 | `JenkinsServer` `JenkinsJob` `JenkinsRolePermission` |
| **AI 运维助手** | `dvadmin.aiagent` | 多供应商模型配置（BYOK）、智能问答、工具调用 | `AiProviderConfig` `AiChatSession` `AiToolCall` `AiUsage` |

外加 DVAdmin 原生的**系统管理**：用户 / 角色 / 菜单 / 按钮权限 / 部门 / 字典 / 系统配置 / 登录日志 / 操作日志 / 定时任务。

---

## 二、请求链路

```
浏览器 /api/api/cmdb/server/
   │
   ▼ nginx（容器 :8080）
   │  rewrite ^/api/(.*)$ /$1 break;     ← 剥掉一层 /api
   ▼
django（容器 :8000）/api/cmdb/server/
   │
   ├─ 认证：JWT（Authorization: JWT <access>）
   ├─ 权限：CustomPermission → 菜单 + 按钮权限双重校验
   ├─ 数据过滤：DataLevelPermissionsFilter（按部门归属）
   └─ 视图：CustomModelViewSet
```

**为什么是双层 `/api`？**

前端所有请求统一走 `/api` 前缀（Vite `VITE_API_URL = '/api'`），而 Django 侧的路由
本身就带 `api/`（`path("api/cmdb/", ...)`）。nginx 用一个 `rewrite` 把前端多发的那层
剥掉，两边各改各的、互不干扰。

> ⚠️ 直接调试时注意：**打单层 `/api/xxx` 恒 404**，必须打双层 `/api/api/xxx`。
> 这是设计如此，不是故障。

---

## 三、权限模型（三层）

| 层 | 机制 | 说明 |
|---|---|---|
| **1. 菜单权限** | `RoleMenuPermission` | 控制角色能看到哪些菜单 |
| **2. 按钮权限** | `RoleMenuButtonPermission` | 按 **API 路径 + HTTP 方法**逐条匹配，控制能否调用某个接口 |
| **3. 数据权限** | `DataLevelPermissionsFilter` | 按 `dept_belong_id` 过滤数据行，控制能看到哪些数据 |

### 按钮权限的三个关键约束（踩坑最集中的地方）

1. **自定义 `@action` 必须逐条登记 MenuButton**
   权限校验是拿请求的 `(api 路径, method 下标)` 去逐条 `re.match(api 模板)`。
   少登记一个 action，对应功能就对所有人不可用。

2. **`is_superuser` 不作数**
   超管身份并不能绕过按钮权限校验。只建菜单不授
   `RoleMenuButtonPermission`，超管也会「按钮全没了」。

3. **component 必须先有页面文件**
   菜单里配的 `component` 路径若在 `web/src/views/` 下不存在，页面打不开。

### 个人私有数据必须解除数据权限过滤

`DataLevelPermissionsFilter` 会按部门归属过滤数据。对于**个人私有数据**
（如 AI 的 BYOK 密钥配置），必须显式关闭该过滤器：

```python
extra_filter_class = []      # 关闭数据权限过滤，改由 owner 字段做隔离
```

否则会出现「A 部门用户配了自己的 API Key，B 部门用户看不到任何配置」这类问题。
先例见 `backend/dvadmin/cmdb/views/server_grant.py`。

---

## 四、关键设计取舍

### 4.1 AI 运维助手：BYOK + 四道安全闸

| 决策 | 内容 | 理由 |
|---|---|---|
| **Key 归属** | 个人私有（BYOK），按 `owner` 隔离 | 平台不承担统一 Key 的成本与滥用风险 |
| **权限口径** | 复用 CMDB 的资产授权 | 能操作哪台机器，AI 就能操作哪台，口径一致 |
| **数据外发** | 自动脱敏后再截断 | 敏感信息（密码、密钥）不能进大模型请求 |
| **工具执行** | 四道闸：开关闸 → 命令闸 → 授权闸 → 脱敏闸 | 被拒也写台账，可审计 |

「四道闸」的具体含义（见 `aiagent/tools.py`）：

1. **开关闸** —— `enabled_tools` + `readonly_mode`，未启用的工具直接拒绝
2. **命令闸** —— 白名单按 `;` / `&&` / `||` / `|` **逐段校验**，元字符全拦
3. **授权闸** —— `require_access(..., 'dispatch')` 复用 CMDB 授权
4. **脱敏闸** —— **先脱敏再截断**（顺序反了会漏）

工具接口**只收 `server_id`，不收裸 IP**，避免绕过资产授权直接连任意主机。

### 4.2 前后端更新方式不对称

| | 前端 | 后端 |
|---|---|---|
| 打包方式 | `npm run build` 产物 COPY 进 nginx 镜像 | 镜像里只有依赖 |
| 代码来源 | **镜像内** | 宿主机 `./backend` **挂载** |
| 改代码后 | 必须重建镜像 | 重启容器即可 |

这不是设计疏漏，而是取舍：前端构建重（node 环境 + 几分钟），
放镜像里一次构建到处运行；后端迭代快，挂载后改完即生效。

### 4.3 命令下发的安全边界

- 引擎：`paramiko` + `ThreadPoolExecutor` 批量 SSH
- 凭证：**任务级统一凭证**（不是每台机器一套）
- 目标：CMDB 多选 + 手动 IP 兜底
- 审批：RBAC + 审计，不额外走审批流
- 执行模式：**同步**（不依赖 Celery；这也意味着 celery 容器缺依赖不影响下发）

### 4.4 其它工程约定

| 约定 | 原因 |
|---|---|
| `USE_TZ = False` | 全链路用本地时间；**代价是不能对 naive datetime 调 `localtime()`**，否则直接抛异常 |
| 更新接口是**全量**而非 partial | `PUT` 缺字段会报「必填项」，且**不会进入 `validate()`** |
| 按钮权限必须逐条登记 | 见第三节 |
| `dept` 是真实外键（PROTECT），`role` / `manage_dept` / `current_role` 是 `db_constraint=False` | 只有 `dept` 需要担心悬空引用；`init/01_seed_config.sql` 末尾已做修复 |

---

## 五、初始化数据的构成

`init/01_seed_config.sql` 是从运行环境导出的**配置类数据**（不含业务数据与用户）：

| 表 | 条数 | 内容 |
|---|---|---|
| `dvadmin_system_menu` | 51 | 全部菜单（含 7 个自研模块） |
| `dvadmin_system_menu_button` | 207 | 按钮权限定义 |
| `dvadmin_role_menu_permission` | 196 | 角色-菜单授权 |
| `dvadmin_role_menu_button_permission` | 667 | 角色-按钮授权 |
| `dvadmin_system_menu_field` | 132 | 列表字段配置 |
| `dvadmin_system_role` | 7 | 角色 |
| `dvadmin_system_dept` | 4 | 部门 |
| `dvadmin_system_dictionary` | 49 | 字典 |
| `dvadmin_system_config` | 29 | 系统配置 |
| `dvadmin_api_white_list` | 1 | 免认证接口白名单 |

导入后平台即有完整的菜单与权限骨架；用户与业务数据需自行创建。

---

## 六、如何扩展一个新模块

1. 在 `backend/dvadmin/` 下新建 app（如 `foo`）
2. 写 `models.py` / `serializers.py` / `views.py` / `urls.py`
3. 在 `application/settings.py` 的 `INSTALLED_APPS` 注册 `"dvadmin.foo"`
4. 在 `application/urls.py` 注册 `path("api/foo/", include("dvadmin.foo.urls"))`
5. `makemigrations foo && migrate`
6. 在 `web/src/views/foo/` 下写好页面组件
7. **注册菜单与按钮权限** —— 参考 `backend/register_log_collect.py` 的写法：
   建菜单 → 把**每一个** `@action` 登记成 MenuButton → 按角色授权

> 第 7 步是新手最容易漏的：页面能打开但接口全 403，原因通常是某个自定义
> `@action` 没登记 MenuButton。
