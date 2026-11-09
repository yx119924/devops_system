# -*- coding: utf-8 -*-
"""巡检周报 · Excel 明细附表

7 个 sheet：概况 / 级别 / 类别 / 类型 / 每日明细 / 时段 / 节点
与日报附表的差别：把「告警明细」（逐条事件）换成「每日明细」（逐日汇总），
因为周报的明细量太大，逐条列意义不大，逐日才能看出节奏。
"""

from .xlsx_exporter import (
    C_BAND, C_BORDER, C_CRIT, C_HEAD, C_TITLE, CN,
    Alignment, Border, Font, PatternFill, Workbook,
    XLSX_AVAILABLE, XLSX_IMPORT_ERROR,
    _body, _databar, _header_row, _pct, _sheet_title,
)


def render(data, out_path):
    if not XLSX_AVAILABLE:
        raise RuntimeError(
            "服务端缺少 openpyxl 依赖（%s）。请重建 django 镜像后再导出 Excel。"
            % XLSX_IMPORT_ERROR)

    d = data
    sev = d.get("severity_counts") or {}
    total = d.get("total", 0)
    days = d.get("days", 0)
    wb = Workbook()

    # ---------------- Sheet 1 巡检概况
    ws = wb.active
    ws.title = "巡检概况"
    r = _sheet_title(ws, "运维巡检报告", 4,
                     "%s　%s 至 %s（共 %d 天）" % (d.get("week_label", ""),
                                                d.get("start", ""), d.get("end", ""), days))
    _header_row(ws, r, ["项目", "内容", "", ""])
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
    r += 1

    kv = [
        ("巡检周期", "%s 00:00:00 — %s 23:59:59" % (d.get("start", ""), d.get("end", ""))),
        ("周期标识", d.get("week_label", "—")),
        ("统计天数", "%d 天" % days),
        ("数据来源", d.get("source_desc", "—")),
        ("统计口径", d.get("caliber", "—")),
        ("告警总量", "%d 条" % total),
        ("日均告警", "%.1f 条/天" % (d.get("avg_per_day") or 0)),
        ("级别分布", "严重 %d / 警告 %d / 提示 %d"
         % (sev.get("critical", 0), sev.get("warning", 0), sev.get("info", 0))),
        ("环比上周", _delta_text(d)),
        ("告警类型数", "%d 种" % len(d.get("types") or [])),
        ("涉及告警来源", "%d 个" % len(d.get("nodes") or [])),
        ("峰值日", _peak_text(d)),
    ]
    for k, v in kv:
        c = ws.cell(row=r, column=1, value=k)
        c.font = Font(name=CN, size=10, bold=True, color=C_TITLE)
        c.fill = PatternFill("solid", fgColor=C_BAND)
        c.alignment = Alignment(vertical="center", indent=1)
        c.border = Border(left=_thin(), right=_thin(), top=_thin(), bottom=_thin())
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        c = ws.cell(row=r, column=2, value=v)
        c.font = Font(name=CN, size=10, color="262626")
        c.alignment = Alignment(vertical="center", indent=1, wrap_text=True)
        c.border = Border(left=_thin(), right=_thin(), top=_thin(), bottom=_thin())
        ws.row_dimensions[r].height = 22
        r += 1
    for i, w in enumerate([16, 30, 22, 30], 1):
        ws.column_dimensions[_col(i)].width = w
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 2 级别分布
    ws = wb.create_sheet("级别分布")
    r = _sheet_title(ws, "3.1  告警总量与级别分布", 3)
    _header_row(ws, r, ["告警级别", "数量（条）", "占比"])
    r += 1
    rows = [["%s（%s）" % (cn, k), sev.get(k, 0), "%.1f%%" % _pct(sev.get(k, 0), total)]
            for k, cn in (("critical", "严重"), ("warning", "警告"), ("info", "提示"))]
    rows.append(["合计", total, "100.0%" if total else "0.0%"])
    _body(ws, r, rows, ["left", "center", "center"], True, [26, 16, 14])
    for c_i in range(1, 4):
        c = ws.cell(row=r + len(rows) - 1, column=c_i)
        c.font = Font(name=CN, size=10, bold=True, color=C_TITLE)
        c.fill = PatternFill("solid", fgColor=C_BAND)
    ws.cell(row=r, column=2).font = Font(name=CN, size=10, bold=True, color=C_CRIT)
    _databar(ws, r, r + len(rows) - 2, "B")
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 3 类别分布
    if d.get("categories"):
        ws = wb.create_sheet("类别分布")
        r = _sheet_title(ws, "3.2  告警类别分布", 5)
        _header_row(ws, r, ["序号", "告警类别", "数量（条）", "占比", "主要来源"])
        r += 1
        rows = [[i, c["name"], c["count"], "%.1f%%" % c["ratio"], _top_type_of(d, c["name"])]
                for i, c in enumerate(d["categories"], 1)]
        _body(ws, r, rows, ["center", "left", "center", "center", "left"],
              True, [8, 18, 12, 10, 44])
        _databar(ws, r, r + len(rows) - 1, "C")
        ws.freeze_panes = "A%d" % r
        ws.sheet_view.showGridLines = False

    # ---------------- Sheet 4 类型分布
    if d.get("types"):
        ws = wb.create_sheet("类型分布")
        r = _sheet_title(ws, "3.3  告警类型分布（共 %d 种）" % len(d["types"]), 5)
        _header_row(ws, r, ["序号", "告警类型", "所属类别", "数量（条）", "占比"])
        r += 1
        rows = [[i, t["alertname"], t.get("category", "其他"), t["count"],
                 "%.1f%%" % t.get("ratio", 0)]
                for i, t in enumerate(d["types"], 1)]
        _body(ws, r, rows, ["center", "left", "left", "center", "center"],
              True, [8, 34, 18, 12, 10])
        _databar(ws, r, r + len(rows) - 1, "D")
        ws.freeze_panes = "A%d" % r
        ws.sheet_view.showGridLines = False

    # ---------------- Sheet 5 每日明细（周报的核心表）
    if d.get("daily"):
        ws = wb.create_sheet("每日明细")
        r = _sheet_title(ws, "3.4  每日告警明细（共 %d 天）" % len(d["daily"]), 7,
                         "带「★」的是周期内告警最集中的一天")
        _header_row(ws, r, ["日期", "星期", "总量", "严重", "警告", "提示", "主要类别"])
        r += 1
        avg = d.get("avg_per_day") or 0
        peak_date = (d.get("peak_day") or {}).get("date", "")
        rows = []
        for x in d["daily"]:
            cats = x.get("categories") or []
            main = "、".join("%s（%d）" % (c["name"], c["count"]) for c in cats[:2]) if cats else "—"
            star = "　★" if x["date"] == peak_date and x["total"] else ""
            rows.append([x["date"], x.get("weekday", ""), x["total"],
                         x.get("critical", 0), x.get("warning", 0), x.get("info", 0),
                         main + star])
        _body(ws, r, rows, ["center", "center", "center", "center", "center", "center", "left"],
              True, [14, 10, 10, 10, 10, 10, 48])
        _databar(ws, r, r + len(rows) - 1, "C")
        # 峰值日整行加淡黄底
        for i, x in enumerate(d["daily"]):
            if x["date"] == peak_date and x["total"]:
                for c_i in range(1, 8):
                    ws.cell(row=r + i, column=c_i).fill = PatternFill("solid", fgColor="FFF2CC")
        ws.freeze_panes = "A%d" % r
        ws.sheet_view.showGridLines = False

    # ---------------- Sheet 6 时段分布
    ws = wb.create_sheet("时段分布")
    r = _sheet_title(ws, "3.5  告警时段分布（0—23 时）", 3)
    _header_row(ws, r, ["时段", "数量（条）", "占周期"])
    r += 1
    rows = [["%02d:00—%02d:00" % (h["hour"], h["hour"] + 1), h["count"],
             "%.1f%%" % _pct(h["count"], total)]
            for h in (d.get("hourly") or [])]
    _body(ws, r, rows, ["center", "center", "center"], True, [16, 14, 12])
    _databar(ws, r, r + len(rows) - 1, "B")
    ws.freeze_panes = "A%d" % r
    ws.sheet_view.showGridLines = False

    # ---------------- Sheet 7 节点分布
    if d.get("nodes"):
        ws = wb.create_sheet("节点分布")
        r = _sheet_title(ws, "3.6  告警节点分布（共 %d 个）" % len(d["nodes"]), 5)
        _header_row(ws, r, ["序号", "节点 / 实例", "主机名", "数量（条）", "占比"])
        r += 1
        rows = [[i, n["instance"], n.get("hostname") or "—", n["count"],
                 "%.1f%%" % n.get("ratio", 0)]
                for i, n in enumerate(d["nodes"], 1)]
        _body(ws, r, rows, ["center", "left", "left", "center", "center"],
              True, [8, 26, 20, 12, 10])
        _databar(ws, r, r + len(rows) - 1, "D")
        ws.freeze_panes = "A%d" % r
        ws.sheet_view.showGridLines = False

    wb.save(out_path)
    return out_path


# ---------------------------------------------------------------- 小工具
def _thin():
    from openpyxl.styles import Side
    return Side(style="thin", color=C_BORDER)


def _col(i):
    from openpyxl.utils import get_column_letter
    return get_column_letter(i)


def _peak_text(d):
    p = d.get("peak_day") or {}
    if not p.get("date"):
        return "本周无告警"
    return "%s（%s）%d 条" % (p["date"], p.get("weekday", ""), p["total"])


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
    best, best_n = "", -1
    for t in d.get("types") or []:
        if t.get("category") == cat_name and t["count"] > best_n:
            best, best_n = t["alertname"], t["count"]
    return best or "—"
