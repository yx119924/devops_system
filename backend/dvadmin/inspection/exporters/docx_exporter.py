# -*- coding: utf-8 -*-
"""巡检日报 · Word 渲染器

输入是 aggregate.build_report() 返回的报告结构，输出 .docx 字节流或文件。

设计原则
--------
  1. 渲染层不认识数据库，只认识报告结构 —— 换数据源不影响排版。
  2. 所有结论句由 build_findings() 从数据算出，模板里不出现任何
     「总体良好」「运行平稳」式措辞，除非数据本身真的为零。
  3. 中文字体必须同时设置 w:eastAsia，否则 Word 里会回退成宋体。
  4. pPr / tblPr / tcPr / trPr 的子元素顺序按 OOXML schema 插入（_insert_ordered），
     顺序错了 Word 会弹「文件内容有问题」，而 python-docx 读取时不校验。
"""

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ---------------------------------------------------------------- 配色与字体
CN_FONT = "微软雅黑"
MONO_FONT = "Consolas"

C_TITLE = "1F3864"      # 主标题 深蓝
C_HEAD = "2E75B6"       # 表头 / 分隔线 中蓝
C_BAND = "EAF1F8"       # 斑马纹 浅蓝
C_BORDER = "C9D6E5"     # 表格边框
C_TEXT = "262626"       # 正文
C_MUTED = "7F7F7F"      # 次要文字
C_CRIT = "C00000"       # 严重
C_WARN = "C55A11"       # 警告
C_INFO = "8496B0"       # 提示
C_OK = "548235"         # 正常


