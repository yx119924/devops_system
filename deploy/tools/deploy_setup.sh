#!/bin/bash
set -e
cd /opt/devops-platform

# 生成随机密码
MYSQL_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 18)
REDIS_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 12)

# 写 .env（docker-compose 变量引用）
printf 'MYSQL_PASSWORD=%s\nREDIS_PASSWORD=%s\n' "$MYSQL_PASSWORD" "$REDIS_PASSWORD" > .env

# 生成 env.py 并替换数据库/redis 连接信息
cp backend/conf/env.example.py backend/conf/env.py
sed -i "s|DATABASE_HOST = '127.0.0.1'|DATABASE_HOST = '172.30.0.13'|" backend/conf/env.py
sed -i "s|REDIS_HOST = '127.0.0.1'|REDIS_HOST = '172.30.0.15'|" backend/conf/env.py
sed -i "s|DATABASE_PASSWORD = 'DVADMIN3'|DATABASE_PASSWORD = '$MYSQL_PASSWORD'|" backend/conf/env.py
sed -i "s|REDIS_PASSWORD = 'DVADMIN3'|REDIS_PASSWORD = '$REDIS_PASSWORD'|" backend/conf/env.py

# docker-compose 端口仅绑定本机（不暴露公网）
sed -i 's|- "3306:3306"|- "127.0.0.1:3306:3306"|' docker-compose.yml
sed -i 's|- "6379:6379"|- "127.0.0.1:6379:6379"|' docker-compose.yml

echo "=== .env ==="
cat .env
echo "=== env.py 关键配置 ==="
grep -E "DATABASE_HOST|DATABASE_PASSWORD|REDIS_HOST|REDIS_PASSWORD|DATABASE_ENGINE|DATABASE_NAME" backend/conf/env.py
echo "=== compose 端口 ==="
grep -nE "3306|6379" docker-compose.yml
echo "=== SETUP_DONE ==="
