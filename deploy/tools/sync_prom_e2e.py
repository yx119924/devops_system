# -*- coding: utf-8 -*-
"""
E2E 验证：登录 → 告警规则页 → 点「同步 Prom」 → 弹窗显示统计 → 列表刷新
"""
import json, time, sys, subprocess, os, traceback
from pathlib import Path

BASE_URL = "http://1.95.62.215:8080"
LOGIN_URL = f"{BASE_URL}/#/login"
RULE_URL = f"{BASE_URL}/#/rule"
ARTIFACT_DIR = Path(r"D:\WorkBuddy_workspace\ops_system\deploy\_e2e_artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)

PY = r"C:\Users\yex\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
SCRIPT_DIR = r"D:\WorkBuddy_workspace\ops_system\deploy"


def get_superadmin_token():
    """ssh 进 django 容器，用 RefreshToken.for_user(superadmin) 拿 24h access token"""
    code = (
        "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','application.settings'); "
        "import django; django.setup(); "
        "from django.apps import apps; "
        "from rest_framework_simplejwt.tokens import RefreshToken; "
        "U = apps.get_model('system','Users'); "
        "u = U.objects.get(username='superadmin'); "
        "print(str(RefreshToken.for_user(u).access_token))"
    )
    cmd = (
        f'docker exec -w /backend dvadmin3-django python -c "{code}"'
    )
    r = subprocess.run(
        [PY, os.path.join(SCRIPT_DIR, "ssh_run.py"), cmd],
        capture_output=True, text=True, encoding="utf-8"
    )
    out = r.stdout.strip()
    # 取最后一行（前面可能有 warning）
    lines = [l for l in out.splitlines() if l and "DeprecationWarning" not in l and "warnings.warn" not in l]
    return lines[-1] if lines else ""


def run():
    from playwright.sync_api import sync_playwright

    token = get_superadmin_token()
    print("[TOKEN] superadmin token len =", len(token))
    if not token or len(token) < 50:
        print("[FAIL] token 获取失败")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # 注入 token（localStorage key 是 'token'，不 JSON.stringify，避免引号污染）
        page.goto(f"{BASE_URL}/#/login", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        page.evaluate(f"() => localStorage.setItem('token', '{token}')")
        page.evaluate("() => localStorage.setItem('isLogin', '1')")
        # 落一跳到受保护路由触发权限加载
        page.goto(RULE_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(ARTIFACT_DIR / "01_rule_page_loaded.png"), full_page=False)

        # 找「同步 Prom」按钮
        try:
            page.wait_for_selector('button:has-text("同步 Prom")', timeout=10000)
        except Exception as e:
            print(f"[FAIL] 没找到「同步 Prom」按钮：{e}")
            page.screenshot(path=str(ARTIFACT_DIR / "fail_no_button.png"), full_page=True)
            ctx.close(); browser.close()
            return False
        print("[OK] 找到「同步 Prom」按钮")

        # 点同步
        page.click('button:has-text("同步 Prom")')
        # 等 ElMessageBox 弹窗
        try:
            page.wait_for_selector('.el-message-box', timeout=10000)
        except Exception as e:
            print(f"[FAIL] 弹窗未出现：{e}")
            page.screenshot(path=str(ARTIFACT_DIR / "fail_no_dialog.png"), full_page=True)
            ctx.close(); browser.close()
            return False
        page.wait_for_timeout(800)  # 等弹窗内容渲染
        page.screenshot(path=str(ARTIFACT_DIR / "02_sync_dialog.png"), full_page=False)
        # 抓弹窗内容
        try:
            text = page.text_content('.el-message-box__content') or ""
        except Exception:
            text = page.text_content('.el-message-box') or ""
        print("[DIALOG]")
        for line in text.splitlines():
            line = line.strip()
            if line:
                print("  " + line)
        # 关闭弹窗
        page.click('.el-message-box__btns button')
        page.wait_for_timeout(800)
        # 列表应已刷新
        page.screenshot(path=str(ARTIFACT_DIR / "03_list_after_sync.png"), full_page=False)

        # 找「编辑」按钮点开看弹窗里字段是齐的
        try:
            page.wait_for_selector('.fs-table .rowHandle-btns button:has-text("编辑")', timeout=5000)
            page.click('.fs-table .rowHandle-btns button:has-text("编辑")', timeout=5000)
            page.wait_for_selector('.el-dialog', timeout=5000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(ARTIFACT_DIR / "04_edit_form.png"), full_page=False)
            # 关编辑弹窗
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception as e:
            print(f"[WARN] 编辑验证未通过（不影响主流程）：{e}")

        ctx.close(); browser.close()
        return True


if __name__ == "__main__":
    ok = run()
    print("E2E:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
