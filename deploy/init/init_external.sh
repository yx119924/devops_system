#!/bin/bash
# =====================================================================
#  XwOps 平台 - 内网 MySQL 建库 + 导数据脚本（场景 B：外接已有 MySQL）
#
#  用途：在【能访问内网 MySQL 的机器】上执行（可以是 MySQL 服务器本机，
#        也可以是任意装了 mysql 客户端、能连到内网 MySQL 的机器）。
#
#  它会做三件事：
#    1. 创建数据库 django-vue3-admin（已存在则跳过）
#    2. 导入 xwops_init.sql（建表 + 全部业务数据）
#    3. （可选）创建一个专用账号 xwops 并授权，供后端连接
#
#  执行前，先修改下面【四个配置】。
#  用法：bash init_external.sh
# =====================================================================

# ================= 请修改这 4 个配置 =================
MYSQL_HOST="192.168.1.100"          # 内网 MySQL 地址（IP 或域名）
MYSQL_PORT="3306"                    # 内网 MySQL 端口
MYSQL_ADMIN_USER="root"              # 有建库权限的管理员账号
MYSQL_ADMIN_PASSWORD="你的MySQL管理员密码"   # 管理员密码
DB_NAME="django-vue3-admin"          # 数据库名（保持默认，不要改）

# 后端连接专用账号（可选，第 3 步会创建；不想建专用账号可跳过本段）
CREATE_APP_USER="yes"                # 填 "yes" 创建专用账号，其他值跳过
APP_USER="xwops"                     # 后端连接账号
APP_PASSWORD="请改成后端连接密码"      # 后端连接密码（记下来，要写进 env.py）
# =====================================================

SQL_FILE="$(cd "$(dirname "$0")" && pwd)/xwops_init.sql"

if [ ! -f "$SQL_FILE" ]; then
  echo "❌ 找不到 $SQL_FILE，请确认 xwops_init.sql 和本脚本在同一目录"
  exit 1
fi

echo "=============================================="
echo "[1/3] 建库：$DB_NAME"
echo "=============================================="
MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_ADMIN_USER" \
  -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
if [ $? -ne 0 ]; then
  echo "❌ 建库失败，请检查 MySQL 地址/账号/密码是否正确"
  exit 1
fi
echo "✅ 数据库 $DB_NAME 已就绪"

echo ""
echo "[2/3] 导入数据（建表 + 业务数据）"
echo "=============================================="
MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_ADMIN_USER" \
  --default-character-set=utf8mb4 "$DB_NAME" < "$SQL_FILE"
if [ $? -ne 0 ]; then
  echo "❌ 导入失败，请检查上方报错信息"
  exit 1
fi
echo "✅ 数据导入完成"

echo ""
echo "[3/3] 创建后端连接账号并授权"
echo "=============================================="
if [ "$CREATE_APP_USER" = "yes" ]; then
  MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_ADMIN_USER" \
    -e "CREATE USER IF NOT EXISTS '$APP_USER'@'%' IDENTIFIED BY '$APP_PASSWORD'; GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$APP_USER'@'%'; FLUSH PRIVILEGES;"
  if [ $? -ne 0 ]; then
    echo "⚠️  账号创建失败（可忽略，改用管理员账号连接也可），请手动执行上面的 GRANT 语句"
  else
    echo "✅ 后端连接账号已创建：$APP_USER / 密码见上方配置"
    echo ""
    echo "   请把下面两个值写进新服务器 backend/conf/env.py："
    echo "     DATABASE_USER = '$APP_USER'"
    echo "     DATABASE_PASSWORD = '$APP_PASSWORD'"
  fi
else
  echo "ℹ️  已跳过专用账号创建，请直接用管理员账号连接（env.py 填管理员账号密码）"
fi

echo ""
echo "=============================================="
echo " ✅ 内网 MySQL 初始化完成！"
echo ""
echo " 接下来回到新服务器，修改 backend/conf/env.py："
echo "   DATABASE_HOST   = '$MYSQL_HOST'"
echo "   DATABASE_PORT   = $MYSQL_PORT"
echo "   DATABASE_USER   = $APP_USER（或你的管理员账号）"
echo "   DATABASE_PASSWORD = 对应密码"
echo "=============================================="
