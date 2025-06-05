# 运维平台前端

## 技术架构

### 核心框架
- Vue 3：渐进式JavaScript框架
- Vue Router：Vue.js官方路由管理器
- Vuex：Vue.js的状态管理模式和库
- Element Plus：基于Vue 3的组件库

### 开发工具
- Vite：现代前端构建工具
- ESLint：JavaScript代码检查工具
- Axios：基于Promise的HTTP客户端

### 项目结构
```
web/
├── public/           # 静态资源目录
├── src/              # 源代码目录
│   ├── api/         # API接口
│   ├── assets/      # 资源文件
│   ├── components/  # 公共组件
│   ├── layout/      # 布局组件
│   ├── router/      # 路由配置
│   ├── store/       # Vuex状态管理
│   ├── styles/      # 全局样式
│   ├── utils/       # 工具函数
│   ├── views/       # 页面组件
│   ├── App.vue      # 根组件
│   └── main.js      # 入口文件
├── .eslintrc.js     # ESLint配置
├── .gitignore       # Git忽略文件
├── index.html       # HTML模板
├── package.json     # 项目配置
└── vite.config.js   # Vite配置
```

## Linux部署步骤

### 1. 环境准备
```bash
# 安装Node.js和npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 验证安装
node --version
npm --version
```

### 2. 安装项目依赖
```bash
# 安装依赖
npm install
```

### 3. 修改配置

创建生产环境配置文件 `.env.production`：
```env
# 生产环境API地址
VITE_APP_API_BASE_URL=http://your_api_domain/api
```

### 4. 构建项目
```bash
# 构建生产环境版本
npm run build
```

### 5. 配置Nginx

安装Nginx：
```bash
sudo apt install nginx
```

创建Nginx配置文件：
```bash
sudo nano /etc/nginx/sites-available/ops_platform_frontend
```

添加以下配置：
```nginx
server {
    listen 80;
    server_name your_domain;

    root /var/www/ops_platform_frontend/dist;
    index index.html;

    # 处理单页应用路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 静态资源缓存设置
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, no-transform";
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }
}
```

### 6. 部署文件
```bash
# 创建部署目录
sudo mkdir -p /var/www/ops_platform_frontend

# 复制构建文件到部署目录
sudo cp -r dist/* /var/www/ops_platform_frontend/

# 设置目录权限
sudo chown -R www-data:www-data /var/www/ops_platform_frontend
```

### 7. 启用配置
```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/ops_platform_frontend /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 8. 检查服务
```bash
# 检查Nginx状态
sudo systemctl status nginx
```

### 9. 设置自动部署（可选）

如果需要自动部署，可以创建部署脚本 `deploy.sh`：
```bash
#!/bin/bash

# 拉取最新代码
git pull

# 安装依赖
npm install

# 构建项目
npm run build

# 部署到生产环境
sudo rm -rf /var/www/ops_platform_frontend/*
sudo cp -r dist/* /var/www/ops_platform_frontend/
sudo chown -R www-data:www-data /var/www/ops_platform_frontend

# 重启Nginx
sudo systemctl restart nginx
```

设置脚本权限：
```bash
chmod +x deploy.sh
```

## 注意事项

1. 确保服务器防火墙允许HTTP/HTTPS流量
2. 建议配置HTTPS以提高安全性
3. 定期备份部署文件
4. 监控服务器资源使用情况
5. 保持依赖包的更新和安全补丁的及时应用