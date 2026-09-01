#!/usr/bin/env python3
"""
XwOps 重置用户密码脚本

背景：
  导出到仓库的初始化 SQL（init/xwops_init.sql）出于安全考虑，
  已把 superadmin / admin / test 三个账号的密码哈希替换为占位符
  （pbkdf2_sha256$600000$REPLACE_ME_SALT$REPLACE_ME_HASH）。
  因此首次导入数据库后，这三个账号都【无法登录】，
  必须用本脚本为账号设置真实密码。

用法（在 django 容器内执行）：
  docker exec -it dvadmin3-django python reset_password.py superadmin 你的新密码

  或者把本脚本放到宿主机 backend/ 目录下，进入容器后执行：
  docker exec -it dvadmin3-django bash
  cd /backend
  python reset_password.py superadmin 你的新密码

说明：
  - DVAdmin 的密码机制是 pbkdf2(md5(明文)) 双重哈希，
    Users.set_password() 已被框架重写，内部会自动做 md5 再 pbkdf2，
    所以这里直接调用 u.set_password(明文) 即可，无需手动 md5。
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")

import django  # noqa: E402

django.setup()

from dvadmin.system.models import Users  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print("用法: python reset_password.py <用户名> <新密码>")
        print("示例: python reset_password.py superadmin XwOps@2026")
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    try:
        user = Users.objects.get(username=username)
    except Users.DoesNotExist:
        print(f"[错误] 用户 {username} 不存在")
        sys.exit(1)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    print(f"[成功] 用户 {username} 的密码已重置")


if __name__ == "__main__":
    main()