# ---------------------------------------------------------------- 底层工具
def _font(run, name=CN_FONT, size=None, bold=None, color=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def _para(doc_or_cell, text="", size=10.5, bold=False, color=C_TEXT,
          align=None, space_before=0, space_after=4, indent=None,
          line_spacing=1.5, name=CN_FONT):
    p = doc_or_cell.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line_spacing
    if indent is not None:
        pf.first_line_indent = Cm(indent)
    if align is not None:
        p.alignment = align
    if text:
        _font(p.add_run(text), name=name, size=size, bold=bold, color=color)
    return p


def _rich_para(doc, segments, size=10.5, indent=None, space_after=4, line_spacing=1.5):
    """segments = [(text, {bold/color/size}), ...] —— 用于句中强调数字。"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line_spacing
    if indent is not None:
        pf.first_line_indent = Cm(indent)
    for seg in segments:
        if isinstance(seg, str):
            _font(p.add_run(seg), size=size)
        else:
            text, style = seg
            _font(p.add_run(text), size=style.get("size", size),
                  bold=style.get("bold", False), color=style.get("color", C_TEXT))
    return p


# OOXML 对 pPr / tblPr / tcPr / trPr 的子元素顺序有强制要求。
# 顺序错了 Word 会弹「文件内容有问题」，而 python-docx 读取时不校验 —— 只有人肉打开才发现。
# 所以这里不用 append，一律按 schema 顺序插入。
PPR_ORDER = (
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
    "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
    "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE",
    "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
    "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
    "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle",
    "rPr", "sectPr", "pPrChange",
)
TBLPR_ORDER = (
    "tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
    "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
    "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription",
    "tblPrChange",
)
TCPR_ORDER = (
    "cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd",
    "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark",
    "headers", "cellIns", "cellDel", "cellMerge", "tcPrChange",
)
TRPR_ORDER = (
    "cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter",
    "cantSplit", "trHeight", "tblHeader", "tblCellSpacing", "jc", "hidden",
    "ins", "del", "trPrChange",
)


def _insert_ordered(parent, el, order):
    """按 schema 顺序把 el 插进 parent；已存在同标签的先移除（幂等）。"""
    tag = el.tag.split("}")[-1]
    if tag not in order:
        parent.append(el)
        return
    want = order.index(tag)
    for child in list(parent):
        ctag = child.tag.split("}")[-1]
        if ctag == tag:
            parent.remove(child)
            continue
        if ctag in order and order.index(ctag) > want:
            child.addprevious(el)
            return
    parent.append(el)


def _border(paragraph, color=C_HEAD, size=8):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    _insert_ordered(pPr, pBdr, PPR_ORDER)


def _section_title(doc, text, en=""):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16)
    pf.space_after = Pt(8)
    pf.keep_with_next = True
    _font(p.add_run(text), size=14, bold=True, color=C_TITLE)
    if en:
        _font(p.add_run("   " + en), size=8, color=C_MUTED)
    _border(p, C_HEAD, 8)
    return p


def _sub_title(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(10)
    pf.space_after = Pt(4)
    pf.keep_with_next = True
    _font(p.add_run(text), size=11, bold=True, color=C_HEAD)
    return p


def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    _insert_ordered(tcPr, shd, TCPR_ORDER)


def _cell_margins(table, top=60, bottom=60, left=100, right=100):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for tag, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement("w:" + tag)
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    _insert_ordered(tblPr, mar, TBLPR_ORDER)


def _table_borders(table, color=C_BORDER, size=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    _insert_ordered(tblPr, borders, TBLPR_ORDER)


def _write_cell(cell, text, size=9.5, bold=False, color=C_TEXT, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(1)
    pf.space_after = Pt(1)
    pf.line_spacing = 1.15
    _font(p.add_run(str(text)), size=size, bold=bold, color=color)


def _data_table(doc, headers, rows, widths, aligns=None, zebra=True,
                head_bg=C_HEAD, highlight_col=None, font_size=9.5):
    """widths 单位 cm；aligns 每列的对齐方式（默认左对齐）。"""
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _table_borders(table)
    _cell_margins(table)

    aligns = aligns or [WD_ALIGN_PARAGRAPH.LEFT] * len(headers)

    hdr = table.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    _insert_ordered(trPr, th, TRPR_ORDER)
    for i, h in enumerate(headers):
        c = hdr.cells[i]
        c.width = Cm(widths[i])
        _shade(c, head_bg)
        _write_cell(c, h, size=font_size, bold=True, color="FFFFFF",
                    align=WD_ALIGN_PARAGRAPH.CENTER)

    for r_i, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            c = cells[i]
            c.width = Cm(widths[i])
            color = C_TEXT
            bold = False
            if highlight_col is not None and i == highlight_col:
                color, bold = C_CRIT, True
            _write_cell(c, val, size=font_size, bold=bold, color=color, align=aligns[i])
            if zebra and r_i % 2 == 1:
                _shade(c, C_BAND)
    return table


def _kv_table(doc, pairs, widths=(3.6, 12.4)):
    """两列信息表，左侧浅蓝底作标签。"""
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _table_borders(table)
    _cell_margins(table, top=70, bottom=70)
    for k, v in pairs:
        cells = table.add_row().cells
        cells[0].width = Cm(widths[0])
        cells[1].width = Cm(widths[1])
        _shade(cells[0], C_BAND)
        _write_cell(cells[0], k, size=9.5, bold=True, color=C_TITLE)
        _write_cell(cells[1], v, size=9.5)
    return table


def _bar(text, value, max_value, width=20, color=C_HEAD):
    """用全角方块在表格里画条形图 —— 导出后肉眼可读，不依赖图片。"""
    if max_value <= 0:
        return ""
    n = int(round(value / max_value * width))
    return text + "  " + "█" * max(n, 0)


def _footer_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("第 "), size=8, color=C_MUTED)
    run = p.add_run()
    for tag, attr, txt in (
        ("w:fldChar", "begin", None),
        ("w:instrText", None, "PAGE"),
        ("w:fldChar", "end", None),
    ):
        el = OxmlElement(tag)
        if attr:
            el.set(qn("w:fldCharType"), attr)
        if txt:
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)
    _font(run, size=8, color=C_MUTED)
    _font(p.add_run(" 页"), size=8, color=C_MUTED)


# ---------------------------------------------------------------- 主渲染
def render(data, out_path):
    d = data
    sev = d.get("severity_counts") or {}
    doc = Document()

    # 页面
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.4)
    sec.right_margin = Cm(2.4)

    # 全局默认字体
    style = doc.styles["Normal"]
    style.font.name = CN_FONT
    style.font.size = Pt(10.5)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    _footer_page_number(sec)

    # ---- 报头
    # 标题固定为「运维巡检报告」，**不带平台品牌名**：品牌名改过一次（XwOps → DevOps），
    # 写进标题就得到处跟着改；日期才是区分日报/周报的唯一标识。
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    _font(p.add_run("运维巡检报告"), size=22, bold=True, color=C_TITLE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    _font(p.add_run("巡检日期：%s（%s）" % (d["date_cn"], d["weekday"])),
          size=10.5, color=C_TEXT)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("报告生成时间：%s    生成人：运维部" % d["generated_at"]),
          size=9, color=C_MUTED)
    _border(p, C_HEAD, 12)

    # ---- 一、巡检概况
    _section_title(doc, "一、巡检概况", "OVERVIEW")
    _para(doc, "本次巡检对平台纳管范围内的 IT 基础设施进行告警维度检查，"
               "范围为 %s 全天（00:00—24:00），数据取自 Prometheus 指标与告警平台事件库，"
               "覆盖以下监控对象：" % d["date_cn"],
          indent=0.74, space_after=8)

    _kv_table(doc, [
        ("巡检日期", "%s 00:00:00 — 23:59:59" % d["date"]),
        ("数据来源", d["source_desc"]),
        ("监控范围", "%d 个采集任务（%s）、%d 个 target、%d 条告警规则"
                    % (len(d["scope"]["jobs"]), "、".join(d["scope"]["jobs"]) or "—",
                       d["scope"]["targets_total"], d["scope"]["rules_total"])),
        ("目标在线", ("%d / %d（%.1f%%）"
                    % (d["scope"]["targets_up"], d["scope"]["targets_total"],
                       d["scope"]["targets_up"] * 100.0 / d["scope"]["targets_total"]))
                    if d["scope"]["targets_total"] else "未取到"),
        # ★ 必须按 severity_counts 取，不能按下标 severity_map[0..2]：
        #   真实数据里 info 经常为 0，此时 severity_map 只有两个元素，[2][1] 直接越界。
        ("告警总量", "%d 条（严重 %d / 警告 %d / 提示 %d）"
                    % (d["total"], sev.get("critical", 0),
                       sev.get("warning", 0), sev.get("info", 0))),
    ])

    # ---- 二、巡检内容
    _section_title(doc, "二、巡检内容", "SCOPE")
    items = [
        ("告警总量与级别分布", "统计当日产生的全部告警，按严重 / 警告 / 提示三档归类，并与前一日对比"),
        ("告警类别分布", "把规则名收敛为网络连通 / 主机资源 / 数据库中间件 / GPU / 业务探测 / "
                       "任务调度六类，定位问题来源属于哪个技术域"),
        ("告警类型分布", "按告警规则名称聚合，识别当日高频告警类型及其占比"),
        ("告警时段分布", "以小时为粒度还原告警发生节奏，定位集中爆发时段"),
        ("告警节点分布", "按告警来源实例聚合，识别单机告警集中情况"),
        ("监控覆盖检查", "核对 Prometheus 采集任务与 target 在线状态，确认巡检数据来源完整"),
        ("未恢复告警核查", "列出截至报告生成仍未恢复的告警项及其持续时长"),
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
        ["告警级别", "数量（条）", "占比", "环比前一日"],
        [
            [lab, str(cnt), "%.1f%%" % (cnt / d["total"] * 100 if d["total"] else 0),
             d["severity_delta"][i]]
            for i, (lab, cnt) in enumerate(d["severity_map"])
        ] + [["合计", str(d["total"]), "100.0%",
              ("%+d" % (d["total"] - d["prev_total"])) if d["prev_total"] else "—"]],
        widths=[4.4, 3.4, 3.2, 5.2],
        aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
    )

    if d["categories"]:
        _sub_title(doc, "3.2  告警类别分布")
        max_cat = max(c["count"] for c in d["categories"])
        _data_table(
            doc,
            ["序号", "告警类别", "数量", "占比", "主要来源", "分布"],
            [[str(i), c["name"], str(c["count"]), "%.1f%%" % c["ratio"],
              c["top_type"], _bar("", c["count"], max_cat, width=14)]
             for i, c in enumerate(d["categories"], 1)],
            widths=[1.2, 3.0, 1.5, 1.5, 5.6, 3.4],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        )

    if d["top_types"]:
        _sub_title(doc, "3.3  告警类型分布（TOP %d）" % len(d["top_types"]))
        max_cnt = max(t["count"] for t in d["top_types"])
        _data_table(
            doc,
            ["序号", "告警类型", "所属类别", "数量", "占比", "分布"],
            [[str(i), t["name_cn"], t["category"], str(t["count"]),
              "%.1f%%" % (t["count"] / d["total"] * 100 if d["total"] else 0),
              _bar("", t["count"], max_cnt, width=14)]
             for i, t in enumerate(d["top_types"], 1)],
            widths=[1.2, 5.2, 2.8, 1.5, 1.5, 4.0],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        )

    _sub_title(doc, "3.4  告警时段分布（0—23 时）")
    _data_table(
        doc,
        [str(i).zfill(2) for i in range(24)],
        [[str(h["count"]) for h in d["hourly"]]],
        widths=[0.67] * 24,
        aligns=[WD_ALIGN_PARAGRAPH.CENTER] * 24,
        zebra=False,
        font_size=8,
    )
    hh = d["hourly"]
    best_i, best_sum = 0, -1
    for i in range(len(hh) - 1):
        s = hh[i]["count"] + hh[i + 1]["count"]
        if s > best_sum:
            best_i, best_sum = i, s
    _para(doc, "峰值时段 %02d:00—%02d:00，两小时合计 %d 条，占全日 %.1f%%。"
               % (hh[best_i]["hour"], hh[best_i]["hour"] + 2, best_sum,
                  best_sum / d["total"] * 100 if d["total"] else 0),
          size=9, color=C_MUTED, space_before=4, space_after=8)

    if d["top_nodes"]:
        _sub_title(doc, "3.5  告警节点分布（TOP %d）" % len(d["top_nodes"]))
        _data_table(
            doc,
            ["序号", "节点 / 实例", "主机名", "数量", "占比", "主要告警类型"],
            [[str(i), n["instance"], n["hostname"] or "—", str(n["count"]),
              "%.1f%%" % (n["count"] / d["total"] * 100 if d["total"] else 0),
              n["top_type"]]
             for i, n in enumerate(d["top_nodes"], 1)],
            widths=[1.2, 4.2, 3.2, 1.6, 1.6, 4.4],
            aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        )

    _sub_title(doc, "3.6  监控覆盖检查")
    _data_table(
        doc,
        ["检查项", "期望值", "实际值", "结论"],
        [[r["item"], r["expect"], r["actual"], r["result"]] for r in d["coverage"]],
        widths=[4.6, 3.6, 3.4, 4.4],
        aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
    )

    if d["unresolved"]:
        _sub_title(doc, "3.7  未恢复告警")
        _data_table(
            doc,
            ["告警类型", "节点", "级别", "触发时间", "持续时长"],
            [[u["alertname_cn"], u["instance"], u["severity_cn"],
              u["starts_at"], "%.1f 小时" % u["duration_hours"]]
             for u in d["unresolved"]],
            widths=[4.4, 4.0, 1.8, 3.6, 2.4],
            aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
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
    for note in (d.get("data_notes") or []):
        _para(doc, "· " + note, size=8.5, color=C_MUTED,
              line_spacing=1.3, space_after=2)
    _para(doc, "说明：本报告由 DevOps 平台巡检模块自动生成，统计口径为「%s」，数据源为 %s。"
               "告警明细见同目录 Excel 附表。" % (d["caliber"], d["source_desc"]),
          size=8.5, color=C_MUTED, line_spacing=1.3)
    if d.get("extra_note"):
        _para(doc, d["extra_note"], size=8.5, color=C_MUTED, line_spacing=1.3)

    doc.save(out_path)
    return out_path
