# XwOps 日志采集 · 使用手册

> **从目标机装 filebeat，到在平台上查到日志，全流程逐步说明。**
> 定位：照着做即可，所有命令都能直接复制。
>
> 适用：XwOps 的「**日志管理 → 采集配置**」功能（`/api/log/collect/`）。
> 平台侧依赖：`dvadmin.log` 模块。目标机侧依赖：filebeat（**平台不代装，需自行安装**）。

---

## 关于本手册

### 当前的采集模型（先记住这一句）

> **一个采集任务 = 一条日志路径 = 目标机上的一个 filebeat input。**

推论：

| 你有 | 就要建 |
|---|---|
| 1 个服务、1 份日志 | 1 个任务 |
| 1 台机上有 23 个服务目录，每个目录一份 `all.log` | **23 个任务**（每个任务挂全部 n 台主机） |
| 同一个服务要采两种格式的文件 | 2 个任务 |

**为什么不能一个任务填多条路径**：平台的「日志路径」是单值字段（`CharField(255)`），
白名单只允许 `字母数字 _ - . / * [ ]`，空格与花括号都会被后端拒绝。
多路径 / 一条 glob 覆盖多服务的方案**暂未实现**，需要时再单独设计。

### 这份文档解决什么问题

平台上点几下就能配采集，但**真正跑通它，有 8 道门要过**，而其中大部分门**平台不会提示你**。
本手册按实际操作顺序把 8 道门全部写出来，并给出每一步的**判断命令**。

### 三个必须先分清的概念

很多人第一次用会卡住，是因为把这三件事当成一件事：

| # | 是什么 | 由谁决定 | 平台管得了吗 |
|---|---|---|---|
| ① | 目标机上**有没有** filebeat | 你（手工安装） | ❌ 平台只检测，不代装 |
| ② | filebeat **该采哪些文件** | 平台下发的「配置片段」 | ✅ 平台负责写 |
| ③ | 日志最终**落到哪个 ES 索引** | 目标机 `filebeat.yml` 的 `output` | ❌ 平台**改不动** |

> ★ **最重要的一条**：`日志检索` 里看到的索引列表，是**实时去 ES 查真实存在的索引**。
> 所以「查不到」= ES 里真的没有，**不是页面没刷新**。而索引名**不是**你在平台上填的那个前缀——
> 前缀只是「检索时的通配模式」+ 随事件带下去的一个字段。

### 关于截图

本手册**不内嵌现成截图**——截图里必然带有内网 IP、主机名、账号名、真实索引名，
而本仓库是**公开仓库**，直接放进去等于对外披露你的内网信息。

