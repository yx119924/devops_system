#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册 jenkins 模块到 settings.py(INSTALLED_APPS) 和 application/urls.py(路由)
幂等：已存在则跳过。

★ 本仓库交付时 settings.py / urls.py 里 dvadmin.jenkins 已经注册完毕，
  正常从零部署**不需要**执行本脚本；保留它是为了以后新增 app 时作参考。

用法（django 容器内）：
    docker exec dvadmin3-django python register_jenkins.py
"""
import os
import re

# ★ 不写死部署路径：脚本自身就在 backend/ 根目录下，取所在目录即可。
#   容器内是 /backend，宿主机上无论部署到哪个路径都能正确工作。
BASE = os.environ.get("XWOPS_BACKEND") or os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(BASE, "application", "settings.py")
urls_path = os.path.join(BASE, "application", "urls.py")


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
