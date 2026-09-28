# docker/ —— 成品镜像

## 为什么这里看不到 `.tar` 文件？

镜像包 **490 MB**，远超 GitHub 单文件 **100 MB** 硬上限，**无法提交进 Git 仓库**。
因此镜像统一通过 **GitHub Release 附件**分发，`.tar` 已被 `.gitignore` 排除。

> 这带来一个必然结果：本目录在 GitHub 上只有脚本和清单，`.tar` 需要额外下载一次。
> 这是「仓库要能 clone」「镜像要能一键加载」两个目标之间绕不开的取舍。

---

## 镜像清单

| 镜像 | 说明 | 解压后大小 |
|---|---|---|
| `xwops/web:1.0.0` | 前端 nginx：**前端已编译进镜像**（`/usr/share/nginx/html`）+ 反向代理 | 113 MB |
| `xwops/django:1.0.0` | 后端运行环境：Python 3.12 + 依赖。**不含业务代码**（靠挂载） | 981 MB |
| `xwops/celery:1.0.0` | 异步任务运行环境：同 django 依赖层。**不含业务代码**（靠挂载） | 981 MB |
| `mysql:8.0` | 数据库（官方镜像） | 1.1 GB |
| `redis:6.2.6-alpine` | 缓存 / Celery broker（官方镜像） | 46.4 MB |

| 项目 | 值 |
|---|---|
| 打包文件 | `xwops-images-v1.0.0.tar` |
| 文件大小 | 514,598,912 字节（490.8 MB） |
| MD5 | `3bc78c4191306387f4016c1ad3765ef5` |
| SHA256 | `b79d75e0b3e12c7364c725cd6edad26ba334b85271c472facaaa0c8c69230f61` |
| 下载地址 | <https://github.com/yx119924/devops_system/releases/download/v1.0.0/xwops-images-v1.0.0.tar> |
| 内含镜像 | 上表 5 个（django/celery 共享层只存一份，所以并非简单相加） |

> ⚠️ **本包已于 2026-09-29 重新导出**（v1.0.0 重新发行）。
> 重新导出是因为 `xwops/web:1.0.0` 需要用**合入加固集后的前端源码**重建 ——
> 加固后的后端不再下发通知渠道敏感字段，沿用旧前端会让渠道页字段异常。
> **源码与镜像包必须配对使用**，别拿 09-28 的源码配 09-29 的镜像（或反之）。
> 其余 4 个镜像（django / celery / mysql / redis）内容未变。

> ⚠️ **`django` / `celery` 镜像里没有业务代码**，这是 DVAdmin 的既有设计：
> 代码通过 `docker-compose.yml` 的 `./backend:/backend` 挂载进容器。
> 所以 **`backend/` 源码目录是运行必需品**，不能只拿镜像不要源码。详见 `DEPLOY.md` 第 5 节。

---

## 一、下载镜像包

从本仓库 **Releases** 页面下载 → <https://github.com/yx119924/devops_system/releases>

在**仓库根目录**下一条命令直接下载到位：

```bash
curl -L --retry 3 -o docker/xwops-images-v1.0.0.tar \
  https://github.com/yx119924/devops_system/releases/download/v1.0.0/xwops-images-v1.0.0.tar
```

得到的目标位置：`docker/xwops-images-v1.0.0.tar`

## 二、校验完整性（**必做**）

490 MB 传输过程出错是常事，加载前先对 md5，避免「镜像坏了却以为部署失败」。

```bash
cd docker
md5sum -c checksums.txt
# 期望输出：xwops-images-v1.0.0.tar: OK
```

## 三、加载镜像（**一键**）

```bash
bash docker/load-images.sh
```

或手动等价执行：

```bash
docker load -i docker/xwops-images-v1.0.0.tar
```

加载完成后确认 5 个镜像都在：

```bash
docker images | grep -E 'xwops/|mysql:8.0|redis:6.2.6'
```

期望看到：

```
xwops/web      1.0.0             ...
xwops/django   1.0.0             ...
xwops/celery   1.0.0             ...
mysql          8.0               ...
redis          6.2.6-alpine      ...
```

---

## 四、之后做什么？

回到仓库根目录，按 **`DEPLOY.md`** 从 **第 4 步（改配置）** 继续。

---

## 五、改了代码，怎么重新打包镜像？

本目录另有一个与 `load-images.sh` **对称**的脚本：

```bash
bash docker/save-images.sh                    # 全量 5 个镜像 -> xwops-images-v<tag>.tar
bash docker/save-images.sh 1.1.0              # 指定 xwops/* 的 tag
bash docker/save-images.sh 1.1.0 --web-only   # 只打前端镜像（改前端最常用，包小很多）
```

它会先确认镜像存在且**带 tag**（避免把 `<none>` 匿名镜像一起导出），再 `docker save`，
最后生成 `checksums.txt`（md5）与 SHA256。

**完整流程**（改前端 → 重建 → 打包 → 送到目标机）见
**`DEPLOY.md` 第 9 节「改前端代码」**。其中有一条关键前提：

> ⚠️ **内网机器不能就地构建前端**。
> `docker_env/web/Dockerfile` 里有
> `RUN npm install --registry=https://registry.npmmirror.com --no-audit --no-fund --legacy-peer-deps`，
> **必须有外网**。内网目标机上执行构建会在这一步失败。
> 内网场景只能在**有外网的机器**上构建，再 `docker save` + 拷进去 `docker load`。

