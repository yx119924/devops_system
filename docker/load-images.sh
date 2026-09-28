#!/bin/bash
# ==============================================================================
# XwOps 平台 —— 镜像一键加载
#
# 用法：
#   bash docker/load-images.sh                              # 用默认包名
#   bash docker/load-images.sh /path/to/other-images.tar    # 指定包
#
# 做三件事：校验 md5 → docker load → 列出结果。
# 校验失败直接退出，避免把半截镜像load进去后误判成「部署失败」。
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"

TAR="${1:-xwops-images-v1.0.0.tar}"

echo "=== 1/3 检查镜像包 ==="
if [ ! -f "$TAR" ]; then
    echo "[错误] 找不到镜像包：$(pwd)/$TAR"
    echo "       请从本仓库 Releases 页面下载 xwops-images-v1.0.0.tar 放到 docker/ 目录下。"
    exit 1
fi
ls -l "$TAR"

echo
echo "=== 2/3 校验 md5 ==="
if [ -f checksums.txt ]; then
    md5sum -c checksums.txt
    echo "校验通过"
else
    echo "[警告] 未找到 checksums.txt，跳过校验"
fi

echo
echo "=== 3/3 加载镜像（490 MB，约需 30-90 秒）==="
docker load -i "$TAR"

echo
echo "=== 加载结果 ==="
docker images | grep -E 'xwops/|mysql:8.0|redis:6.2.6' || {
    echo "[错误] 未看到预期镜像，加载可能失败。"
    exit 1
}

echo
echo "完成。接下来回到仓库根目录，按 DEPLOY.md 第 4 步（改配置）继续。"
echo "★ 如果这次是自己改了代码重新打的包，见 DEPLOY.md 第 9 节「改前端代码」。"
