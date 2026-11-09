# -*- coding: utf-8 -*-
"""巡检周报 · Word 渲染器

与日报的区别（结构不同，所以不复用 render()）：
  · 多一张「每日告警明细」（周一到周日逐行，含相对日均的偏离）
  · 少「监控覆盖检查」「未恢复告警」——前者是瞬时值，后者是当天快照，放进周报会误导
  · 概况段带「日均」「环比上周」

排版工具（字体、表格、OOXML 顺序）全部复用 docx_exporter，避免两套实现走样。
"""

from .docx_exporter import (
    C_BAND, C_BORDER, C_HEAD, C_MUTED, C_TEXT, C_TITLE,
    CN_FONT, DOCX_AVAILABLE, DOCX_IMPORT_ERROR,
    PPR_ORDER, TBLPR_ORDER, TCPR_ORDER, TRPR_ORDER,   # noqa: F401（供自检脚本按名导入）
    Cm, Document, OxmlElement, Pt, RGBColor, WD_ALIGN_PARAGRAPH, WD_TABLE_ALIGNMENT, qn,
    _border, _cell_margins, _data_table, _font, _footer_page_number, _insert_ordered,
    _kv_table, _para, _rich_para, _section_title, _shade, _sub_title,
    _table_borders, _write_cell,
)

