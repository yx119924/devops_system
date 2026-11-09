# -*- coding: utf-8 -*-
"""告警分类 —— 把几十条规则名收敛成 7 个类别

为什么需要这一层
----------------
线上真实数据长这样（2026-11-07 实测 276 条）：

    ping测延迟超过200ms      36     网关不可达              30
    交叉楼服务器状态异常      24     ping测丢包率较高         20
    目标网关不可达           18     服务器状态异常           18
    GPU额定功率过高          18     健康检查接口状态码非200   18
    PostgreSQL主库存在阻塞查询  5   Kafka Broker 离线        3
    海豚调度任务失败告警       2     磁盘使用率过高            2

如果报告只按规则名排 TOP10，领导的视线会停在
「ping测延迟超过200ms 36 次」这种流水账上，看不出结论。

收敛成类别后，同一批数据能直接说出：
「网络连通类 130 条，占全日 47.1%，是当日最主要的问题来源。」

匹配顺序即优先级，先命中先归类 —— 所以「交叉楼服务器状态异常」必须排在
「主机资源」之前，否则会被「服务器状态」抢走，而它本质是跨楼网络的探测告警。
"""

# (类别名, 关键词元组)。顺序 = 优先级，不要随意调换。
CATEGORY_RULES = (
    ("网络连通", (
        "ping", "Ping", "网关", "不可达", "丢包", "延迟", "交叉楼",
        "网络", "丢包率", "ExporterProbeBacklog",
    )),
    ("GPU", ("GPU", "gpu", "显存")),
    ("数据库中间件", (
        "PostgreSQL", "postgres", "PQ", "Redis", "Kafka", "MySQL", "MongoDB",
        "数据库", "主备", "备库", "主库", "阻塞查询", "复制延迟",
    )),
    ("业务探测", (
        "健康检查", "Web页面", "HTTP", "站点", "接口", "actuator",
    )),
    ("任务调度", ("海豚", "调度", "DolphinScheduler", "工作流")),
    ("主机资源", (
        "磁盘", "内存", "服务器状态", "CPU", "负载", "文件句柄", "swap",
    )),
)

DEFAULT_CATEGORY = "其他"

# 报告里的固定展示顺序（没有数据的类别不出现）
CATEGORY_ORDER = ("网络连通", "主机资源", "数据库中间件", "GPU", "业务探测", "任务调度", "其他")


def classify(alertname):
    """告警名 -> 类别。匹配不到归「其他」，绝不丢数据。"""
    name = (alertname or "").strip()
    if not name:
        return DEFAULT_CATEGORY
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in name:
                return cat
    return DEFAULT_CATEGORY


def group_counts(pairs):
    """[(alertname, count), ...] -> {类别: 总数}，用于快速核对。"""
    out = {}
    for name, cnt in pairs:
        cat = classify(name)
        out[cat] = out.get(cat, 0) + cnt
    return out
