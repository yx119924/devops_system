#!/bin/bash
# =====================================================================
#  XwOps 平台 - 部署包打包脚本
#  用途：在【源服务器】上执行，把当前运行的系统打包成一个部署包，
#        拿到新服务器上解压 + docker load 后即可用 docker-compose 启动。
#
#  覆盖两种场景：
#    场景 A（完整部署）    ：自带 MySQL/Redis 容器
#    场景 B（外接已有 MySQL/Redis）：只起 web/django/celery，用 init/ 下的 SQL 导数据
#
#  执行位置：/opt/devops-platform（项目根目录）
#  用法：bash pack_deploy.sh
#  产出：/tmp/xwops_deploy_YYYYMMDD.tar.gz
# =====================================================================
set -e
cd /opt/devops-platform

PKG=/tmp/xwops_deploy
STAMP=$(date +%Y%m%d_%H%M%S)

echo "=============================================="
echo "[1/9] 停止业务容器（保证 MySQL/Redis 数据一致）"
echo "=============================================="
docker compose stop

echo ""
echo "[2/9] 导出镜像（docker save）"
echo "=============================================="
mkdir -p $PKG/images
docker save devops-platform-dvadmin3-web:latest    -o $PKG/images/web.tar
docker save devops-platform-dvadmin3-django:latest -o $PKG/images/django.tar
docker save devops-platform-dvadmin3-celery:latest -o $PKG/images/celery.tar
docker save mysql:8.0                              -o $PKG/images/mysql.tar
docker save redis:6.2.6-alpine                     -o $PKG/images/redis.tar
echo "镜像导出完成："
ls -lh $PKG/images/

echo ""
echo "[3/9] 打包后端代码（含 media 会话录像）"
echo "=============================================="
tar czf $PKG/backend.tar.gz backend/
echo "backend.tar.gz 生成完成"

echo ""
echo "[4/9] 打包 docker_env（nginx 配置 + MySQL/Redis 数据 + Dockerfile）"
echo "=============================================="
tar czf $PKG/docker_env.tar.gz docker_env/
echo "docker_env.tar.gz 生成完成"

echo ""
echo "[5/9] 拷贝 .env（数据库/Redis 密码）"
echo "=============================================="
cp .env $PKG/.env
echo ".env 已拷贝"

echo ""
echo "[6/9] 生成改造后的 docker-compose.yml（完整版，image + 端口开放）"
echo "=============================================="
cat > $PKG/docker-compose.yml <<'EOF'
version: "3"
services:
  dvadmin3-web:
    container_name: dvadmin3-web
    image: devops-platform-dvadmin3-web:latest
    ports:
      - "8080:8080"
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./docker_env/nginx/my.conf:/etc/nginx/conf.d/my.conf
      - ./backend/media:/backend/media
    expose:
      - "8080"
    restart: always
    networks:
      network:
        ipv4_address: 172.30.0.11

  dvadmin3-django:
    image: devops-platform-dvadmin3-django:latest
    container_name: dvadmin3-django
    working_dir: /backend
    depends_on:
      - dvadmin3-mysql
    environment:
      PYTHONUNBUFFERED: 1
      DATABASE_HOST: dvadmin3-mysql
      TZ: Asia/Shanghai
    volumes:
      - ./backend:/backend
      - ./logs/log:/var/log
    ports:
      - "8000:8000"
    expose:
      - "8000"
    restart: always
    networks:
      network:
        ipv4_address: 172.30.0.12

  dvadmin3-mysql:
    image: mysql:8.0
    container_name: dvadmin3-mysql
    privileged: true
    restart: always
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: "django-vue3-admin"
      TZ: Asia/Shanghai
    command:
      --wait_timeout=31536000
      --interactive_timeout=31536000
      --max_connections=1000
      --default-authentication-plugin=mysql_native_password
    volumes:
      - "./docker_env/mysql/data:/var/lib/mysql"
      - "./docker_env/mysql/conf.d:/etc/mysql/conf.d"
      - "./docker_env/mysql/logs:/logs"
    networks:
      network:
        ipv4_address: 172.30.0.13

  dvadmin3-celery:
    image: devops-platform-dvadmin3-celery:latest
    container_name: dvadmin3-celery
    working_dir: /backend
    depends_on:
      - dvadmin3-mysql
    environment:
      PYTHONUNBUFFERED: 1
      DATABASE_HOST: dvadmin3-mysql
      TZ: Asia/Shanghai
    volumes:
      - ./backend:/backend
      - ./logs/log:/var/log
    restart: always
    networks:
      network:
        ipv4_address: 172.30.0.14

  dvadmin3-redis:
    image: redis:6.2.6-alpine
    container_name: dvadmin3-redis
    restart: always
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./docker_env/redis/data:/data
      - ./docker_env/redis/redis.conf:/etc/redis/redis.conf
    ports:
      - "6379:6379"
    sysctls:
      - net.core.somaxconn=1024
    command: /bin/sh -c "echo 'vm.overcommit_memory = 1' >> /etc/sysctl.conf && redis-server /etc/redis/redis.conf --appendonly yes --requirepass ${REDIS_PASSWORD}"
    privileged: true
    networks:
      network:
        ipv4_address: 172.30.0.15

networks:
  network:
    ipam:
      driver: default
      config:
        - subnet: '172.30.0.0/16'
EOF
echo "完整版 docker-compose.yml 已生成"