# ---------------------------------------------------------------- 主渲染
def render(data, out_path):
    if not DOCX_AVAILABLE:
        raise RuntimeError(
            "服务端缺少 python-docx 依赖（%s）。请在服务器执行："
            "docker compose build dvadmin3-django && docker compose up -d dvadmin3-django "
            "重建镜像后再导出 Word。" % DOCX_IMPORT_ERROR)

    d = data
    sev = d.get("severity_counts") or {}
    total = d.get("total", 0)
    days = d.get("days", 0)

    doc = Document()

    # ---- 页面
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.4)
    sec.right_margin = Cm(2.4)

    style = doc.styles["Normal"]
    style.font.name = CN_FONT
    style.font.size = Pt(10.5)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    _footer_page_number(sec)

    # ---- 报头（标题与日报一致，靠副标题区分周期）
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    _font(p.add_run("运维巡检报告"), size=22, bold=True, color=C_TITLE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    _font(p.add_run("%s　%s 至 %s（共 %d 天）"
                    % (d.get("week_label", ""), d.get("start", ""), d.get("end", ""), days)),
          size=10.5, color=C_TEXT)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("报告生成时间：%s　　生成人：运维部" % _now_text()),
          size=9, color=C_MUTED)
    _border(p, C_HEAD, 12)

    # ---- 一、巡检概况
    _section_title(doc, "一、巡检概况", "OVERVIEW")
    _para(doc, "本报告对平台纳管范围内的 IT 基础设施进行周期告警维度检查，"
               "统计区间为 %s 00:00:00 至 %s 23:59:59（自然周，周一至周日），"
               "数据取自 Prometheus 指标与告警平台事件库。"
               % (d.get("start", ""), d.get("end", "")),
          indent=0.74, space_after=8)

    _kv_table(doc, [
        ("巡检周期", "%s 至 %s（%d 天）"
                    % (d.get("start", ""), d.get("end", ""), days)),
        ("周期标识", d.get("week_label", "—")),
        ("数据来源", d.get("source_desc", "—")),
        ("告警总量", "%d 条（严重 %d / 警告 %d / 提示 %d）"
                    % (total, sev.get("critical", 0), sev.get("warning", 0),
                       sev.get("info", 0))),
        ("日均告警", "%.1f 条/天" % (d.get("avg_per_day") or 0)),
        ("环比上周", _delta_text(d)),
    ])

    # ---- 二、巡检内容
    _section_title(doc, "二、巡检内容", "SCOPE")
    items = [
        ("告警总量与级别分布", "统计周期内全部告警，按严重 / 警告 / 提示三档归类"),
        ("告警类别分布", "把规则名收敛为网络连通 / 主机资源 / 数据库中间件 / GPU / 业务探测 / 任务调度"),
        ("告警类型分布", "按告警规则名称聚合，识别周期内高频告警类型"),
        ("每日告警明细", "逐日还原告警量与级别构成，标注相对日均的偏离"),
        ("告警时段分布", "以小时为粒度还原全周告警节奏，定位集中爆发时段"),
        ("告警节点分布", "按告警来源聚合，识别单机告警集中情况"),
    ]
    for i, (name, desc) in enumerate(items, 1):
        _rich_para(doc, [
            ("%d. %s" % (i, name), {"bold": True, "color": C_TITLE}),
            ("  —  " + desc, {"color": C_TEXT}),
        ], size=10.5, space_after=3)

    # ---- 三、巡检结果
    _section_title(doc, "三、巡检结果", "FINDINGS")

    _sub_title(doc, "3.1  告警总量与级别分布")
    _data_table(
        doc,
        ["告警级别", "数量（条）", "占比"],
        [[lab, str(cnt), "%.1f%%" % (cnt * 100.0 / total if total else 0)]
         for lab, cnt in (d.get("severity_map") or _sev_pairs(sev))]
        + [["合计", str(total), "100.0%" if total else "0.0%"]],
        widths=[6.0, 5.1, 5.1],
        aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.CENTER],
    )

    if d.get("categories"):
        _sub_title(doc, "3.2  告警类别分布")
        _data_table(
            doc,
            ["序号", "告警类别", "数量（条）", "占比", "主要来源（该类占比最高的规则）"],
            [[str(i), c["name"], str(c["count"]), "%.1f%%" % c["ratio"],
              _top_type_of(d, c["name"])]
             for i, c in enumerate(d["categories"], 1)],
            widths=[1.2, 3.2, 2.2, 1.8, 7.8],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.LEFT],
        )

    if d.get("types"):
        _sub_title(doc, "3.3  告警类型分布（TOP %d）" % min(len(d["types"]), 10))
        _data_table(
            doc,
            ["序号", "告警类型", "所属类别", "数量（条）", "占比"],
            [[str(i), t["alertname"], t.get("category", "其他"), str(t["count"]),
              "%.1f%%" % t.get("ratio", 0)]
             for i, t in enumerate(d["types"][:10], 1)],
            widths=[1.2, 7.4, 3.8, 2.0, 1.8],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER],
        )

    # 3.4 每日明细 —— 周报独有的一张表
    if d.get("daily"):
        _sub_title(doc, "3.4  每日告警明细")
        avg = d.get("avg_per_day") or 0
        peak_date = (d.get("peak_day") or {}).get("date", "")
        rows = []
        for x in d["daily"]:
            cats = x.get("categories") or []
            main = ("、".join("%s（%d）" % (c["name"], c["count"]) for c in cats[:2])
                    if cats else "—")
            dev = "—"
            if avg:
                diff = x["total"] - avg
                dev = "持平" if abs(diff) < 0.05 else ("%+.1f" % diff)
            rows.append([x["date"], x.get("weekday", ""), str(x["total"]),
                         str(x.get("critical", 0)), str(x.get("warning", 0)),
                         str(x.get("info", 0)), main + ("　★峰值" if x["date"] == peak_date and x["total"] else "")])
        _data_table(
            doc,
            ["日期", "星期", "总量", "严重", "警告", "提示", "主要类别"],
            rows,
            widths=[2.6, 1.6, 1.8, 1.8, 1.8, 1.8, 4.8],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.LEFT],
        )
        _para(doc, "注：日均 %.1f 条/天；带「★峰值」的为周期内告警最集中的一天。"
                   % avg, size=9, color=C_MUTED, space_before=4, space_after=8)

    _sub_title(doc, "3.5  告警时段分布（0—23 时）")
    _data_table(
        doc,
        [str(i).zfill(2) for i in range(24)],
        [[str(h["count"]) for h in (d.get("hourly") or [{"count": 0}] * 24)]],
        widths=[0.67] * 24,
        aligns=[WD_ALIGN_PARAGRAPH.CENTER] * 24,
        zebra=False,
        font_size=8,
    )
    hh = d.get("hourly") or []
    if hh:
        best_i, best_sum = 0, -1
        for i in range(len(hh) - 1):
            s = hh[i]["count"] + hh[i + 1]["count"]
            if s > best_sum:
                best_i, best_sum = i, s
        _para(doc, "全周高峰时段 %02d:00—%02d:00，两小时合计 %d 条，占周期总量 %.1f%%。"
                   % (hh[best_i]["hour"], hh[best_i]["hour"] + 2, best_sum,
                      best_sum * 100.0 / total if total else 0),
              size=9, color=C_MUTED, space_before=4, space_after=8)

    if d.get("nodes"):
        _sub_title(doc, "3.6  告警节点分布（TOP %d）" % min(len(d["nodes"]), 10))
        _data_table(
            doc,
            ["序号", "节点 / 实例", "主机名", "数量（条）", "占比"],
            [[str(i), n["instance"], n.get("hostname") or "—", str(n["count"]),
              "%.1f%%" % n.get("ratio", 0)]
             for i, n in enumerate(d["nodes"][:10], 1)],
            widths=[1.2, 5.4, 4.4, 2.6, 2.6],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER],
        )

    # ---- 四、巡检结论
    _section_title(doc, "四、巡检结论", "CONCLUSION")
    for line in (d.get("findings") or []):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.5
        _font(p.add_run(line), size=10.5)

    # ---- 五、巡检建议
    _section_title(doc, "五、巡检建议", "RECOMMENDATION")
    for i, line in enumerate(d.get("suggestions") or [], 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        _font(p.add_run("%d. " % i), size=10.5, bold=True, color=C_TITLE)
        _font(p.add_run(line), size=10.5)

    # ---- 附注
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    _border(p, "E0E0E0", 4)
    _para(doc, "说明：本报告由巡检模块按自然周自动生成。%s" % (d.get("caliber") or ""),
          size=8.5, color=C_MUTED, line_spacing=1.3)
    _para(doc, "经 Alertmanager 独立 route 分流、未回调平台的告警不在此列。",
          size=8.5, color=C_MUTED, line_spacing=1.3)

    doc.save(out_path)
    return out_path


# ---------------------------------------------------------------- 小工具
def _now_text():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _sev_pairs(sev):
    lab = (("critical", "严重"), ("warning", "警告"), ("info", "提示"))
    return [("%s（%s）" % (cn, k), sev.get(k, 0)) for k, cn in lab if sev.get(k)]


def _delta_text(d):
    total = d.get("total") or 0
    prev = d.get("prev_total") or 0
    if not prev:
        return "上周无告警，无可比基数"
    diff = total - prev
    if diff == 0:
        return "与上周持平（%d 条）" % prev
    pct = diff * 100.0 / prev
    return "%s %d 条（%s%.1f%%），上周 %d 条" % (
        "上升" if diff > 0 else "下降", abs(diff),
        "+" if diff > 0 else "-", abs(pct), prev)


def _top_type_of(d, cat_name):
    """某类别下触发次数最多的规则名 —— 日报从 categories.top_type 取，周报的合并结构里没有，得反查。"""
    best, best_n = "", -1
    for t in d.get("types") or []:
        if t.get("category") == cat_name and t["count"] > best_n:
            best, best_n = t["alertname"], t["count"]
    return best or "—"
