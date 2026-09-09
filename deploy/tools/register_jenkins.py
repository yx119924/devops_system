#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册 jenkins 模块到 settings.py(INSTALLED_APPS) 和 application/urls.py(路由)
幂等：已存在则跳过。在远程宿主机 /opt/devops-platform/backend 下运行。
"""
import re

BASE = "/opt/devops-platform/backend"
settings_path = f"{BASE}/application/settings.py"
urls_path = f"{BASE}/application/urls.py"


def patch_settings():
    with open(settings_path, "r", encoding="utf-8") as f:
        content = f.read()
    if '"dvadmin.jenkins"' in content:
        print("settings.py 已含 dvadmin.jenkins，跳过")
        return
    old = '    "dvadmin.alert",\n'
    new = '    "dvadmin.alert",\n    "dvadmin.jenkins",\n'
    assert old in content, "未找到 dvadmin.alert 锚点"
    content = content.replace(old, new, 1)
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("settings.py 已注册 dvadmin.jenkins")


def patch_urls():
    with open(urls_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "dvadmin.jenkins.urls" in content:
        print("urls.py 已含 api/jenkins，跳过")
        return
    old = '    path("api/alert/", include("dvadmin.alert.urls")),\n'
    new = '    path("api/alert/", include("dvadmin.alert.urls")),\n    path("api/jenkins/", include("dvadmin.jenkins.urls")),\n'
    assert old in content, "未找到 api/alert 锚点"
    content = content.replace(old, new, 1)
    with open(urls_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("urls.py 已注册 api/jenkins")


if __name__ == "__main__":
    patch_settings()
    patch_urls()
    print("=== 注册完成 ===")
