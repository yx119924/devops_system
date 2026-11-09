# -*- coding: utf-8 -*-
"""巡检日报 · 结论文案生成（纯函数）

独立成一层的理由：页面展示和 Word 导出必须引用**同一份**文案。
如果两处各写一套，很快就会出现「页面说下降 11.9%、Word 说下降 12%」这种尴尬。

约定：每条结论、每条建议都必须带具体数字，不允许出现
「总体良好」「运行平稳」这类无法验证的表述 —— 除非数据本身就是零。
"""

def build_findings(d):
    """把数据算成人话。每条都带数字，禁止出现无数值的形容词。"""
    total = d["total"]
    prev = d["prev_total"]
    # ★ 必须用 severity_counts：severity_map 的键是「严重（critical）」这种展示串，
    #   dict() 之后 .get("critical") 恒为 0 —— 会写出「严重 0 条」而数据里明明有 3 条。
    sev = d.get("severity_counts") or {}
    out = []

    # 环比
    if prev > 0:
        delta = (total - prev) / prev * 100
        word = "下降" if delta < 0 else "上升"
        if abs(delta) < 0.1:
            out.append("当日累计产生告警 %d 条，与前一日（%d 条）基本持平。" % (total, prev))
        else:
            out.append("当日累计产生告警 %d 条，较前一日（%d 条）%s %.1f%%。"
                       % (total, prev, word, abs(delta)))
    else:
        out.append("当日累计产生告警 %d 条，前一日无告警记录。" % total)

    # 级别
    out.append("其中严重 %d 条、警告 %d 条、提示 %d 条，严重占比 %.1f%%。"
               % (sev.get("critical", 0), sev.get("warning", 0),
                  sev.get("info", 0), sev.get("critical", 0) / total * 100 if total else 0))

    # 类别集中度（领导视角：哪一类问题最多，而不是哪条规则响得最勤）
    cats = d.get("categories") or []
    if cats and total:
        top = cats[0]
        if top["ratio"] >= 30:
            out.append("从告警类别看，「%s」类 %d 条，占当日 %.1f%%，为最主要的问题来源"
                       "（其中以「%s」触发最多）。"
                       % (top["name"], top["count"], top["ratio"], top["top_type"]))
        else:
            spread = "、".join("%s %d 条" % (c["name"], c["count"]) for c in cats[:3])
            out.append("告警分散在 %d 个类别，占比最高的是「%s」（%.1f%%），前三类为 %s。"
                       % (len(cats), top["name"], top["ratio"], spread))

    # 类型集中度
    types = d["types"]
    if types:
        top3 = types[:3]
        top3_sum = sum(t["count"] for t in top3)
        share = top3_sum / total * 100 if total else 0
        desc = "、".join("%s（%d 条，%.1f%%）" % (t["name_cn"], t["count"], t["count"] / total * 100)
                        for t in top3)
        out.append("告警类型集中在 %s，三者合计占当日总量的 %.1f%%。" % (desc, share))

    # 时段峰值：滑动两小时窗口取最大，比单小时更能说明"爆发期"
    hh = d["hourly"]
    if hh and any(x["count"] for x in hh):
        best_i, best_sum = 0, -1
        for i in range(len(hh) - 1):
            s = hh[i]["count"] + hh[i + 1]["count"]
            if s > best_sum:
                best_i, best_sum = i, s
        out.append("告警发生高峰为 %02d:00—%02d:00，两小时合计 %d 条，占全日 %.1f%%"
                   "（其中 %02d 时单小时 %d 条）。"
                   % (hh[best_i]["hour"], hh[best_i]["hour"] + 2, best_sum,
                      best_sum / total * 100 if total else 0,
                      hh[best_i]["hour"], hh[best_i]["count"]))

    # 节点集中度
    nodes = d["nodes"]
    if nodes:
        top = nodes[0]
        out.append("涉及节点 %d 台，其中 %s 单日 %d 条（占 %.1f%%），为当日告警最集中节点。"
                   % (len(nodes), top["instance"], top["count"],
                      top["count"] / total * 100 if total else 0))

    # 未恢复
    un = d["unresolved"]
    if un:
        longest = max(un, key=lambda x: x["duration_hours"])
        out.append("截至报告生成，仍有 %d 条告警未恢复，最长持续 %d 小时 %d 分。"
                   % (len(un), int(longest["duration_hours"]),
                      int((longest["duration_hours"] % 1) * 60)))
    else:
        out.append("截至报告生成，当日告警已全部恢复，无遗留未闭环项。")

    return out


def build_suggestions(d):
    """建议必须挂在阈值和数字上，可追溯到具体表格行。"""
    total = d["total"]
    # ★ 必须用 severity_counts：severity_map 的键是「严重（critical）」这种展示串，
    #   dict() 之后 .get("critical") 恒为 0 —— 会写出「严重 0 条」而数据里明明有 3 条。
    sev = d.get("severity_counts") or {}
    out = []

    if sev.get("critical", 0) > 0:
        out.append("当日出现 %d 条严重级告警，建议逐条核对处理记录（见附表「告警明细」），"
                   "确认根因已消除而非仅恢复。" % sev["critical"])

    if d["unresolved"]:
        names = "、".join(u["alertname_cn"] for u in d["unresolved"][:3])
        out.append("尚有 %d 条告警未恢复（%s），建议优先处置后再出具本周汇总。"
                   % (len(d["unresolved"]), names))

    for n in d["nodes"][:2]:
        ratio = n["count"] / total * 100 if total else 0
        if ratio >= 25:
            out.append("节点 %s 当日告警占比 %.1f%%（%d/%d），显著高于其他节点，"
                       "建议对该机做一次资源与日志专项排查。"
                       % (n["instance"], ratio, n["count"], total))

    # 类别维度：占比过半说明是系统性问题，不是单点故障 —— 处置方式完全不同
    cats = d.get("categories") or []
    if cats and total and cats[0]["ratio"] >= 50:
        c = cats[0]
        out.append("「%s」类告警占当日 %.1f%%（%d/%d），已构成系统性问题而非个别节点故障，"
                   "建议沿该类别的探测链路整体排查，而不是逐条处理单点告警。"
                   % (c["name"], c["ratio"], c["count"], total))

    if any("测试规则" in n for n in (d.get("data_notes") or [])):
        out.append("告警规则中存在名称含 test / 测试 的调试用规则，建议停用，"
                   "避免污染日报与周报的统计口径。")

    top_type = d["types"][0] if d["types"] else None
    if top_type and total and top_type["count"] / total >= 0.2:
        out.append("「%s」占比达 %.1f%%，建议复核该规则的告警阈值是否偏敏感，"
                   "或对涉及节点做容量评估。"
                   % (top_type["name_cn"], top_type["count"] / total * 100))

    cover = d["scope"]
    if cover["targets_up"] < cover["targets_total"]:
        out.append("监控目标在线 %d/%d，有 %d 个 target 不可达，建议检查 exporter 与网络连通性。"
                   % (cover["targets_up"], cover["targets_total"],
                      cover["targets_total"] - cover["targets_up"]))

    if not out:
        out.append("当日无严重告警、无未恢复项、监控目标全部在线，无需专项处置；"
                   "建议保持现有巡检频次。")
    return out