替代方案是**逐条给出命令与期望输出**，并在每个需要目视确认的地方标出 `📷 截图位`。
**如果你要补充截图**，请按 [附录 B](#附录-b-截图清单) 放置，并**先遮挡内网 IP / 主机名 / 账号**。

### 阅读约定

| 标记 | 含义 |
|---|---|
| ★ | 容易踩的坑，务必看 |
| 📷 截图位 | 此处可补一张界面截图（自行截图并脱敏） |
| 命令块 | 可直接复制执行；`<>` 里的内容按你的环境替换 |

---

## 0. 五分钟心智模型

一条日志从目标机到能检索，要经过 **8 段**。任何一段断了，结果都是「ES 里什么都没有」：

```
① 目标机装 filebeat
        ↓
② 配 filebeat.yml（output 指向哪台 ES / 索引叫什么 / 从哪读采集指令）
        ↓
③ 服务跑起来（不是 crash-loop）
        ↓
④ ES 侧建保留策略 + 索引模板（决定字段类型与过期删除）
        ↓
⑤ 平台建任务（一条路径）→ 点「下发」→ 片段落到 /etc/filebeat/inputs.d/
        ↓
⑥ filebeat 热加载到片段（≤10s）→ harvester 启动
        ↓
⑦ 事件发到 ES → 按 output 的配置生成索引
        ↓
⑧ 检索页选索引模式 → 按 IP / 服务 / 时间 / 关键字查
```

**记住这张图**：排查时永远先问「**现在断在第几段**」，而不是东改一处西改一处。

---

## 1. 前置检查（开始前 2 分钟）

| 检查项 | 怎么确认 | 期望 |
|---|---|---|
| 目标机能 SSH 登录 | `ssh <账号>@192.0.2.30` | 通 |
| 目标机 SSH 端口 | `ss -lntp \| grep ssh` | 非 22 的话，后面 CMDB 里要填对 |
| 目标机发行版 | `cat /etc/os-release` | apt 系 / yum 系，决定第 2 步走哪种装法 |
| **有 root 权限的凭据** | `sudo -v` 或直接有 root 密码/私钥 | ★ **必须有**，见 [6.1](#61-凭据必须是-root为什么) |
| ES 地址与版本 | `curl -s http://<ES>:9200/` | 能返回 `cluster_name` / `version` |
| ES 磁盘余量 | `curl -s "http://<ES>:9200/_cat/allocation?v&h=node,disk.total,disk.used,disk.avail,disk.percent"` | 决定保留天数 |
| 平台的 ES 数据源已登记 | 平台 → 日志管理 → ES 数据源 | URL 填对、能「测试连接」通过 |

---

## 2. 第 1 步：目标机安装 filebeat

### 2.1 先探测能不能连 Elastic 的源

`filebeat` **不在 Ubuntu / CentOS 官方源里**，所以「配源」这一步**不能省**。
先探一句，决定走哪种装法：

```bash
curl -sI --max-time 8 https://artifacts.elastic.co/GPG-KEY-elasticsearch | head -1
```

| 结果 | 走哪种 |
|---|---|
| 返回 `HTTP/...` | **方式 A（在线加源）** |
| 超时 / 连不上 | **方式 B（离线 deb）** |
| 目标机本来就是 Docker 主机且不想装包 | **方式 C（容器跑 filebeat）**，但先看它的代价 |

> ★ 直接跑 `apt-get install -y filebeat` 会得到
> `E: Unable to locate package filebeat` —— 这不是包坏了，是**源里本来就没有**。

### 2.2 方式 A：在线加 Elastic 源（推荐）

```bash
sudo apt-get install -y apt-transport-https gnupg

curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch \
  | sudo gpg --dearmor -o /usr/share/keyrings/elastic.gpg

echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/7.x/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/elastic-7.x.list

sudo apt-get update
sudo apt-get install -y filebeat
```

yum 系（CentOS / RHEL / 麒麟）等价做法：

```bash
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch
sudo tee /etc/yum.repos.d/elastic-7.x.repo >/dev/null <<'EOF'
[elastic-7.x]
name=Elastic repository for 7.x packages
baseurl=https://artifacts.elastic.co/packages/7.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF
sudo yum install -y filebeat
```

### 2.3 方式 B：离线 deb / rpm（内网）

```bash
# 在有外网的机器上下载
curl -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.17.9-amd64.deb

# 传到目标机后安装
sudo dpkg -i filebeat-7.17.9-amd64.deb
```

rpm 系把 `.deb` 换成 `filebeat-7.17.9-x86_64.rpm`，用 `sudo rpm -ivh`。

### 2.4 方式 C：用容器跑 filebeat（有代价）

目标机本来就是 Docker 主机时可以不装包：

```bash
docker run -d --name filebeat --user root --restart unless-stopped \
  -v /etc/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro \
  -v /etc/filebeat/inputs.d:/usr/share/filebeat/inputs.d:ro \
  -v /opt/myapp/logs:/applogs:ro \
  docker.elastic.co/beats/filebeat:7.17.9 -e -strict.perms=false
```

> ★★ **两个代价，先想清楚再用**：
> 1. **平台会一直显示「未安装 filebeat」** —— 平台的「环境检测」是靠
>    `command -v filebeat` 和 `systemctl is-active filebeat` 判断的，容器方式这两个都查不到。
>    **功能本身仍可用**（片段目录挂进去就能读到），但**状态显示是失真的**。
> 2. **路径要写容器视角**：任务的「日志路径」得填容器里看到的路径（如 `/applogs/*.log`），
>    而不是宿主机路径。

### 2.5 版本：建议用 7.17.x

| 理由 | 说明 |
|---|---|
| 平台判据是 **≥ 7.9** | 7.17 ≥ 7.9，会使用 `filestream`（新式 input） |
| 7.x 不需要 ES 8 的安全配置 | ES 8 默认开 TLS + 账号密码，要多配一堆东西 |
| 平台的真机验证都在 7.17 上做过 | 兼容性最有把握 |

### 2.6 验证安装

```bash
filebeat version
# 期望：filebeat version 7.17.x (amd64), libbeat 7.17.x ...
```

**这一步过不去就不要往下走。**

---

## 3. 第 2 步：目标机配置 filebeat.yml

### 3.1 先建片段目录

平台会往这个目录写「配置片段」，**目录必须先存在**（平台只会 `mkdir -p`，权限不够会失败）：

```bash
sudo mkdir -p /etc/filebeat/inputs.d
```

### 3.2 改 `/etc/filebeat/filebeat.yml`

★ 改前先备份：`sudo cp -p /etc/filebeat/filebeat.yml /etc/filebeat/filebeat.yml.bak`

**完整模板（三处按你的环境改，其余照抄）：**

```yaml
# ── 1) 采集指令的来源：指向平台的片段目录 ─────────────────────────
# 实际配置写在这些片段里，平台负责下发；你不需要在这里写日志路径。
filebeat.inputs: []

filebeat.config.inputs:
  enabled: true
  path: /etc/filebeat/inputs.d/*.yml      # ← 与平台上任务里的「片段目录」一致
  reload.enabled: true                    # ★ 必开：改片段不用重启 filebeat
  reload.period: 10s

# ── 2) 日志往哪写 ──────────────────────────────────────────────
output.elasticsearch:
  hosts: ["http://192.0.2.163:9200"]      # ← 改成你的 ES
  index: "myapp-log-%{+yyyy.MM.dd}"       # ← 改成你的索引前缀

# ── 3) 自定义索引名时必须同时声明模板，否则 filebeat 拒绝启动 ──────
setup.template.name: "myapp-log"          # ← 与 index 的前缀一致（去掉 -%{+yyyy.MM.dd}）
setup.template.pattern: "myapp-log-*"

# ── 4) ★ 关掉 ILM，否则你的索引名不作数（见 3.3）─────────────────
setup.ilm.enabled: false
```

> ★ **模板名与前缀必须对得上**。filebeat 自带的索引模板叫 `filebeat-*`，你写到别的索引名下
> 模板就套不上，ES 只能**动态映射**去猜字段类型——猜错的后果是数据被拒或静默丢弃。
> 所以 filebeat 宁可**拒绝启动**，也不让你产出映射混乱的索引。

### 3.3 ILM：关掉它，否则你配的索引名不作数

filebeat 7.17 的 `setup.ilm.enabled` 默认是 **`auto`** —— 意思是「**ES 支持就自动启用**」。
而 ILM 一旦启用：

> filebeat 会用它**自己的滚动别名**来创建和命名索引，
> **你写在 `output.elasticsearch.index` 里的名字就不再是最终索引名。**

**症状**：你在配置里写的是 `myapp-log-2026.09.30`，ES 里出现的却是：

```
filebeat-7.17.29-2026.09.30-000001
```

`-000001` 这个后缀就是 **ILM 的签名**。

> ★ **怎么决定关不关？看你环境里已有的索引**：
> ```bash
> curl -s "http://<ES>:9200/_cat/indices?h=index&s=index:asc" | grep -- '-log-'
> ```
> - 已有系列**都没有** `-000001` ⇒ 你环境的惯例是「**ILM 关 + 按天索引**」，**跟着关**；
> - 已有系列**有** `-000001` ⇒ 你环境在用 ILM，那就把 `setup.ilm.rollover_alias` 改成你的前缀，
>   而不是关掉它。

> ★★ **关掉 filebeat 的 ILM ≠ 不要保留策略**。
> 前者只是不让 filebeat 接管**命名**；过期删除要靠 ES 侧单独建策略，见 [第 5 节](#5-第-4-步es-侧准备保留策略--索引模板)。
> 不建保留策略，索引会一直堆到磁盘 95% —— 那时**所有索引变只读，采集当场写不进来**。

### 3.4 校验配置语法

```bash
sudo filebeat test config -c /etc/filebeat/filebeat.yml
# 期望：Config OK
```

---

## 4. 第 3 步：启动服务并验证出口

### 4.1 起服务

```bash
sudo systemctl enable --now filebeat
sleep 5
systemctl status filebeat --no-pager -l
```

**期望**：`Active: active (running)`。

> ★★ **如果它是反复重启（crash-loop）**，systemd 很快会**放弃它**，
> 之后你直接 `restart` 只会看到 `Start request requested too quickly`。
> 这时必须先清失败计数：
> ```bash
> sudo systemctl reset-failed filebeat
> sudo systemctl restart filebeat
> ```

### 4.2 ★ 最重要的一步：验证「发得出去」

```bash
sudo filebeat test output
```

它会**逐跳**打印与 ES 的连接测试（DNS → TCP → TLS → 握手）：

```
elasticsearch: http://192.0.2.163:9200...
  parse url... OK
  connection...
    parse host... OK
    dns lookup... OK
    dial up... OK
  TLS... OK
  talk to server... OK
  version: 7.17.x
```

**`talk to server... OK` 才说明数据发得出去。** 这一条命令能省掉后面一大半猜测。

### 4.3 确认 filebeat 真的在采

```bash
sudo journalctl -u filebeat -n 40 --no-pager
```

关心这几行：

| 日志行 | 说明 |
|---|---|
| `Filebeat is running as root` | 以 root 运行 ⇒ 读日志文件**不存在权限问题** |
| `Config reloader started` | 片段热加载器已启动 |
| `Configured paths: [...]` | ★ 平台下发的路径被读到了 |
| `Harvester started for paths: [...]` | 开始采集（几个文件就有几条） |

> ★ `Harvester started` **只代表"开始读了"**，不代表"发出去了"。
> 真正决定性的是指标行里的 `output.events.acked`（见 [9.4](#94-最可靠的验收造一行新日志)）。

---

## 5. 第 4 步：ES 侧准备（保留策略 + 索引模板）

> 这一步在**第一条日志落进来之前**完成。晚了就要 reindex。

### 5.1 先定索引名

日志落到哪个索引，由目标机 `filebeat.yml` 的 `index` 决定（见 [3.2](#32-改-etcfilebeatfilebeatyml)）。
示例里用的是 `myapp-log-%{+yyyy.MM.dd}`，即按天滚动：

```
myapp-log-2026.11.05
myapp-log-2026.11.06
...
```

**建议就一个索引族，不要按服务拆**：查的时候用字段（`service_name` / `server_ip`）过滤，
倒排交集是毫秒级的；拆成几十个索引反而让分片数暴涨，且跨服务串联排查时要跨索引搜。

### 5.2 建保留策略（过期自动删索引）

```bash
curl -X PUT "http://<ES>:9200/_ilm/policy/myapp-log-30d" \
  -H 'Content-Type: application/json' -d '{
  "policy": {
    "phases": {
      "hot":    { "min_age": "0ms", "actions": {} },
      "delete": { "min_age": "30d", "actions": { "delete": {} } }
    }
  }
}'
```

> 期望返回 `{"acknowledged":true}`。
> `min_age` 从**索引创建时间**算，不是最后一条数据的时间 —— 按天索引正好对得上。
> **不用 rollover**：索引名保持 `myapp-log-YYYY.MM.DD`，不会被改成 `-000001`。
> ILM 是**异步**的（`poll_interval` 默认 10 分钟），到点不会立刻消失，别以为没生效。

### 5.3 建索引模板（决定字段类型 + 绑定保留策略）

```bash
curl -X PUT "http://<ES>:9200/_index_template/myapp-log-custom" \
  -H 'Content-Type: application/json' -d '{
  "index_patterns": ["myapp-log-*"],
  "priority": 200,
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.lifecycle.name": "myapp-log-30d"
    },
    "mappings": {
      "properties": {
        "server_ip":    { "type": "keyword" },
        "service_name": { "type": "keyword" }
      }
    }
  }
}'
```

三个要点，每个都对应一次踩坑：

| 要点 | 不这么做的后果 |
|---|---|
| **模板名带 `-custom`** | filebeat 自推模板的名字 = `setup.template.name`，同名 PUT 会**整个覆盖**，谁后跑谁赢 |
| **`priority: 200`** | filebeat 自推模板 priority 是 150，低于它就压不住，字段仍被动态映射成 `text` |
| **两个字段声明 keyword** | 动态映射会建成 `text`，`term` 查询**返回 0 条且不报错**（`web-api` 被 `-` 拆成两个词） |

> ★★ **`number_of_replicas` 单节点必须是 `0`**。
> 写成 `1` 时，副本分片无处分配，索引会**一直停在 yellow** —— 数据读写都正常，
> 但那行黄色告警会永远挂着，且容易被误当成故障。
> 多节点环境才填 `1`（或更多）；从单节点扩成多节点后，记得把模板改回 `1`
> 并给已有索引补副本 —— **零副本的集群坏一块盘就丢数据**。
>
> - 单个索引的副本数是**动态设置**，可原地改、不用 reindex：
>   `PUT /myapp-log-*/_settings {"index":{"number_of_replicas":0}}`
> - 单节点 ES 平时核对：`GET _cat/indices/myapp-log-*?h=index,health,rep`，`health` 应为 `green`。
> - **索引一旦创建，改模板不回溯**。已经建错了只能 reindex。
> - `service_name` / `server_ip` 这两个字段名是**平台约定**，不要改：
>   前者由任务的「附加字段」写入，后者由平台下发片段时逐台注入。

**★ 如果模板建晚了（索引已经产生了才想起来建）**

模板只在**索引创建那一刻**生效，已存在的索引不会变。分三种情况处理：

| 现有索引的 mapping | 影响 | 怎么办 |
|---|---|---|
| 字段已是 `keyword` | 无 | 不用管 |
| `text` + `keyword` 子字段（ES 7 动态映射的默认结果） | **功能正常** | 不用管 —— 平台的筛选接口会自动改用 `service_name.keyword` 聚合 |
| 纯 `text` 且无子字段 | 聚合被 ES 拒绝 | 只能 reindex |

先查一句：

```bash
curl -s "http://<ES>:9200/myapp-log-*/_mapping" | grep -A4 service_name
```

**保留策略可以补绑**（模板里的 `index.lifecycle.name` 同样不回溯）：

```bash
# ⚠️ 绑之前先看创建时间，超过 min_age 的索引会被 ILM 立刻删除
curl -s "http://<ES>:9200/_cat/indices/myapp-log-*?h=index,creation.date.string&s=index:asc"

curl -X PUT "http://<ES>:9200/myapp-log-*/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index":{"lifecycle":{"name":"myapp-log-30d"}}}'
```

> ★ **不要用「删索引重来」的办法修正类型**：删除索引**不会让 filebeat 重发数据** ——
> registry 里已记了 offset，filebeat 认为那些行读过了。真要重来只能 `_reindex` 到新索引名。

### 5.4 验证

```bash
# 模板在不在
curl -s "http://<ES>:9200/_index_template/myapp-log-custom" | head -20

# 索引建出来后，确认字段类型（这条要在第一条数据之后跑）
curl -s "http://<ES>:9200/myapp-log-*/_mapping" | grep -A2 -E 'server_ip|service_name'
# 期望："type": "keyword"
```

### 5.5 磁盘水位（决定保留天数能不能到 30 天）

ES 三个水位，别等 100%：

| 水位 | 默认值 | 触发什么 |
|---|---|---|
| low | 85% | 不再分配新分片（**新索引可能建不出来**） |
| high | 90% | 尝试迁走分片，迁不走就卡住 |
| **flood_stage** | **95%** | **所有索引变只读**，采集当场写不进来 |

容量公式：

```
单日增量 × 保留天数 × (1 + 副本数) ≤ 磁盘总量 × 0.85
```

单日增量用接入第二天实测：`GET _cat/indices/myapp-log-*?h=index,docs.count,store.size`。

---

## 6. 第 5 步：平台侧准备

### 6.1 凭据必须是 root（为什么）

这是**最容易卡住**的一点。平台的执行方式是：

> 用任务绑定的**凭据账号**直接 SSH 执行命令，**不会自动加 `sudo`**。

而「下发」这一步要跑的是一条**带 `set -e` 的脚本**，其中：

| 命令 | 需要什么 | 普通账号能满足吗 |
|---|---|---|
| `mkdir -p /etc/filebeat/inputs.d` | 目录已存在时不需要权限 | ✅ 预建好即可 |
| `base64 -d > /etc/filebeat/inputs.d/xwops-xxx.yml.incoming` | 该**目录的写权限** | ✅ 给写权限即可 |
| `filebeat test config -c <片段>` | 读文件 | ✅ |
| `cp -p` 备份、`mv -f` 原子替换、`chmod 0644` | 目录写权限 + 文件属主 | ✅ |
| **`systemctl restart filebeat`** | root / polkit | ❌ **只有这一步真的需要 root** |

**两件事必须知道：**

1. ★★ **「这个账号有 sudo 权限」帮不上忙。** `sudo` 不是一种「自动生效的权限」，
   它是一条**你必须显式敲出去的命令**。平台没敲，那份 sudoers 授权**一次都不会被兑现**。
   典型报错：
   ```
   下发命令退出码 1: bash: line 1: /etc/filebeat/inputs.d/xwops-xxx.yml.incoming: Permission denied
   ```
   注意 `bash: line 1:` —— 这是 **bash 在做输出重定向时就失败了**，连一个字节都没写下去。

2. ★ **最后一步可以被绕过**：平台的逻辑是「主配置开了 `reload.enabled` 就等热加载，
   否则 `systemctl restart filebeat`」。所以**主配置里有 `reload.enabled: true` 时，
   平台根本不会敲 `systemctl`**——理论上普通账号 + 目录写权限也能下发成功。

**结论（推荐做法）：**

| 方案 | 做什么 | 适用 |
|---|---|---|
| **A（推荐）** | 用 **root** 凭据 | 最省事，试跑 + 下发一次全通 |
| B | 保留普通账号：① 给它片段目录的写权限 ② 主配置必须开 `reload.enabled` | 安全要求高、且能接受两处都要配对 |

方案 B 的命令：

```bash
# ① 让该账号能写片段目录
sudo chown <账号>:<账号> /etc/filebeat/inputs.d
# 更保守的替代：sudo chgrp <账号> /etc/filebeat/inputs.d && sudo chmod 775 /etc/filebeat/inputs.d
```

> ★ **如果目标机禁了 root 密码登录**（Ubuntu 默认 `PermitRootLogin prohibit-password`），
> 用**私钥凭据**：凭据管理里认证类型选「私钥」，粘贴私钥全文（不能带 passphrase）。
> 一条私钥可以给多台主机用，但凭据的「关联服务器」要**留空**（通用凭据），
> 否则绑定到某台机后，挂别的机器会报「凭据绑定的服务器与目标服务器不一致」。

### 6.2 登记 ES 数据源

平台 → 日志管理 → **ES 数据源** → 新建：

| 字段 | 填什么 |
|---|---|
| 名称 | 自定义，如 `统一日志采集` |
| URL | `http://<ES>:9200`，带 `http://` |
| 用户名 / 密码 | 有认证才填 |
| 索引模式 | 检索时默认用的通配，如 `myapp-log-*` |

> ★ 这个数据源是**查询入口**（检索页去哪里查），**不是写入目标**。
> 日志写到哪台 ES，由**目标机 `filebeat.yml` 的 `output`** 决定。

---

## 7. 第 6 步：新建采集任务

### 7.1 一个服务一个任务

平台的「日志路径」是**单值字段**，渲染成 filebeat `paths:` 的**一个**元素，且白名单只允许
`字母数字 _ - . / * [ ]`：

```
✅ /opt/myapp/logs/web/all.log
✅ /opt/myapp/logs/web/*.log
❌ /opt/myapp/logs/{web,api}/all.log      ← 花括号被后端拒绝
❌ /opt/myapp/logs/web/all.log /opt/...    ← 空格被拒绝
```

`*/all.log` 看似能一条覆盖所有服务，但**服务名没有来源**：一个任务只有一套「附加字段」，
没法给不同子目录打不同的 `service_name`，检索页就筛不出服务。

⇒ **一个服务目录 = 一个任务**。23 个服务就建 23 个任务，每个任务的目标服务器都勾全部 n 台。

### 7.2 字段逐项说明

平台 → 日志管理 → **采集配置** → 新建。

| 字段 | 填什么 | 备注 |
|---|---|---|
| **任务名称** | 如 `myapp-web` | 建议 `<应用>-<服务>`，会作为 `xwops_task_name` 随日志写下去，**也是片段文件名的来源** |
| **ES 数据源** | 选 6.2 建的 | 仅用于比对与跳转检索 |
| **索引前缀** | 如 `myapp-log` | 小写字母数字开头；★ **只是标签**，不决定落库索引 |
| **凭据** | ★ 选 **root**（或私钥凭据） | 见 [6.1](#61-凭据必须是-root为什么) |
| 采集方式 | 托管 filebeat 配置片段 | 当前仅此一种 |
| **日志路径** | 如 `/opt/myapp/logs/web/all.log` | ★ **填在这里**，不是填在 filebeat.yml |
| 包含 / 排除正则 | 按需 | 见下方「正则方言」提醒 |
| 最低级别 | 按需 | 低于该级别的行**直接丢弃**（不落 ES，检索时筛不出来） |
| 多行起始正则 | Java 堆栈等按需 | 形如 `^\d{4}-\d{2}-\d{2}` |
| **附加字段** | 至少填 `service_name` | ★ 见下方警告 |
| **只采新增** | 建议勾上 | 见 [第 11 节](#11-只采新增到底什么意思) |
| 片段目录 | 默认 `/etc/filebeat/inputs.d` | 与 filebeat.yml 的 `path:` 一致 |

**★ 附加字段的坑（会导致"三边全绿、零数据"）**

filebeat 装的 ECS 模板把 122 个顶层字段里的 **115 个声明成 object 类型**，
像 `service` / `host` / `agent` / `log` / `cloud` 这些**你给它们填标量值**，
ES 会直接拒收，而 **filebeat 是静默丢弃、不重试**——表现是「事件数一直涨，ES 里一条没有」。

要填就填**自己的字段**，检索页认这几个名字：

```json
{"service_name": "web"}
```

| 字段 | 用途 |
|---|---|
| **`service_name`** | ★ 检索页「服务」下拉的来源，必须填 |
| `env_name` | 环境标识，检索结果里会显示 |

> ⚠️ **绝不能写 `service`** —— 那是 ECS 的 object 字段，填标量必被拒收。
> 平台自动注入的 `server_ip` 不受影响（它不是 ECS 字段）。

**★ 正则方言提醒**：filebeat 用的是 Go 的 **RE2**，
不支持**负向预查/回顾**（`(?!...)`、`(?<=...)`）和**数字反向引用**（`\1`）。
平台在保存与下发时都会拦，但你自己心里要有数。

📷 **截图位**：新建任务表单（注意遮挡 IP 与账号）。

### 7.3 批量铺开

第一个任务跑通后（走完第 8~10 步），其余服务照抄，**每次只改三处**：

1. 任务名称（`myapp-web` → `myapp-api`）
2. 日志路径（`.../web/all.log` → `.../api/all.log`）
3. 附加字段（`service_name: web` → `api`）

目标服务器一次勾全 n 台即可。

> 建议一次铺 3~5 个服务就验一轮，别 23 个全建完再统一验 —— 那时出问题分不清是模板、路径还是字段的错。

---

## 8. 第 7 步：检测 → 试跑 → 下发 → 回读

### 8.1 环境检测（只读）

点**检测**。返回的 `warnings` 很有价值：

| warning 原文 | 含义 |
|---|---|
| `目标机没有安装 filebeat（command -v filebeat 为空）` | 回到第 2 步 |
| `主配置里没有加载片段目录 —— 需要补 filebeat.config.inputs 才能生效` | 回 3.2 补 `filebeat.config.inputs` |
| `filebeat 服务当前不是 active（failed）` | 回 4.1 / 4.2 |
| `filebeat X 较老，将使用 log input 而非 filestream` | 版本低于 7.9 |
| `落库目标由目标机 output 决定：hosts=… index=…` | ★ **这是"日志实际落到哪个索引"的权威答案** |

> ★ **warning 必须读**。这一条「目标机没有安装 filebeat」曾经被忽略，
> 导致排查方向完全跑偏。

### 8.2 试跑（只读，不落 ES）

点**试跑**：平台会 SSH 到目标机 `tail` 最后 N 行，**在平台侧**跑一遍过滤规则，给你看保留/被过滤的对照。

> ★★ **试跑成功 ≠ 采集成功。** 试跑**不下发、不让 filebeat 动、不写 ES**。
> 它只证明「**凭据能读到这个日志文件**」。
> ★ **试跑只对第一台目标机生效**，多目标任务不能拿它当全部通过。

### 8.3 下发

点**下发**。平台做的事（任一步失败即中止）：

1. 生成片段 → **平台侧校验形状**（必须是**顶级数组**，不能套 `filebeat.inputs:`）；
2. 目标机：写 `.incoming`（**绝不先动现场**）→ `filebeat test config` **语法校验**；
3. 校验通过 → `cp -p` 备份旧片段 → **删掉该任务的历史命名片段** → `mv -f` **原子替换** → `chmod 0644`；
4. 主配置开了 `reload.enabled` 就**等热加载（≤10s）**，否则 `systemctl restart filebeat`。

> ★ 这个「先写 `.incoming`、校验通过才替换」的设计很关键：
> **校验失败时目标机现有配置一个字都不会被改动。**

📷 **截图位**：下发结果弹窗（成功 / 异常明细）。

### 8.4 回读现场（别只看平台说"成功"）

```bash
# ① 片段在不在（文件名带服务名，一眼能认出是哪个任务）
ls -l /etc/filebeat/inputs.d/
# 期望：xwops-<服务名>-<任务id>.yml，例如 xwops-myapp-web-7.yml

# ② 片段到底写了什么 —— ★ 这是"消费方拿到的输入"，最权威
sudo cat /etc/filebeat/inputs.d/xwops-myapp-web-7.yml
```

**片段长这样（filestream 形态，filebeat ≥ 7.9）：**

```yaml
# 由 XwOps 平台生成 · 任务 #7 · 请勿手工修改（下次下发会覆盖）
- type: filestream
  id: xwops-task-7
  enabled: true
  paths:
    - /opt/myapp/logs/web/all.log
  fields:
    xwops_task_id: 7
    xwops_task_name: 'myapp-web'
    index_prefix: 'myapp-log'
    service_name: 'web'
  fields_under_root: true
  parsers:
    - multiline:
        pattern: '^\d{4}-\d{2}-\d{2}'
        negate: true
        match: after
  processors:
    - add_fields:
        target: ''
        fields:
          server_ip: '192.0.2.30'
```

**filebeat < 7.9 或勾了「只采新增」时**，同一个任务会降级成 `log` input：

```yaml
- type: log
  enabled: true
  tail_files: true          # ★ 只在 log input 里有这个选项
  paths:
    - /opt/myapp/logs/web/all.log
  fields:
    ...
```

> ★ **`filebeat.inputs:` 这个键不能出现在片段里。** 片段必须是**顶级数组**（`- type:` 开头）。
> 套了键的片段**语法合法**，filebeat 会**放行但提取出 0 个 input**——
> 不报错、不采集、平台显示成功。这是最坏的失败形态。

### 8.5 多台主机的注意事项

一个任务勾了 n 台，片段是**逐台渲染**的：路径与服务名相同，只有 `server_ip` 每台不同。

- **必须通过平台下发**，不要手工把一台的片段拷到另一台 —— 那样 `server_ip` 会全错，
  检索时按 IP 筛永远是同一台。
- 下发后抽查 2~3 台：

```bash
grep 'server_ip' /etc/filebeat/inputs.d/xwops-myapp-web-7.yml
# 每台应该看到自己的 IP
```

---

## 9. 第 8 步：验收

### 9.1 索引建出来了，名字对

```bash
curl -s "http://<ES>:9200/_cat/indices/myapp-log-*?h=index,docs.count,store.size&s=index:desc"
```

期望：出现 `myapp-log-2026.11.05`（当天），`docs.count` > 0。
若索引名是 `filebeat-7.17.x-...-000001` ⇒ [3.3](#33-ilm关掉它否则你配的索引名不作数) 的 `setup.ilm.enabled: false` 没生效。

### 9.2 字段类型是 keyword

```bash
curl -s "http://<ES>:9200/myapp-log-*/_mapping" | grep -A2 -E 'server_ip|service_name'
```

期望 `"type": "keyword"`。
若看到 `"type": "text"` + `"fields": {"keyword": ...}` ⇒ [5.3](#53-建索引模板决定字段类型--绑定保留策略) 的模板没在索引创建前生效，**只能 reindex 重来**。

### 9.3 关键字段都有值

```bash
curl -s -X POST "http://<ES>:9200/myapp-log-*/_search?size=1&pretty" \
  -H 'Content-Type: application/json' -d '{"sort":[{"@timestamp":"desc"}]}' \
  | grep -E '"(server_ip|service_name|@timestamp|message)"'
```

四项缺一不可：`server_ip`（主机）、`service_name`（服务）、`@timestamp`（时间）、`message`（关键字）。

- `service_name` 缺失 ⇒ 附加字段没写进片段，回 [7.2](#72-字段逐项说明)
- `@timestamp` 是采集时刻而非日志正文时间 ⇒ 时间提取正则没填对

### 9.4 最可靠的验收：造一行新日志

```bash
echo "$(date '+%F %T') XWOPS-COLLECT-PROBE hello" | sudo tee -a /opt/myapp/logs/web/all.log
sleep 30
curl -s "http://<ES>:9200/_cat/indices/myapp-log-*?h=index,docs.count&s=creation.date:desc" | head -3
```

**期望**：最上面一行是你的索引，`docs.count` **从 0 变成 1（或加 1）**。

> ★ `docs.count = 1` 且时间对得上 ⇒ **全链路打通**。这是唯一无歧义的验收判据。
> 光看「平台显示下发成功」不算。

### 9.5 按服务 / 按主机聚合，数量对得上

```bash
curl -s -X POST "http://<ES>:9200/myapp-log-*/_search?size=0" \
  -H 'Content-Type: application/json' -d '{
  "aggs": {
    "by_service": { "terms": { "field": "service_name", "size": 50 } },
    "by_host":    { "terms": { "field": "server_ip", "size": 50 } }
  }
}'
```

- `by_service` 的桶数应该等于**已有数据的服务数**
- `by_host` 的桶数应该等于**已有数据的主机数**
- 报 `Fielddata is disabled` ⇒ 字段是 text，回到 [9.2](#92-字段类型是-keyword)

---

## 10. 第 9 步：在检索页查日志

平台 → 日志管理 → **日志检索**。

### 10.1 选数据源与索引模式

1. **ES 数据源**：选 [6.2](#62-登记-es-数据源) 建的那条
2. **索引模式**：`myapp-log-*`（下拉里是归并后的通配模式，**带星号**）

### 10.2 筛选条件

| 条件 | 说明 |
|---|---|
| **时间范围** | 必选。不选时间会扫全部索引，大索引会超时（前端 30s 上限） |
| **主机 IP** | 多选，选项来自当前索引里真实出现过的 `server_ip` |
| **服务** | 多选，选项来自 `service_name` |
| **级别** | 从正文里匹配——没有独立 `level` 字段时是弱匹配 |
| **关键字** | 全文检索，走 `query_string` |

> ★ 主机 / 服务下拉是**对着当前索引做聚合**得来的，所以：
> - 索引里没有 `service_name` 字段 ⇒ 下拉为空，下方会出现黄色提示说明原因
> - 换索引后已选但不存在的值会被自动剔除，避免"选了却查不到"

### 10.3 查不到怎么办

按顺序确认：

1. 索引模式对不对（`myapp-log-*`，注意 `*`）
2. 数据源 URL 是不是**日志真正落进去的那台 ES**
3. ES 里到底有没有：`curl -s "http://<ES>:9200/_cat/indices?h=index&s=index:asc" | grep myapp`
4. 时间范围是不是落在日志的时间段内（`@timestamp` 可能不是采集时刻）
5. 筛选条件是否过窄（先清空 IP / 服务，只留时间 + 关键字）

---

## 11. 「只采新增」到底什么意思

这个开关的语义比大多数人以为的**窄**：

> `tail_files` **只对「filebeat 还没见过的文件」生效**。

**推论（非常重要）：一台全新装的 filebeat，registry 是空的，所以所有日志文件对它都是"没见过"的。**

| 场景 | 行为 |
|---|---|
| 刚配好采集 | **从每个文件的末尾开始读** ⇒ 已有的历史日志**一条都不采** |
| 之后新写入的行 | 正常采集 |
| filebeat 重启（registry 还在） | 从**上次记录的位置**继续读，不丢不重 |

**所以：配置完成那一刻之前产生的内容，不会进 ES。** 这不是 bug，是这个开关的设计目的
（避免把几百 MB 历史日志一次性灌进 ES）。

| 你的目标 | 怎么做 |
|---|---|
| 只要新日志 | 保持勾选 |
| 历史 + 新增都要 | **取消勾选**，重新下发 |
| 只要最近 N 天的历史 | 用 `ignore_older`（高级配置）+ 不勾「只采新增」 |

---

## 12. 故障总表（按症状查）

**先说方法**：先确定断在 [第 0 节那张图](#0-五分钟心智模型) 的**第几段**，再对症下药。

| # | 症状 | 最可能的原因 | 判据 / 处置 |
|---|---|---|---|
| 1 | 试跑报「没有读到内容…且账号有读权限」 | 凭据账号读不到日志文件（**目录缺 `x`**，不是文件权限） | `namei -l <日志文件路径>` 逐级看；补目录的进入权限 |
| 2 | `apt-get install filebeat` 报 `Unable to locate package` | 没加 Elastic 源（filebeat 不在官方源） | 走 [2.2](#22-方式-a在线加-elastic-源推荐) 或 [2.3](#23-方式-b离线-deb--rpm内网) |
| 3 | 服务反复重启，日志 `could not initialize the keystore: … permission denied` | `path.data` 落在了不可写的目录 | `systemctl cat filebeat` 看 `WorkingDirectory` 与 `--path.data`；正解是让它落在 `/var/lib/filebeat` |
| 4 | `Start request repeated too quickly` | crash-loop 触发了 systemd 的 `StartLimitBurst` | `sudo systemctl reset-failed filebeat` 再 `restart` |
| 5 | 启动报 `setup.template.name and setup.template.pattern have to be set if index name is modified` | 自定义了 `index` 却没声明模板 | 补 `setup.template.name` / `setup.template.pattern` |
| 6 | 检测报 `Authentication failed` | ① 目标机禁了 root 密码登录（Ubuntu 默认）② 凭据密码为空 ③ 账号不对 | 先 `ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no root@<IP>` 强制走密码试一次；不行就改用私钥凭据 |
| 7 | 检测报 `连接超时 / Connection refused` | 端口不对（非 22）或网络不通 | CMDB 里该服务器的 SSH 端口要填对；`ss -lntp \| grep ssh` 确认 |
| 8 | 下发报 `…xwops-xxx.yml.incoming: Permission denied` | 凭据非 root 且目录不可写（**平台不加 `sudo`**） | 换 root 凭据，或按 [6.1](#61-凭据必须是-root为什么) 方案 B |
| 9 | 下发报 `can only be writable by the owner but the permissions are "-rw-rw-r--"` | 目标机 umask 是 `002`，`.incoming` 被建成组可写 | 见 [第 13 节](#13-已知限制与平台当前缺陷) 第 3 条 |
| 10 | **ES 里没有索引** | ① 还没点「下发」；② 没装 filebeat；③ 服务没起来；④ **「只采新增」⇒ 还没有新日志** | 用 [9.4](#94-最可靠的验收造一行新日志) 造一行 probe |
| 11 | ES 里索引名是 `filebeat-<版本>-<日期>-000001` | **ILM 接管了命名** | 加 `setup.ilm.enabled: false`（见 [3.3](#33-ilm关掉它否则你配的索引名不作数)） |
| 12 | 事件数在涨、ES 一条没有 | 附加字段用了 ECS 对象型字段名（`service`/`host`/…） | 见 [7.2](#72-字段逐项说明) 的警告，改成 `service_name` |
| 13 | 改了 filebeat.yml 但没生效 | `setup.*` / `output.*` 是**启动级**配置，不参与 reload | `sudo systemctl restart filebeat` |
| 14 | 检索页「主机 / 服务」下拉是空的 | ① 索引里没有这两个字段；② 字段被映射成 text；③ 当前用户没有 `logSearch:Facets` 按钮权限 | 看下拉下方的黄色提示；权限问题见 [13.1](#131-检索页筛选相关的已知限制) |
| 15 | 片段文件名还是 `xwops-task-<id>.yml` | 文件名在**下发**时生成，重启不改变 | 对该任务重新点一次「下发」 |

---

## 13. 已知限制与平台当前缺陷

> 这一节是**主动披露**，避免你在踩到时怀疑人生。**不是你的配置问题。**

| # | 现象 | 根因 | 影响 / 绕行 |
|---|---|---|---|
| 1 | 平台上填的「索引前缀」不会变成 ES 里的索引名 | filebeat 的 `index` 是 **output 级**配置，**片段改不动它**；平台只把前缀作为 `fields` 带下去 + 当检索通配用 | 索引名统一在目标机 `filebeat.yml` 里管；ILM 启用时还会被 ILM 再改一次 |
| 2 | 没人提示「这个功能需要 root 凭据」 | 平台**没有任何地方**做凭据权限预检 | 只能靠一次失败反推。**见 [6.1](#61-凭据必须是-root为什么)** |
| 3 | 下发在 **umask=002** 的机器上必然失败 | 平台把 `.incoming` 写成 `664`（`0666 & ~umask`），而 `filebeat test config` 要求「**只有属主可写**」；平台的 `chmod 0644` 排在**校验之后**，永远轮不到 | **临时解**：预建并固定权限（`>` 重定向到已存在的文件不改权限）<br>`sudo touch /etc/filebeat/inputs.d/xwops-xxx.yml.incoming && sudo chmod 0644 <同上>`<br>⚠️ 一次性——成功下发后它会被 `mv` 走<br>**正解**：让平台在**校验之前**统一 umask/chmod（待修） |
| 4 | 用容器跑 filebeat 时，平台恒显示「未安装」 | 「环境检测」靠 `command -v filebeat` / `systemctl is-active filebeat` 判断 | 功能可用但状态失真，见 [2.4](#24-方式-c用容器跑-filebeat有代价) |
| 5 | 试跑只对**第一台**目标机生效 | 实现如此 | 多目标任务请分批验证 |
| 6 | 试跑读不到时，平台只能并列猜测原因 | 试跑执行的 `tail … 2>/dev/null \|\| true` **把 stderr 丢了** | 平台分不清「路径不存在」与「权限不足」；自行用 `namei -l` / 手工 `tail` 复核 |
| 7 | 非超管看不到「主机 / 服务」下拉 | `facets` 接口需要 `logSearch:Facets` 按钮权限，缺了会被 `CustomPermission` **默认拒绝（403）**，页面只显示空下拉、不报错 | 角色管理里给该角色勾上「日志检索」菜单下的**全部 4 个按钮**，数据权限选**全部数据权限**，然后**重新登录** |

### 13.1 检索页筛选相关的已知限制

- 筛选只认 `server_ip` / `service_name` **两个字段**。其它索引（如 nginx 日志）没有这两个字段时，
  下拉为空并提示「该索引没有 server_ip / service_name 字段」，属于预期行为。
- 若字段被动态映射成 `text`，聚合会被 ES 拒绝，提示「不是 keyword」。此时只能 reindex。
- 老索引的字段若是 `text` + `.keyword` 子字段，平台会自动改用子字段聚合，**不需要手工处理**。

---

## 14. 一页速查（命令清单）

```bash
# ── 目标机 ──────────────────────────────────────────────
filebeat version                                          # 装好了吗
sudo filebeat test config -c /etc/filebeat/filebeat.yml   # 配置语法
sudo filebeat test output                                 # ★ 发得出去吗
systemctl status filebeat --no-pager                      # 服务状态
sudo systemctl reset-failed filebeat                      # crash-loop 后必做
sudo journalctl -u filebeat -n 40 --no-pager              # 看日志
ls -l /etc/filebeat/inputs.d/                             # 片段在不在
sudo cat /etc/filebeat/inputs.d/xwops-<服务名>-<id>.yml    # ★ 片段内容
namei -l /opt/myapp/logs/web/all.log                      # ★ 权限逐级排查
systemctl show filebeat -p ExecStart -p User              # 以谁的身份跑

# ── ES ─────────────────────────────────────────────────
curl -s http://192.0.2.163:9200/                          # 版本 / 集群名
curl -s "http://192.0.2.163:9200/_cat/indices/myapp-log-*?h=index,docs.count,store.size&s=index:desc"
curl -s "http://192.0.2.163:9200/myapp-log-*/_mapping" | grep -A2 service_name
curl -s "http://192.0.2.163:9200/myapp-log-*/_ilm/explain?human=true" | grep -E '"index"|"phase"'
curl -s "http://192.0.2.163:9200/_cat/aliases?v"          # ILM 滚动别名
curl -s -X DELETE "http://192.0.2.163:9200/<要删的索引>"

# ── 验收（造一行新日志）─────────────────────────────────
echo "$(date '+%F %T') XWOPS-COLLECT-PROBE hello" | sudo tee -a /opt/myapp/logs/web/all.log
sleep 30
curl -s "http://192.0.2.163:9200/_cat/indices/myapp-log-*?h=index,docs.count&s=creation.date:desc" | head -3
```

---

## 附录 A. 脱敏占位符清单

本文档与仓库一致，**所有值都是占位符**，请按你的环境替换：

| 占位值 | 含义 | 换成什么 |
|---|---|---|
| `192.0.2.163` | ES 地址 | 你的 ES 地址 |
| `192.0.2.30` | 目标机地址 | 你的被采集机 IP |
| `/opt/myapp/logs/web/all.log` | 被采集的日志路径 | 你的真实路径 |
| `myapp` / `myapp-log` | 业务标识 / 索引前缀 | 你的业务名 |
| `web` / `api` | 服务名示例（`service_name` 的值） | 你的服务目录名 |
| `xwops-<服务名>-<id>.yml` | 目标机上的片段文件名 | 由任务名与任务 id 自动生成 |
| `service_name` | 自定义字段：服务标识 | **不要改**（检索页按这个名字取值） |
| `server_ip` | 平台自动注入的字段：目标机 IP | **不要改**（平台代码写死） |
| `other-app-log-*` | 环境中其它应用的索引示例 | 你环境里已有的索引 |
| `<账号>` `root` | SSH 凭据账号 | 你的账号 |

> ★ **不要把真实口令、私钥内容、内网 IP 写进任何提交进仓库的文档里。**

## 附录 B. 截图清单

本手册正文用**命令与期望输出**代替截图（原因见 [关于截图](#关于截图)）。
如需补充截图，请放在 `docs/images/log-collect/` 下，按下列命名：

| 文件名 | 该拍什么 | 脱敏要求 |
|---|---|---|
| `01-task-form.png` | 平台「新建采集任务」表单 | 遮挡 IP、账号、真实业务名 |
| `02-env-detect.png` | 「环境检测」结果与 warnings | 遮挡 IP、主机名 |
| `03-preview.png` | 「试跑」结果弹窗 | 日志内容如有敏感信息需遮挡 |
| `04-dispatch-result.png` | 「下发结果」弹窗 | 遮挡 IP |
| `05-es-indices.png` | `_cat/indices` 输出（圈出你的索引） | 遮挡其它应用的索引名 |
| `06-search.png` | 日志检索页出结果 | 遮挡日志正文中的敏感信息 |

放置方式（在正文对应位置插入）：

```markdown
![新建采集任务](docs/images/log-collect/01-task-form.png)
```

---

## 附：本文档与其它手册的关系

| 文档 | 内容 |
|---|---|
| [`DEPLOY.md`](DEPLOY.md) | XwOps 平台自身的从零部署 |
| [`UPDATE.md`](UPDATE.md) | 已上线环境的增量更新 |
| **`LOG-COLLECT.md`（本文）** | 日志采集功能的**目标机 + 平台**完整配置与排查 |
| [`PRODUCT-ARCHITECTURE.md`](PRODUCT-ARCHITECTURE.md) | 产品架构与模块划分 |

---

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-05 | 重写为「一个任务 = 一条路径 = 一个 input」的单一采集模型；补 ES 保留策略与索引模板、`service_name` 字段约定、检索页筛选说明、片段文件名改为 `xwops-<服务名>-<id>.yml` |
