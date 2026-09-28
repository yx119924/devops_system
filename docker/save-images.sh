#!/bin/bash
# ==============================================================================
# XwOps 平台 —— 镜像一键打包（load-images.sh 的对称脚本）
#
# 用法（在仓库根目录执行）：
#   bash docker/save-images.sh                  # 用 docker/README.md 里的默认 tag
#   bash docker/save-images.sh 1.1.0            # 指定 xwops/* 镜像的 tag
#   bash docker/save-images.sh 1.1.0 --web-only # 只打包前端镜像（改前端后最常用）
#
# 做四件事：确认镜像存在且带 tag → 检查磁盘 → docker save → 生成 md5 / sha256。
#
# ★ 为什么必须显式写 tag：docker save 不带 tag 会把匿名镜像（<none>:<none>）
#   一并导出，加载后无人引用，白白占体积 —— 这是踩过的坑（pack_deploy 的
#   ensure_tag() 就是为堵它而加的）。本脚本只按 RepoTags 精确导出。
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"

TAG="1.0.0"
if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then
    TAG="$1"
fi
ONLY_WEB=0
for a in "$@"; do
    [ "$a" = "--web-only" ] && ONLY_WEB=1
done

XWOPS_IMAGES=("xwops/web:${TAG}" "xwops/django:${TAG}" "xwops/celery:${TAG}")
BASE_IMAGES=("mysql:8.0" "redis:6.2.6-alpine")

if [ "$ONLY_WEB" = "1" ]; then
    IMAGES=("xwops/web:${TAG}")
    OUT="xwops-web-${TAG}.tar"
else
    IMAGES=("${XWOPS_IMAGES[@]}" "${BASE_IMAGES[@]}")
    OUT="xwops-images-v${TAG}.tar"
fi

echo "=== 1/4 确认镜像存在 ==="
missing=0
for img in "${IMAGES[@]}"; do
    if docker image inspect "$img" >/dev/null 2>&1; then
        size=$(docker image inspect "$img" --format '{{.Size}}')
        printf "  [OK]   %-28s %s\n" "$img" "$(numfmt --to=iec "$size" 2>/dev/null || echo "${size}B")"
    else
        printf "  [缺失] %s\n" "$img"
        missing=1
    fi
done
if [ "$missing" = "1" ]; then
    echo
    echo "[错误] 有镜像不存在。请先构建："
    echo "         docker build -f docker_env/web/Dockerfile     -t xwops/web:${TAG} ."
    echo "         docker build -f docker_env/django/Dockerfile  -t xwops/django:${TAG} ."
    echo "         docker build -f docker_env/celery/Dockerfile  -t xwops/celery:${TAG} ."
    echo "       或先 docker load -i 旧包拿到基础镜像。"
    exit 1
fi

echo
echo "=== 2/4 检查磁盘空间 ==="
need=$(docker image inspect --format '{{.Size}}' "${IMAGES[@]}" 2>/dev/null | paste -sd+ | bc 2>/dev/null || echo 0)
[ -z "$need" ] && need=0
echo "  镜像合计（解压后占用）：$((need / 1024 / 1024)) MB"
echo "  ★ 注意：docker save 产出的是分层 tar，通常远小于上面这个数字"
echo "    （v1.0.0 的 5 个镜像解压后约 3.2 GB，导出 tar 只有 490 MB）。"
avail=$(df -Pk . | awk 'NR==2 {print int($4/1024)}')
echo "  当前目录可用：${avail} MB"
if [ "$avail" -lt 1024 ]; then
    echo "[警告] 可用空间不足 1 GB，可能写不下 tar。"
fi

echo
echo "=== 3/4 导出镜像 -> docker/$OUT ==="
rm -f "$OUT"
docker save -o "$OUT" "${IMAGES[@]}"
ls -l "$OUT"

echo
echo "=== 4/4 生成校验值 ==="
md5sum "$OUT" | tee checksums.txt
sha256sum "$OUT" | awk '{print "SHA256: " $1}'

echo
echo "----------------------------------------"
echo "包名   : docker/$OUT"
echo "字节数 : $(stat -c %s "$OUT" 2>/dev/null || stat -f %z "$OUT")"
echo "★ checksums.txt 已被本脚本覆盖为上面这个包，load-images.sh 会用它校验。"
if [ "$ONLY_WEB" = "1" ]; then
    echo "★ 只导出了 web 镜像。目标机上是同一个 tag 才能直接覆盖："
    echo "     docker load -i $OUT && docker compose up -d --no-build dvadmin3-web"
else
    echo "★ 全量包。目标机：bash docker/load-images.sh $OUT"
fi
echo "----------------------------------------"
