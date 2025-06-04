# 运维平台后端

## 技术架构

### 后端框架
- Django 4.2.7：Python Web框架
- Django REST Framework：RESTful API开发框架
- djangorestframework-simplejwt：JWT认证
- django-cors-headers：处理跨域请求
- mysqlclient：MySQL数据库驱动
- python-dotenv：环境变量管理

### 数据库
- MySQL：关系型数据库

### 项目结构
```
ops_platform/
├── apps/                # 应用目录
│   └── system/         # 系统管理模块
│       ├── migrations/ # 数据库迁移文件
│       ├── models.py   # 数据模型
│       ├── serializers.py # 序列化器
│       ├── urls.py     # URL配置
│       └── views.py    # 视图函数
├── ops_platform/       # 项目配置目录
│   ├── settings.py    # 项目设置
│   ├── urls.py       # 主URL配置
│   └── wsgi.py       # WSGI配置
└── manage.py          # 项目管理脚本
```

## Linux部署步骤

### 1. 环境准备
```bash
# 安装Python3和pip
sudo apt update
sudo apt install python3 python3-pip

# 安装MySQL
sudo apt install mysql-server

# 安装Python开发包和MySQL开发包（用于mysqlclient）
sudo apt install python3-dev default-libmysqlclient-dev build-essential
```

### 2. 创建项目目录
```bash
sudo mkdir -p /var/www/ops_platform
sudo chown -R $USER:$USER /var/www/ops_platform
```

### 3. 创建虚拟环境
```bash
python3 -m venv /var/www/ops_platform/venv
source /var/www/ops_platform/venv/bin/activate
```

### 4. 安装依赖
```bash
pip install -r requirements.txt
```

### 5. 修改配置文件
编辑 `ops_platform/settings.py`：
```python
# 关闭调试模式
DEBUG = False

# 设置允许的主机
ALLOWED_HOSTS = ['your_domain_or_ip']

# 配置数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'devops',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# 配置静态文件
STATIC_ROOT = '/var/www/ops_platform/static'
```

### 6. 数据库迁移
```bash
python manage.py migrate
```

### 7. 收集静态文件
```bash
python manage.py collectstatic
```

### 8. 安装和配置Gunicorn
```bash
pip install gunicorn

# 创建Gunicorn配置文件
cat > /var/www/ops_platform/gunicorn_config.py << EOF
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
keepalive = 60
max_requests = 10000
max_requests_jitter = 1000
EOF
```

### 9. 配置Systemd服务
```bash
sudo nano /etc/systemd/system/ops_platform.service
```

添加以下内容：
```ini
[Unit]
Description=Ops Platform Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ops_platform
EnvironmentFile=/var/www/ops_platform/.env
ExecStart=/var/www/ops_platform/venv/bin/gunicorn \
          --config /var/www/ops_platform/gunicorn_config.py \
          ops_platform.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 10. 配置Nginx
```bash
sudo nano /etc/nginx/sites-available/ops_platform
```

添加以下内容：
```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location /static/ {
        root /var/www/ops_platform;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 11. 启动服务
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/ops_platform /etc/nginx/sites-enabled/

# 测试Nginx配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx

# 启动应用服务
sudo systemctl start ops_platform

# 设置开机自启
sudo systemctl enable ops_platform
```

### 12. 检查服务状态
```bash
sudo systemctl status ops_platform
sudo systemctl status nginx
```