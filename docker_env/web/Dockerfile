# ==============================================================================
# XwOps 前端镜像（多阶段：node 构建 → nginx 托管静态产物）
#
# ★★ 依赖必须可复现（2026-10-14 故障后加固，勿回退）
#
#   原写法是 `npm install`。因为 `web/` 里**没有锁文件**、且 `package.json` 用的
#   是 `^` 区间，每次重建都会装"当天最新"的版本 —— 实测 `@fast-crud/*` 从声明的
#   1.21.2 漂到 1.29.0、`element-plus` 从 2.8.0 漂到 2.14.7，结果 fast-crud 的
#   单元格渲染器抛 `TypeError: ….some is not a function`：表格只剩表头、数据行
#   整片渲染不出来（同一份源码，重建一次就坏，且与本次改动内容毫无关系）。
#
#   ⇒ 现在：`web/package-lock.json` 已入库，构建改用 `npm ci` 精确安装。
#   ★ 不要改回 `npm install`。升级依赖请显式改 package.json 并重新生成 lock。
#   ★ `--legacy-peer-deps` 必须保留 —— 锁文件就是带这个参数生成的，去掉会导致
#     安装参数与 lock 不一致。
#   ★ 遗留：`node:20-alpine` 是浮动 tag，Node 补丁版本仍可能漂移。若要彻底钉死，
#     用 `docker image inspect node:20-alpine --format '{{index .RepoDigests 0}}'`
#     取本地已有 digest，把 FROM 改成 `node:20-alpine@sha256:...`。
# ==============================================================================
FROM node:20-alpine AS build
WORKDIR /web
ENV NODE_OPTIONS=--max_old_space_size=4096
COPY web/ .
# ★ npm ci：严格按 package-lock.json 安装；lock 与 package.json 不一致会直接报错
RUN npm ci --registry=https://registry.npmmirror.com --no-audit --no-fund --legacy-peer-deps
RUN npm run build

FROM nginx:alpine
COPY docker_env/nginx/my.conf /etc/nginx/conf.d/my.conf
COPY --from=build /web/dist /usr/share/nginx/html
