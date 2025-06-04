CREATE TABLE `sys_users` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username` varchar(50) NOT NULL COMMENT '用户名',
    `password` varchar(100) NOT NULL COMMENT '密码',
    `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
    `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
    `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
    `avatar` varchar(255) DEFAULT NULL COMMENT '头像',
    `status` tinyint(1) DEFAULT 1 COMMENT '状态(0:禁用,1:启用)',
    `last_login` datetime DEFAULT NULL COMMENT '最后登录时间',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_username` (`username`),
    UNIQUE KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表';

### 2. 角色表 (sys_roles)
-- ```sql
CREATE TABLE `sys_roles` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '角色ID',
    `role_name` varchar(50) NOT NULL COMMENT '角色名称',
    `role_code` varchar(50) NOT NULL COMMENT '角色编码',
    `description` varchar(255) DEFAULT NULL COMMENT '角色描述',
    `status` tinyint(1) DEFAULT 1 COMMENT '状态(0:禁用,1:启用)',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

### 3. 用户角色关联表 (sys_user_roles)
-- ```sql
CREATE TABLE `sys_user_roles` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `user_id` bigint(20) NOT NULL COMMENT '用户ID',
    `role_id` bigint(20) NOT NULL COMMENT '角色ID',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_user_role` (`user_id`,`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

### 4. 权限表 (sys_permissions)
-- ```sql
CREATE TABLE `sys_permissions` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '权限ID',
    `parent_id` bigint(20) DEFAULT 0 COMMENT '父权限ID',
    `name` varchar(50) NOT NULL COMMENT '权限名称',
    `permission_code` varchar(100) NOT NULL COMMENT '权限标识',
    `permission_type` tinyint(1) NOT NULL COMMENT '类型(1:菜单,2:按钮,3:接口)',
    `path` varchar(255) DEFAULT NULL COMMENT '路由地址',
    `icon` varchar(100) DEFAULT NULL COMMENT '图标',
    `component` varchar(255) DEFAULT NULL COMMENT '组件路径',
    `sort` int(11) DEFAULT 0 COMMENT '排序',
    `status` tinyint(1) DEFAULT 1 COMMENT '状态(0:禁用,1:启用)',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_permission_code` (`permission_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

### 5. 角色权限关联表 (sys_role_permissions)
-- ```sql
CREATE TABLE `sys_role_permissions` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `role_id` bigint(20) NOT NULL COMMENT '角色ID',
    `permission_id` bigint(20) NOT NULL COMMENT '权限ID',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_role_permission` (`role_id`,`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

### 初始化SQL语句
-- ```sql
-- 插入超级管理员角色
INSERT INTO `sys_roles` (`role_name`, `role_code`, `description`) 
VALUES ('超级管理员', 'ROLE_ADMIN', '系统超级管理员');

-- 插入管理员用户（密码为 admin123 的MD5加密）
INSERT INTO `sys_users` (`username`, `password`, `nickname`, `email`, `status`) 
VALUES ('admin', 'e5cd3f675d2dd3ef9764f8523b8de2b7', '系统管理员', 'admin@example.com', 1);

-- 关联管理员用户和超级管理员角色
INSERT INTO `sys_user_roles` (`user_id`, `role_id`) 
VALUES (1, 1);

-- 插入基础权限
INSERT INTO `sys_permissions` (`parent_id`, `name`, `permission_code`, `permission_type`, `path`, `icon`, `component`, `sort`) VALUES
(0, '系统管理', 'system', 1, '/system', 'setting', NULL, 1),
(1, '用户管理', 'system:user', 1, '/system/user', 'user', 'system/user/index', 1),
(1, '角色管理', 'system:role', 1, '/system/role', 'team', 'system/role/index', 2),
(1, '权限管理', 'system:permission', 1, '/system/permission', 'safety', 'system/permission/index', 3);

-- 关联超级管理员角色和所有权限
INSERT INTO `sys_role_permissions` (`role_id`, `permission_id`)
SELECT 1, id FROM sys_permissions;