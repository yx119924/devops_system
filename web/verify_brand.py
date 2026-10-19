#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌换装离线门禁 —— 图标 / 站点标题 / 登录页页脚 / 登录后页脚移除

用法（在仓库根或任意目录均可）：
    python web/verify_brand.py

退出码：0 = 全绿；1 = 存在失败项

设计约束（来自项目 AGENTS.md §二）：
  · 必须能对「改动前原件」跑出红灯，否则说明断言太弱、抓不住问题
  · 只断言 devops_system/web 下的真实源码，不验任何副本
"""

import sys
import hashlib
import pathlib

WEB = pathlib.Path(__file__).resolve().parent
SRC = WEB / "src"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def read(rel, base=WEB):
    p = base / rel
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def exists(rel, base=WEB):
    return (base / rel).exists()


def md5(rel, base=WEB):
    p = base / rel
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else ""


# ---------------------------------------------------------------- 1. 图标
print("[1] 图标")
mini = read("src/assets/logo-mini.svg")
favicon = read("public/favicon.svg")

check("logo-mini.svg 存在", mini is not None)
check("public/favicon.svg 存在", favicon is not None)

if mini is not None and favicon is not None:
    check(
        "两份 SVG 内容完全一致（避免页面/标签页图标不一致）",
        md5("src/assets/logo-mini.svg") == md5("public/favicon.svg"),
        "md5 mini=%s favicon=%s" % (md5("src/assets/logo-mini.svg"), md5("public/favicon.svg")),
    )
    for label, content in (("logo-mini", mini), ("favicon", favicon)):
        check(
            "%s 已改为终端提示符 >_" % label,
            "M19 21 L31 32 L19 43" in content and "M36 43 L46 43" in content,
        )
        check("%s 不再包含 Xw 文字" % label, ">Xw<" not in content)
        check("%s 仍带圆角底板" % label, 'rx="14"' in content)

# ---------------------------------------------------------------- 2. 站点标题
print("[2] 站点标题")
html = read("index.html") or ""
check("<title> 为 DevOps", "<title>DevOps</title>" in html)
check("index.html 不含 XwOps", "XwOps" not in html)

tc = read("src/stores/themeConfig.ts") or ""
check("globalTitle 为 DevOps", "globalTitle: 'DevOps'" in tc)
check("globalViceTitle 为 DevOps", "globalViceTitle: 'DevOps'" in tc)
check("globalViceTitleMsg 为 运维管理平台", "globalViceTitleMsg: '运维管理平台'" in tc)

app = read("src/App.vue") or ""
m = None
for line in app.splitlines():
    if "themeConfigVersion = " in line:
        m = line.split("=", 1)[1].strip().strip("'\"")
        break
check("主题缓存版本号已提升（否则老用户缓存会盖住新标题）", m is not None and m != "1.0.0", "当前=%s" % m)
check("清缓存改为精准清理，不清 token（避免全员掉登录）", "Local.clear()" not in app)

# ---------------------------------------------------------------- 3. 登录页页脚
print("[3] 登录页页脚")
login = read("src/views/system/login/index.vue") or ""
check("登录页不含 XwOps", "XwOps" not in login)
for word in ("help_url", "privacy_url", "clause_url"):
    check("登录页已移除 %s 链接" % word, word not in login)
check("登录页已移除 帮助/隐私/条款 文案 key", "pages.login.footer" not in login)
check("登录页版权行含 DevOps", "DevOps" in login or "运维管理平台" in login)
check("getBaseURL 已无孤立引用", "getBaseURL" not in login)

# ---------------------------------------------------------------- 4. 登录后页脚（彻底移除）
print("[4] 登录后页脚")
check("layout/footer/index.vue 已删除", not exists("src/layout/footer/index.vue"))
check("layout/footer 目录已不存在", not exists("src/layout/footer"))

main = read("src/layout/component/main.vue") or ""
check("main.vue 不再挂载 LayoutFooter", "LayoutFooter" not in main)
check("main.vue 不再残留 isFooter 计算属性", "isFooter" not in main)

setings = read("src/layout/navBars/breadcrumb/setings.vue") or ""
check("设置面板已移除页脚开关", "isFooter" not in setings)

for lang in ("zh-cn", "en", "zh-tw"):
    t = read("src/i18n/lang/%s.ts" % lang) or ""
    check("i18n/%s 已移除页脚版权文案" % lang, "Powered by" not in t)
    check("i18n/%s 已移除页脚开关文案" % lang, "fourIsFooter" not in t)

# ---------------------------------------------------------------- 5. 全站残留扫描
print("[5] 全站 XwOps 残留")
EXCLUDE_DIRS = {"node_modules", "dist", ".git"}
hits = []
for p in list(WEB.rglob("*.vue")) + list(WEB.rglob("*.ts")) + list(WEB.rglob("*.html")) + list(WEB.rglob("*.svg")):
    if any(part in EXCLUDE_DIRS for part in p.parts):
        continue
    try:
        if "XwOps" in p.read_text(encoding="utf-8"):
            hits.append(str(p.relative_to(WEB)))
    except (UnicodeDecodeError, OSError):
        pass
check("web 源码中不再出现 XwOps", not hits, "残留: %s" % ", ".join(hits))

# ---------------------------------------------------------------- 汇总
passed = sum(1 for _, ok, _ in results if ok)
failed = len(results) - passed

print()
for name, ok, detail in results:
    if not ok:
        print("  FAIL  %s%s" % (name, ("  <- " + detail) if detail else ""))
print()
print("=" * 60)
print("总计 %d 项断言：通过 %d，失败 %d" % (len(results), passed, failed))
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
