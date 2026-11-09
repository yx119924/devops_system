# -*- coding: utf-8 -*-
"""巡检日报 · Excel 明细附表渲染器

定位：不是给领导看的主报告，是给运维自己和主管下钻用的数据底稿。
  1. 7 个 sheet：概况 / 级别 / 类别 / 类型 / 时段 / 节点 / 告警明细
  2. 表头配色与 Word 版一致，冻结首行，数字居中
  3. 明细 sheet 数据直接来自 alert_event 原始事件，带自动筛选，
     严重项标红、未恢复项标黄
"""
import datetime as dt

# ★ 与 docx_exporter 同理：可选依赖缺失只让该功能不可用，不能拖垮整个 Django 启动。
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    XLSX_AVAILABLE = True
    XLSX_IMPORT_ERROR = ""
except ImportError as _exc:                                  # noqa: BLE001
    XLSX_AVAILABLE = False
    XLSX_IMPORT_ERROR = str(_exc)
    Workbook = None                                          # type: ignore
    Alignment = Border = Font = PatternFill = Side = None    # type: ignore
    get_column_letter = None                                 # type: ignore

C_TITLE = "1F3864"
C_HEAD = "2E75B6"
C_BAND = "EAF1F8"
C_BORDER = "C9D6E5"
C_CRIT = "C00000"

CN = "微软雅黑"
if XLSX_AVAILABLE:
    THIN = Side(style="thin", color=C_BORDER)
    BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
else:
    # 依赖缺失时不能在模块加载阶段构造 openpyxl 对象，否则一样炸在 import 上
    THIN = BOX = None


def _sheet_title(ws, text, ncols, sub=None):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(row=1, column=1, value=text)
    c.font = Font(name=CN, size=13, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=C_TITLE)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 28
    if sub:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
        c = ws.cell(row=2, column=1, value=sub)
        c.font = Font(name=CN, size=9, color="595959")
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[2].height = 18
        return 3
    return 2


