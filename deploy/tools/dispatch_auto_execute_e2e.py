# -*- coding: utf-8 -*-
"""
命令下发「自动执行」回归测试：API 层验证

背景：用户多次反馈"创建分发任务后状态卡在 pending、看不到结果"。
修复：deploy/dispatch/web/crud.tsx 的 addRequest 改为「POST 成功后自动调 doExecute」，
     避免「建→点执行」两次操作的体感割裂。

本测试模拟 addRequest 的内部行为：
  1. POST /api/bastion/dispatch/ 创建 → 拿到 id
  2. POST /api/bastion/dispatch/{id}/execute/ → 同步执行所有 item
  3. 验证 status 流转：pending → success（且 items 有 stdout）
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
import django
django.setup()

from dvadmin.bastion.models import CommandDispatch, CommandDispatchItem
from dvadmin.bastion.executor import execute_dispatch


def main():
    print("=" * 60)
    print("命令下发「创建即执行」API 层验证")
    print("=" * 60)

    # 1. 模拟前端 addRequest 内部行为
    d = CommandDispatch.objects.create(
        name="test-auto-execute",
        command="echo 'XwOps dispatch auto-execute test' && uname -n",
        credential_id=2,
        targets=[{"server_id": 1, "label": "1.95.62.215", "ip": "1.95.62.215", "ssh_port": 22}],
        timeout=10,
        max_workers=1,
        status="pending",
    )
    CommandDispatchItem.objects.create(
        dispatch=d, server_id=1, label="1.95.62.215", ip="1.95.62.215", ssh_port=22, status="pending",
    )
    print(f"\n[1] POST /api/bastion/dispatch/  →  id={d.id}, status={d.status}")

    # 2. 模拟 doExecute 自动调用
    d2 = execute_dispatch(d.id)
    print(f"[2] POST /api/bastion/dispatch/{d.id}/execute/  →  status={d2.status}, "
          f"total={d2.total}, success={d2.success_count}")

    # 3. 验证
    items = list(CommandDispatchItem.objects.filter(dispatch=d))
    if not items:
        print("[FAIL] 没有 item 记录")
        return False
    it = items[0]
    print(f"[3] items[0]: status={it.status}, exit={it.exit_code}, duration={it.duration}s")
    if it.stdout:
        print(f"    stdout: {it.stdout[:100]!r}")
    if it.error:
        print(f"    error: {it.error[:200]}")

    # 断言
    assert d2.status == "success", f"期望 status=success，实际 {d2.status}"
    assert it.status == "success", f"item 期望 status=success，实际 {it.status}"
    assert it.exit_code == 0
    assert "XwOps dispatch" in (it.stdout or "")
    assert "ecs" in (it.stdout or "") or "hostname" in (it.stdout or "")

    print("\n[OK] 状态从 pending → success，stdout 含命令输出 ✅")

    # 清理
    CommandDispatchItem.objects.filter(dispatch=d).delete()
    d.delete()
    print("（测试数据已清理）")
    return True


if __name__ == "__main__":
    import sys
    ok = main()
    sys.exit(0 if ok else 1)