echo ""
echo "[7/9] 生成外接版 docker-compose.external.yml（场景 B：只 3 容器）"
echo "=============================================="
cat > $PKG/docker-compose.external.yml <<'EOF'
version: "3"
services:
  dvadmin3-web:
    container_name: dvadmin3-web
    image: devops-platform-dvadmin3-web:latest
    ports:
      - "8080:8080"
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./docker_env/nginx/my.conf:/etc/nginx/conf.d/my.conf
      - ./backend/media:/backend/media
    expose:
      - "8080"
    restart: always
    networks:
      network:
        ipv4_address: 172.30.0.11

  dvadmin3-django:
    image: devops-platform-dvadmin3-django:latest
    container_name: dvadmin3-django
    working_dir: /backend
    environment:
      PYTHONUNBUFFERED: 1
      TZ: Asia/Shanghai
    volumes:
      - ./backend:/backend
      - ./logs/log:/var/log
    ports:
      - "8000:8000"
    expose:
      - "8000"
    restart: always
    networks:
      network:
        ipv4_address: 172.30.0.12

  dvadmin3-celery:
    image: devops-platform-dvadmin3-celery:latest
    container_name: dvadmin3-celery
    working_dir: /backend
    environment:
      PYTHONUNBUFFERED: 1
      TZ: Asia/Shanghai
    volumes:
      - ./backend:/backend
      - ./logs/log:/var/log
    restart: always
    networks:
      network:
        ipv4_address: 172.30.0.14

networks:
  network:
    ipam:
      driver: default
      config:
        - subnet: '172.30.0.0/16'
EOF
echo "外接版 docker-compose.external.yml 已生成"

echo ""
echo "[8/9] 现场导出初始化 SQL（建库 + 60 表 + 数据，5.7/8.0 通用）"
echo "=============================================="
mkdir -p $PKG/init
source .env   # 读取 MYSQL_PASSWORD
docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" dvadmin3-mysql mysqldump -uroot -h127.0.0.1 -P3306 \
  --default-character-set=utf8mb4 --single-transaction --routines --triggers \
  --databases django-vue3-admin > $PKG/init/xwops_init.sql 2>/tmp/xwops_dump.err || {
    echo "❌ mysqldump 失败："; cat /tmp/xwops_dump.err; exit 1; }

# 兼容转换：utf8mb3 -> utf8（5.7 不认识 utf8mb3），删除 8.0 的 CHECK 约束（5.7 不支持）
python3 - <<'PYEOF'
import re
p = "$PKG/init/xwops_init.sql"
with open(p, encoding="utf-8") as f:
    lines = f.readlines()
lines = [l.replace("utf8mb3", "utf8") for l in lines]
out = []
for l in lines:
    if "CONSTRAINT" in l and "CHECK (" in l:
        j = len(out) - 1
        while j >= 0 and out[j].strip() == "":
            j -= 1
        if j >= 0 and out[j].rstrip().endswith(","):
            out[j] = out[j].rstrip()[:-1] + "\n"
        continue
    out.append(l)
with open(p, "w", encoding="utf-8") as f:
    f.writelines(out)
print("SQL 兼容转换完成")
PYEOF
ls -lh $PKG/init/xwops_init.sql

# 生成内网建库导数据脚本
cat > $PKG/init/init_external.sh <<'EOF'
#!/bin/bash
# 内网 MySQL 建库 + 导数据脚本（场景 B）。改下面 4 个配置后执行：bash init_external.sh
MYSQL_HOST="192.168.1.100"
MYSQL_PORT="3306"
MYSQL_ADMIN_USER="root"
MYSQL_ADMIN_PASSWORD="你的MySQL管理员密码"
DB_NAME="django-vue3-admin"
CREATE_APP_USER="yes"
APP_USER="xwops"
APP_PASSWORD="请改成后端连接密码"

SQL_FILE="$(cd "$(dirname "$0")" && pwd)/xwops_init.sql"
[ -f "$SQL_FILE" ] || { echo "找不到 xwops_init.sql"; exit 1; }

MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_ADMIN_USER" \
  -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;" || exit 1
echo "[1/3] 建库完成"

MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_ADMIN_USER" \
  --default-character-set=utf8mb4 "$DB_NAME" < "$SQL_FILE" || exit 1
echo "[2/3] 数据导入完成"

if [ "$CREATE_APP_USER" = "yes" ]; then
  MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_ADMIN_USER" \
    -e "CREATE USER IF NOT EXISTS '$APP_USER'@'%' IDENTIFIED BY '$APP_PASSWORD'; GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$APP_USER'@'%'; FLUSH PRIVILEGES;" \
    && echo "[3/3] 后端账号 $APP_USER 已创建"
fi
echo "完成。请把 env.py 的 DATABASE_HOST/DATABASE_PASSWORD/REDIS_HOST/REDIS_PASSWORD 改成内网地址。"
EOF
chmod +x $PKG/init/init_external.sh
echo "init_external.sh 已生成"

echo ""
echo "[9/9] 恢复源服务器容器运行"
echo "=============================================="
docker compose start
echo "源服务器容器已恢复"

echo ""
echo "=============================================="
echo "打包总包..."
echo "=============================================="
cd /tmp
tar czf xwops_deploy_$STAMP.tar.gz xwops_deploy/
echo ""
echo "=============================================="
echo " 打包完成！部署包位置："
echo "   /tmp/xwops_deploy_$STAMP.tar.gz"
echo ""
echo " 大小："
ls -lh /tmp/xwops_deploy_$STAMP.tar.gz
echo "=============================================="