def _header_row(ws, row, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.font = Font(name=CN, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=C_HEAD)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BOX
    ws.row_dimensions[row].height = 22


def _body(ws, start_row, rows, aligns=None, zebra=True, widths=None):
    aligns = aligns or ["left"] * len(rows[0])
    for r_i, row in enumerate(rows):
        r = start_row + r_i
        for c_i, val in enumerate(row, 1):
            c = ws.cell(row=r, column=c_i, value=val)
            c.font = Font(name=CN, size=10, color="262626")
            c.alignment = Alignment(horizontal=aligns[c_i - 1], vertical="center")
            c.border = BOX
            if zebra and r_i % 2 == 1:
                c.fill = PatternFill("solid", fgColor=C_BAND)
        ws.row_dimensions[r].height = 20
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def _pct(n, total):
    """百分比。total 为 0 时返回 0.0 —— 零告警日不能让报表除零崩掉。"""
    return n * 100.0 / total if total else 0.0


def _build_details(d):
    """明细直接取自 aggregate 输出的 d["details"]。

    ★ 绝不能再「按汇总数反推」——那样只会造出一批看起来自洽、实际不存在的告警，
      交给领导就是数据造假。没有原始事件就老老实实输出空表。
    """
    return [[r["starts_at"], r["alertname"], r["category"], r["severity_cn"],
             r["instance"], r["hostname"] or "—", r["status"],
             r["ends_at"], r["duration"]]
            for r in (d.get("details") or [])]


def render(d, out_path):
    if not XLSX_AVAILABLE:
        raise RuntimeError(
            "服务端缺少 openpyxl 依赖（%s）。请重建 django 镜像后再导出 Excel。" % XLSX_IMPORT_ERROR)
    sev = d.get("severity_counts") or {}
    wb = Workbook()

    # ---------------- Sheet 1 巡检概况
    ws = wb.active
    ws.title = "巡检概况"
    r = _sheet_title(ws, "运维巡检报告", 4,
                     "巡检日期 %s（%s）　生成时间 %s" % (d["date_cn"], d["weekday"], d["generated_at"]))
    _header_row(ws, r, ["项目", "内容", "", ""])
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
    r += 1
    kv = [
        ("巡检日期", "%s 00:00:00 — 23:59:59" % d["date"]),
        ("数据来源", d["source_desc"]),
        ("统计口径", d["caliber"]),
        ("监控任务", "%d 个（%s）" % (len(d["scope"]["jobs"]),
                                   "、".join(d["scope"]["jobs"]) or "—")),
        ("监控目标", ("%d 个，在线 %d 个（%.1f%%）"
         % (d["scope"]["targets_total"], d["scope"]["targets_up"],
            d["scope"]["targets_up"] * 100.0 / d["scope"]["targets_total"]))
         if d["scope"]["targets_total"] else "未取到"),
        ("告警规则", "%d 条" % d["scope"]["rules_total"]),
        ("告警总量", "%d 条" % d["total"]),
        # ★ 按 severity_counts 取，不能用 severity_map 下标：info 为 0 时该列表只有两项
        ("级别分布", "严重 %d / 警告 %d / 提示 %d"
         % (sev.get("critical", 0), sev.get("warning", 0), sev.get("info", 0))),
        ("告警类型数", "%d 种" % len(d["types"])),
        ("涉及节点数", "%d 台" % len(d["nodes"])),
        ("未恢复告警", "%d 条" % len(d["unresolved"])),
    ]
    for k, v in kv:
        c = ws.cell(row=r, column=1, value=k)
        c.font = Font(name=CN, size=10, bold=True, color=C_TITLE)
        c.fill = PatternFill("solid", fgColor=C_BAND)
        c.alignment = Alignment(vertical="center", indent=1)
        c.border = BOX
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        c = ws.cell(row=r, column=2, value=v)
        c.font = Font(name=CN, size=10, color="262626")
        c.alignment = Alignment(vertical="center", indent=1, wrap_text=True)
        c.border = BOX
        ws.row_dimensions[r].height = 22
        r += 1
    for i, w in enumerate([16, 30, 22, 30], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 2 级别分布
    ws = wb.create_sheet("级别分布")
    r = _sheet_title(ws, "3.1  告警总量与级别分布", 4)
    _header_row(ws, r, ["告警级别", "数量（条）", "占比", "环比前一日"])
    r += 1
    rows, acc = [], 0
    for i, (lab, cnt) in enumerate(d["severity_map"]):
        acc += cnt
        rows.append([lab, cnt, "%.1f%%" % _pct(cnt, d["total"]), d["severity_delta"][i]])
    rows.append(["合计", acc, "100.0%", "—"])
    _body(ws, r, rows, ["left", "center", "center", "center"], True, [24, 14, 12, 16])
    for c_i in range(1, 5):
        c = ws.cell(row=r + len(rows) - 1, column=c_i)
        c.font = Font(name=CN, size=10, bold=True, color=C_TITLE, )
        c.fill = PatternFill("solid", fgColor=C_BAND)
    # 严重标红
    ws.cell(row=r, column=2).font = Font(name=CN, size=10, bold=True, color=C_CRIT)
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 3 类别分布
    if d.get("categories"):
        ws = wb.create_sheet("类别分布")
        r = _sheet_title(ws, "3.2  告警类别分布", 5)
        _header_row(ws, r, ["序号", "告警类别", "数量（条）", "占比", "主要来源"])
        r += 1
        rows = [[i, c["name"], c["count"], "%.1f%%" % c["ratio"], c["top_type"]]
                for i, c in enumerate(d["categories"], 1)]
        _body(ws, r, rows, ["center", "left", "center", "center", "left"],
              True, [8, 18, 12, 10, 44])
        ws.freeze_panes = "A%d" % r
        ws.sheet_view.showGridLines = False

    # ---------------- Sheet 4 类型分布
    ws = wb.create_sheet("类型分布")
    r = _sheet_title(ws, "3.3  告警类型分布（共 %d 种）" % len(d["types"]), 6)
    _header_row(ws, r, ["序号", "告警类型", "所属类别", "数量（条）", "占比", "累计占比"])
    r += 1
    rows, acc = [], 0
    for i, t in enumerate(d["types"], 1):
        acc += t["count"]
        rows.append([i, t["name_cn"], t["category"], t["count"],
                     "%.1f%%" % _pct(t["count"], d["total"]),
                     "%.1f%%" % _pct(acc, d["total"])])
    _body(ws, r, rows, ["center", "left", "left", "center", "center", "center"],
          True, [8, 30, 16, 12, 10, 12])
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 5 时段分布
    ws = wb.create_sheet("时段分布")
    r = _sheet_title(ws, "3.4  告警时段分布（0—23 时）", 4)
    _header_row(ws, r, ["时段", "数量（条）", "占全日", "分布"])
    r += 1
    mx = max(h["count"] for h in d["hourly"]) or 1
    rows = [["%02d:00—%02d:00" % (h["hour"], h["hour"] + 1), h["count"],
             "%.1f%%" % _pct(h["count"], d["total"]),
             "█" * int(round(h["count"] / mx * 24))]
            for h in d["hourly"]]
    _body(ws, r, rows, ["center", "center", "center", "left"], True, [16, 12, 10, 30])
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 6 节点分布（全部列出，Excel 不截断，便于下钻）
    ws = wb.create_sheet("节点分布")
    r = _sheet_title(ws, "3.5  告警节点分布（共 %d 个）" % len(d["nodes"]), 6)
    _header_row(ws, r, ["序号", "节点 / 实例", "主机名", "数量（条）", "占比", "主要告警类型"])
    r += 1
    rows = [[i, n["instance"], n["hostname"] or "—", n["count"],
             "%.1f%%" % _pct(n["count"], d["total"]), n["top_type"]]
            for i, n in enumerate(d["nodes"], 1)]
    _body(ws, r, rows, ["center", "left", "left", "center", "center", "left"],
          True, [8, 24, 18, 12, 10, 46])
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 6 告警明细
    ws = wb.create_sheet("告警明细")
    r = _sheet_title(ws, "附：当日告警明细（共 %d 条）" % d["total"], 9)
    _header_row(ws, r, ["触发时间", "告警类型", "所属类别", "级别", "节点", "主机名",
                        "状态", "恢复时间", "持续时长"])
    r += 1
    detail = _build_details(d)
    _body(ws, r, detail,
          ["center", "left", "left", "center", "left", "left", "center", "center", "center"],
          True, [20, 26, 14, 8, 22, 16, 10, 20, 12])
    # 严重行标红
    for i, row in enumerate(detail):
        if row[3] == "严重":
            for c_i in range(1, 10):
                ws.cell(row=r + i, column=c_i).font = Font(name=CN, size=10, bold=True, color=C_CRIT)
    # 未恢复标黄
    for i, row in enumerate(detail):
        if row[6] == "未恢复":
            for c_i in range(1, 10):
                ws.cell(row=r + i, column=c_i).fill = PatternFill("solid", fgColor="FFF2CC")
    ws.auto_filter.ref = "A%d:I%d" % (r - 1, r - 1 + len(detail))
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    wb.save(out_path)
    return out_path
