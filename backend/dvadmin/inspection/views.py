# -*- coding: utf-8 -*-
"""巡检日报 · 接口

三个入口共用同一份聚合结果（services.collect_daily），
保证「页面上看到的数字」与「导出文件里的数字」永远一致。
"""

import logging
from datetime import date, datetime, timedelta
from io import BytesIO
from urllib.parse import quote

from django.http import HttpResponse
from rest_framework.decorators import api_view

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from .exporters import docx_exporter, docx_weekly, xlsx_exporter, xlsx_weekly
from .services import collect_range, collect_daily

logger = logging.getLogger(__name__)

MIN_DATE = date(2020, 1, 1)


def _parse_day(raw, field="date"):
    """解析 YYYY-MM-DD；缺省取今天。返回 (date_obj, error_msg)。"""
    if not raw:
        return date.today(), None
    try:
        d = datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None, "%s 格式不正确，应为 YYYY-MM-DD" % field
    if d > date.today():
        return None, "不能查询未来日期（%s）" % d.isoformat()
    if d < MIN_DATE:
        return None, "日期过早（%s），请检查" % d.isoformat()
    return d, None


def _attachment(content, filename, content_type):
    """统一构造下载响应。

    ★ Content-Disposition 用 `filename=<urlencode>` 这一种简单形式，
      不用 RFC 5987 的 `filename*=UTF-8''...` ——
      前端 utils/service.ts 的 downloadFile() 是按 split("=")[1] 取的，
      带 filename* 时会把 "UTF-8''" 一起截进去，文件名变成乱码。
    """
    resp = HttpResponse(content, content_type=content_type)
    resp["Content-Disposition"] = "attachment; filename=%s" % quote(filename)
    resp["Access-Control-Expose-Headers"] = "Content-Disposition"
    return resp


@api_view(["GET"])
def daily_report(request):
    """GET /inspection/daily/?date=2026-11-06 —— 日报数据（页面用）"""
    day, err = _parse_day(request.GET.get("date"))
    if err:
        return ErrorResponse(msg=err)
    try:
        data = collect_daily(day)
    except Exception as exc:                                    # noqa: BLE001
        logger.exception("生成巡检日报失败")
        return ErrorResponse(msg="生成巡检日报失败：%s" % exc)
    return DetailResponse(data=data)


def _weekly_range(request):
    """解析周期参数 → (start, end, err)。

    自然周口径（周一 00:00 — 周日 23:59）：
      · 不传 week  → 默认「上一个完整周」（今天所在周的周一往前推 7 天）
      · 传任意日期 → 自动对齐到该日期所在周的周一
    页面查询和两个导出接口共用这一份，避免三处各写一遍导致边界不一致。
    """
    raw = request.GET.get("week") or request.GET.get("start")
    if raw:
        anchor, err = _parse_day(raw, "week")
        if err:
            return None, None, err
    else:
        today = date.today()
        anchor = today - timedelta(days=today.weekday() + 7)

    start = anchor - timedelta(days=anchor.weekday())      # 对齐到周一
    end = start + timedelta(days=6)                        # 周日

    today = date.today()
    if start > today:
        return None, None, "不能查询未来的周（%s 起）" % start.isoformat()
    if end > today:
        end = today                                        # 本周还没过完，截到今天
    return start, end, None


@api_view(["GET"])
def weekly_report(request):
    """GET /inspection/weekly/?week=2026-11-03 —— 周报数据（页面用）"""
    start, end, err = _weekly_range(request)
    if err:
        return ErrorResponse(msg=err)
    try:
        data = collect_range(start, end)
    except Exception as exc:                                    # noqa: BLE001
        logger.exception("生成巡检周报失败")
        return ErrorResponse(msg="生成巡检周报失败：%s" % exc)
    return DetailResponse(data=data)


@api_view(["GET"])
def export_weekly_word(request):
    """GET /inspection/export/weekly/word/?week=2026-11-03 —— 下载周报 Word"""
    start, end, err = _weekly_range(request)
    if err:
        return ErrorResponse(msg=err)
    try:
        data = collect_range(start, end)
        buf = BytesIO()
        docx_weekly.render(data, buf)
        buf.seek(0)
        name = "巡检周报_%s至%s.docx" % (data["start"], data["end"][5:])
        return _attachment(
            buf.getvalue(), name,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except RuntimeError as exc:
        logger.warning("导出周报 Word 不可用：%s", exc)
        return ErrorResponse(msg=str(exc))
    except Exception as exc:                                    # noqa: BLE001
        logger.exception("导出周报 Word 失败")
        return ErrorResponse(msg="导出周报 Word 失败：%s" % exc)


@api_view(["GET"])
def export_weekly_excel(request):
    """GET /inspection/export/weekly/excel/?week=2026-11-03 —— 下载周报 Excel"""
    start, end, err = _weekly_range(request)
    if err:
        return ErrorResponse(msg=err)
    try:
        data = collect_range(start, end)
        buf = BytesIO()
        xlsx_weekly.render(data, buf)
        buf.seek(0)
        name = "巡检周报附表_%s至%s.xlsx" % (data["start"], data["end"][5:])
        return _attachment(
            buf.getvalue(), name,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except RuntimeError as exc:
        logger.warning("导出周报 Excel 不可用：%s", exc)
        return ErrorResponse(msg=str(exc))
    except Exception as exc:                                    # noqa: BLE001
        logger.exception("导出周报 Excel 失败")
        return ErrorResponse(msg="导出周报 Excel 失败：%s" % exc)


@api_view(["GET"])
def export_word(request):
    """GET /inspection/export/word/?date=2026-11-06 —— 下载 Word 主报告"""
    day, err = _parse_day(request.GET.get("date"))
    if err:
        return ErrorResponse(msg=err)
    try:
        data = collect_daily(day)
        buf = BytesIO()
        docx_exporter.render(data, buf)
        buf.seek(0)
        name = "巡检日报_%s.docx" % data["date"]
        return _attachment(
            buf.getvalue(), name,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except RuntimeError as exc:
        # 依赖缺失（python-docx 未安装）：给出可执行的修复指引，别吞成笼统的「导出失败」
        logger.warning("导出 Word 不可用：%s", exc)
        return ErrorResponse(msg=str(exc))
    except Exception as exc:                                    # noqa: BLE001
        logger.exception("导出 Word 失败")
        return ErrorResponse(msg="导出 Word 失败：%s" % exc)


@api_view(["GET"])
def export_excel(request):
    """GET /inspection/export/excel/?date=2026-11-06 —— 下载 Excel 明细附表"""
    day, err = _parse_day(request.GET.get("date"))
    if err:
        return ErrorResponse(msg=err)
    try:
        data = collect_daily(day)
        buf = BytesIO()
        xlsx_exporter.render(data, buf)
        buf.seek(0)
        name = "巡检日报附表_%s.xlsx" % data["date"]
        return _attachment(
            buf.getvalue(), name,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as exc:                                    # noqa: BLE001
        logger.exception("导出 Excel 失败")
        return ErrorResponse(msg="导出 Excel 失败：%s" % exc)
