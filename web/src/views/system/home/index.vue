<template>
  <div class="ops-home">
    <!-- 顶部欢迎区：渐变背景 + 实时时间 + 状态灯 -->
    <div class="home-hero">
      <div class="hero-left">
        <div class="hero-greet">
          <span class="hero-hello">{{ greeting }}，{{ userInfo.userInfos.name }}</span>
          <span class="hero-sub">XwOps 运维管理平台 · 统一资产管理 / 堡垒机 / 发布 / 监控</span>
        </div>
        <div class="hero-meta">
          <div class="hero-clock">
            <span class="clock-time">{{ clock.time }}</span>
            <span class="clock-date">{{ clock.date }} {{ clock.week }}</span>
          </div>
          <div class="hero-status">
            <span class="status-dot" :class="{ online: onlineSessions > 0 }"></span>
            <span class="status-text">{{ onlineSessions > 0 ? onlineSessions + ' 个会话在线' : '当前无在线会话' }}</span>
          </div>
          <div class="hero-status">
            <span class="status-dot" :class="{ online: activeAlerts === 0 }"></span>
            <span class="status-text">{{ activeAlerts > 0 ? activeAlerts + ' 个活跃告警' : '无活跃告警' }}</span>
          </div>
        </div>
      </div>
      <div class="hero-deco">
        <span class="deco-ring r1"></span>
        <span class="deco-ring r2"></span>
        <span class="deco-ring r3"></span>
        <el-icon class="deco-icon" :size="64" color="#ffffff"><Monitor /></el-icon>
      </div>
    </div>

    <!-- 统计卡片（6 张：资产 / 告警 / 会话 / 自动化 / 安全）；无权限的卡片自动隐藏 -->
    <el-row :gutter="16" class="stat-row">
      <el-col v-for="(c, k) in statItems" :key="k" :xs="12" :sm="12" :md="8">
        <div class="stat-card" :style="{ '--card-color': c.color, '--card-bg': c.bg }" @click="goTo(c.path)">
          <div class="stat-icon">
            <el-icon :size="28" :color="c.color"><component :is="c.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ c.display }}{{ c.suffix || '' }}</div>
            <div class="stat-label">{{ c.label }}</div>
          </div>
          <div class="stat-extra" v-if="c.extra">{{ c.extra }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 中部：告警趋势 + 告警级别分布（无告警模块权限时整块隐藏） -->
    <el-row :gutter="16" v-if="showAlerts">
      <el-col :xs="24" :sm="24" :md="16">
        <div class="panel">
          <div class="panel-head">
            <div class="panel-title">
              <span class="title-bar"></span>最近 7 天告警趋势
            </div>
            <div class="panel-chips">
              <span class="chip chip-danger">严重 {{ alertSummary.critical }}</span>
              <span class="chip chip-warn">警告 {{ alertSummary.warning }}</span>
              <span class="chip chip-total">本周共 {{ alertSummary.week_total }} 条</span>
            </div>
          </div>
          <div ref="chartRef" class="trend-chart"></div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="24" :md="8">
        <div class="panel panel-severity">
          <div class="panel-head">
            <div class="panel-title"><span class="title-bar"></span>告警级别分布</div>
          </div>
          <div ref="severityChartRef" class="severity-chart"></div>
          <div class="severity-legend">
            <span class="legend-item"><span class="row-dot dot-crit"></span>严重 {{ alertSummary.critical }}</span>
            <span class="legend-item"><span class="row-dot dot-warn"></span>警告 {{ alertSummary.warning }}</span>
            <span class="legend-item"><span class="row-dot dot-info"></span>提示 {{ alertSummary.info }}</span>
          </div>
          <div class="alert-foot" @click="goTo('/alertEvent')">
            <span>查看历史告警</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 底部实时列表：最近告警 + 最近会话 + 操作动态（各自独立判权） -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="24" :md="8" v-if="showAlerts">
        <div class="panel">
          <div class="panel-head">
            <div class="panel-title"><span class="title-bar"></span>最近告警</div>
            <div class="panel-more" @click="goTo('/alertEvent')">更多<el-icon><ArrowRight /></el-icon></div>
          </div>
          <el-empty v-if="!recentAlerts.length" description="暂无告警" :image-size="60" />
          <div v-else class="recent-list">
            <div v-for="(a, i) in recentAlerts" :key="i" class="recent-item">
              <el-tag :type="severityTag(a.severity)" size="small" effect="light">{{ severityText(a.severity) }}</el-tag>
              <div class="recent-main">
                <div class="recent-title">{{ a.alertname }}</div>
                <div class="recent-sub">{{ a.instance }}</div>
              </div>
              <div class="recent-time">{{ a.starts_at }}</div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="24" :md="8" v-if="showSessions">
        <div class="panel">
          <div class="panel-head">
            <div class="panel-title"><span class="title-bar"></span>最近会话</div>
            <div class="panel-more" @click="goTo('/session')">更多<el-icon><ArrowRight /></el-icon></div>
          </div>
          <el-empty v-if="!recentSessions.length" description="暂无会话" :image-size="60" />
          <div v-else class="recent-list">
            <div v-for="(s, i) in recentSessions" :key="i" class="recent-item">
              <span class="session-dot" :class="{ on: s.status === 'active' }"></span>
              <div class="recent-main">
                <div class="recent-title">{{ s.username }}@{{ s.ip }}</div>
                <div class="recent-sub">{{ s.server_name || '未知主机' }}</div>
              </div>
              <div class="recent-time">{{ s.start_time }}</div>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="24" :md="8" v-if="showAudit">
        <div class="panel">
          <div class="panel-head">
            <div class="panel-title"><span class="title-bar"></span>操作动态</div>
            <div class="panel-more" @click="goTo('/operationLog')">更多<el-icon><ArrowRight /></el-icon></div>
          </div>
          <el-empty v-if="!activities.length" description="暂无操作记录" :image-size="60" />
          <div v-else class="activity-list">
            <div v-for="(act, i) in activities" :key="i" class="activity-item">
              <span class="activity-dot" :class="act.type"></span>
              <div class="activity-main">
                <div class="activity-text">{{ act.text }}</div>
                <div class="activity-sub">{{ act.detail }}</div>
              </div>
              <div class="activity-time">{{ act.time }}</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 底部：快捷入口（只显示当前账号真能进的模块） -->
    <div class="panel">
      <div class="panel-head">
        <div class="panel-title"><span class="title-bar"></span>快捷入口</div>
      </div>
      <el-empty v-if="!navItems.length" description="暂无可用模块，请联系管理员开通权限" :image-size="70" />
      <div v-else class="quick-grid">
        <div v-for="(q, k) in navItems" :key="k" class="quick-card" @click="goTo(q.path)">
          <div class="quick-icon" :style="{ background: q.bg }">
            <el-icon :size="24" :color="q.color"><component :is="q.icon" /></el-icon>
          </div>
          <div class="quick-name">{{ q.label }}</div>
          <div class="quick-desc">{{ q.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, onUnmounted, ref, nextTick, computed, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { useUserInfo } from '/@/stores/userInfo';
import { request } from '/@/utils/service';
import {
  Monitor, Bell, Connection, Promotion, Key, Timer, DataLine,
  ArrowRight, Cpu, VideoPlay, Document, Position, Odometer, Warning,
} from '@element-plus/icons-vue';

export default defineComponent({
  name: 'opsHome',
  setup() {
    const router = useRouter();
    const userInfo = useUserInfo();
    const chartRef = ref();
    const severityChartRef = ref();
    let chart: echarts.ECharts | null = null;
    let severityChart: echarts.ECharts | null = null;
    let clockTimer: any = null;

    // 实时时钟
    const clock = ref({ time: '--:--:--', date: '', week: '' });
    const weekMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const updateClock = () => {
      const n = new Date();
      const pad = (x: number) => (x < 10 ? '0' + x : '' + x);
      clock.value = {
        time: `${pad(n.getHours())}:${pad(n.getMinutes())}:${pad(n.getSeconds())}`,
        date: `${n.getFullYear()}-${pad(n.getMonth() + 1)}-${pad(n.getDate())}`,
        week: weekMap[n.getDay()],
      };
    };

    const greeting = computed(() => {
      const h = new Date().getHours();
      if (h < 6) return '夜深了';
      if (h < 9) return '早上好';
      if (h < 12) return '上午好';
      if (h < 14) return '中午好';
      if (h < 18) return '下午好';
      return '晚上好';
    });

    // 真实数据状态
    const serverTotal = ref(0);
    const serverOnline = ref(0);
    const onlineRate = ref(0);
    const activeAlerts = ref(0);
    const onlineSessions = ref(0);
    const todaySessions = ref(0);
    const dispatchInfo = ref({ today: 0, success: 0, failed: 0 });
    const dangerToday = ref(0);
    const jenkinsCount = ref(0);
    const trend = ref<{ date: string; weekday: string; count: number }[]>([]);
    const alertSummary = ref({ critical: 0, warning: 0, info: 0, week_total: 0 });
    const recentAlerts = ref<any[]>([]);
    const recentSessions = ref<any[]>([]);
    const activities = ref<any[]>([]);

    // 数字递增动画（直接操作 reactive 数组里的 display，保证响应式）
    const animateDisplay = (card: any, target: number, duration = 800, decimals = 0) => {
      const start = performance.now();
      const step = (now: number) => {
        const p = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
        card.display = Number((target * eased).toFixed(decimals));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };

    // 统计卡片
    const statCards = reactive<any[]>([]);

    const quickNav = [
      { label: '服务器管理', desc: 'CMDB 资产台账', icon: Cpu, color: '#409eff', bg: '#ecf5ff', path: '/server' },
      { label: '命令下发', desc: '批量远程执行', icon: Position, color: '#67c23a', bg: '#f0f9eb', path: '/dispatch' },
      { label: '会话记录', desc: 'Web SSH 会话', icon: VideoPlay, color: '#e6a23c', bg: '#fdf6ec', path: '/session' },
      { label: '命令审计', desc: '高危命令留痕', icon: Document, color: '#f56c6c', bg: '#fef0f0', path: '/commandLog' },
      { label: '历史告警', desc: '告警事件查询', icon: Bell, color: '#909399', bg: '#f4f4f5', path: '/alertEvent' },
      { label: '告警规则', desc: 'Prometheus 规则', icon: DataLine, color: '#b88230', bg: '#fdf6ec', path: '/rule' },
      { label: '凭据管理', desc: '主机账号 / 密钥', icon: Key, color: '#20c0c0', bg: '#eaf8f8', path: '/credential' },
      { label: '定时任务', desc: '巡检 / 自动化', icon: Timer, color: '#7b61ff', bg: '#f1edff', path: '/celeryManage' },
    ];

    // ---------------- 模块可见性 ----------------
    // 后端 /api/dashboard/stats/ 返回 menus：
    //   null      → 不受限（超级管理员）
    //   string[]  → 该账号可见菜单的 web_path 全集
    // 用它来裁剪首页入口，保证"首页看得到的入口" = "真能点进去的页面"，
    // 不会再出现"首页有卡片、点过去 404"。
    const visiblePaths = ref<string[] | null>(null);

    const can = (path?: string): boolean => {
      if (!path) return true;
      if (visiblePaths.value === null) return true; // 超管 / 后端未下发 → 不裁剪
      return visiblePaths.value.includes(path);
    };

    // 入口 / 卡片 / 面板按权限过滤
    const navItems = computed(() => quickNav.filter((q: any) => can(q.path)));
    const statItems = computed(() => statCards.filter((c: any) => can(c.path)));
    const showAlerts = computed(() => can('/alertEvent') || can('/alertManage'));
    const showSessions = computed(() => can('/session'));
    const showAudit = computed(() => can('/operationLog') || can('/loginLog'));

    const goTo = (path: string) => {
      if (!path) return;
      if (!can(path)) {
        // 与其让用户跳过去吃一个 404，不如在首页就说清楚
        ElMessage.warning('无权限访问该模块，请联系管理员开通');
        return;
      }
      router.push(path);
    };

    // 级别 / 状态显示映射
    const severityTag = (sev: string) => ({ critical: 'danger', warning: 'warning', info: 'info' }[sev] || 'info');
    const severityText = (sev: string) => ({ critical: '严重', warning: '警告', info: '提示' }[sev] || sev);

    const fetchStats = async () => {
      try {
        const res: any = await request({ url: '/api/dashboard/stats/', method: 'get' });
        const d = res?.data || {};
        serverTotal.value = d.server?.total ?? 0;
        serverOnline.value = d.server?.online ?? 0;
        onlineRate.value = d.server?.online_rate ?? 0;
        activeAlerts.value = d.alerts?.active ?? 0;
        onlineSessions.value = d.sessions?.active ?? 0;
        todaySessions.value = d.sessions?.today ?? 0;
        dispatchInfo.value = {
          today: d.dispatch?.today ?? 0,
          success: d.dispatch?.success ?? 0,
          failed: d.dispatch?.failed ?? 0,
        };
        dangerToday.value = d.danger?.today_commands ?? 0;
        jenkinsCount.value = d.jenkins?.server_count ?? 0;
        trend.value = d.trend || [];
        alertSummary.value = {
          critical: d.alerts?.critical ?? 0,
          warning: d.alerts?.warning ?? 0,
          info: d.alerts?.info ?? 0,
          week_total: d.alerts?.week_total ?? 0,
        };
        recentAlerts.value = d.recent_alerts || [];
        recentSessions.value = d.recent_sessions || [];
        activities.value = d.activities || [];
        // menus: null=不受限；数组=可见路径；字段缺失（旧版后端）按不受限处理
        visiblePaths.value = d.menus === undefined ? null : d.menus;
        buildCards();
        nextTick(() => {
          renderChart();
          renderSeverityChart();
        });
      } catch (e) {
        console.error('获取首页统计失败', e);
      }
    };

    const buildCards = () => {
      const cards = [
        {
          label: '服务器在线率', icon: Odometer, color: '#409eff', bg: '#ecf5ff',
          path: '/server', extra: `总数 ${serverTotal.value} · 在线 ${serverOnline.value}`,
          target: onlineRate.value, display: 0, suffix: '%', decimals: 1,
        },
        {
          label: '活跃告警', icon: Bell, color: '#f56c6c', bg: '#fef0f0',
          // ★ 活跃告警 → 跳「活跃告警」菜单（/alertManage，实时透传 Alertmanager），
          //   不要跳 /alertEvent（历史告警）—— 那里是落库的历史事件
          path: '/alertManage', extra: `本周 ${alertSummary.value.week_total} 条`,
          target: activeAlerts.value, display: 0,
        },
        {
          label: '在线会话', icon: Connection, color: '#67c23a', bg: '#f0f9eb',
          path: '/session', extra: `今日 ${todaySessions.value} 次`,
          target: onlineSessions.value, display: 0,
        },
        {
          // 这张卡的落点本来就是 /alertEvent ⇒ 名称改成「历史告警」，
          // 数字也跟着换成「历史告警」的口径（近 7 天告警条数），
          // 否则会出现「标题写历史告警、数字却是本周严重数」的名实不符。
          // 完整的三级分布看下方「告警级别分布」图，这里只放最要紧的两级。
          label: '历史告警', icon: Promotion, color: '#e6a23c', bg: '#fdf6ec',
          path: '/alertEvent', extra: `严重 ${alertSummary.value.critical} · 警告 ${alertSummary.value.warning}`,
          target: alertSummary.value.week_total, display: 0,
        },
        {
          label: '下发任务(今日)', icon: Position, color: '#7b61ff', bg: '#f1edff',
          path: '/dispatch', extra: `成功 ${dispatchInfo.value.success} · 失败 ${dispatchInfo.value.failed}`,
          target: dispatchInfo.value.today, display: 0,
        },
        {
          label: '高危命令(今日)', icon: Warning, color: '#f56c6c', bg: '#fef0f0',
          path: '/commandLog', extra: `Jenkins ${jenkinsCount.value} 台`,
          target: dangerToday.value, display: 0,
        },
      ];
      statCards.splice(0, statCards.length, ...cards);
      statCards.forEach((card) => animateDisplay(card, card.target, 800, card.decimals || 0));
    };

    const renderChart = () => {
      if (!chartRef.value) return;
      if (!chart) chart = echarts.init(chartRef.value);
      const labels = trend.value.map((t) => t.date);
      const counts = trend.value.map((t) => t.count);
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(255,255,255,0.96)',
          borderColor: '#e4e7ed',
          textStyle: { color: '#303133' },
        },
        grid: { left: 36, right: 20, top: 30, bottom: 30 },
        xAxis: {
          type: 'category',
          data: labels,
          boundaryGap: false,
          axisLabel: { color: '#909399' },
          axisLine: { lineStyle: { color: '#dcdfe6' } },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: '#909399' },
          splitLine: { lineStyle: { color: '#f0f2f5' } },
        },
        series: [
          {
            name: '告警数',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 7,
            data: counts,
            itemStyle: { color: '#f56c6c', borderColor: '#fff', borderWidth: 2 },
            lineStyle: { width: 3, color: '#f56c6c' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(245, 108, 108, 0.28)' },
                { offset: 1, color: 'rgba(245, 108, 108, 0.02)' },
              ]),
            },
            emphasis: { scale: true },
          },
        ],
      });
    };

    const renderSeverityChart = () => {
      if (!severityChartRef.value) return;
      if (!severityChart) severityChart = echarts.init(severityChartRef.value);
      const total = alertSummary.value.week_total;
      const data = [
        { value: alertSummary.value.critical, name: '严重', itemStyle: { color: '#f56c6c' } },
        { value: alertSummary.value.warning, name: '警告', itemStyle: { color: '#e6a23c' } },
        { value: alertSummary.value.info, name: '提示', itemStyle: { color: '#409eff' } },
      ];
      severityChart.setOption({
        tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.96)', borderColor: '#e4e7ed', textStyle: { color: '#303133' } },
        series: [
          {
            type: 'pie',
            radius: ['55%', '76%'],
            center: ['50%', '46%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
            label: { show: false },
            labelLine: { show: false },
            data: total > 0 ? data : [{ value: 1, name: '暂无', itemStyle: { color: '#f0f2f5' } }],
          },
        ],
        graphic: [
          {
            type: 'text',
            left: 'center',
            top: '38%',
            style: {
              text: String(total),
              fill: '#303133',
              fontSize: 30,
              fontWeight: 700,
              textAlign: 'center',
            },
          },
          {
            type: 'text',
            left: 'center',
            top: '52%',
            style: {
              text: '本周告警',
              fill: '#909399',
              fontSize: 12,
              textAlign: 'center',
            },
          },
        ],
      });
    };

    const handleResize = () => {
      chart?.resize();
      severityChart?.resize();
    };

    onMounted(() => {
      updateClock();
      clockTimer = setInterval(updateClock, 1000);
      fetchStats();
      window.addEventListener('resize', handleResize);
    });
    onUnmounted(() => {
      if (clockTimer) clearInterval(clockTimer);
      window.removeEventListener('resize', handleResize);
      chart?.dispose();
      severityChart?.dispose();
    });

    return {
      userInfo, greeting, clock, onlineSessions, activeAlerts, alertSummary,
      statCards, statItems, quickNav, navItems, chartRef, severityChartRef, goTo,
      showAlerts, showSessions, showAudit,
      recentAlerts, recentSessions, activities, severityTag, severityText,
    };
  },
});
</script>

<style scoped>
.ops-home {
  padding: 16px;
}
/* ===== 顶部欢迎区 ===== */
.home-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 22px 28px;
  margin-bottom: 16px;
  border-radius: 14px;
  background: linear-gradient(120deg, #1f6feb 0%, #3b8cff 45%, #6aa6ff 100%);
  color: #fff;
  box-shadow: 0 6px 20px rgba(31, 111, 235, 0.28);
}
.hero-left {
  position: relative;
  z-index: 2;
}
.hero-greet {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.hero-hello {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.hero-sub {
  font-size: 13px;
  opacity: 0.85;
}
.hero-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.hero-clock {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.clock-time {
  font-size: 30px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.clock-date {
  font-size: 13px;
  opacity: 0.85;
}
.hero-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 13px;
}
.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #c0c4cc;
  transition: background 0.3s;
}
.status-dot.online {
  background: #4ef09a;
  animation: pulse 1.8s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(78, 240, 154, 0.7); }
  70% { box-shadow: 0 0 0 8px rgba(78, 240, 154, 0); }
  100% { box-shadow: 0 0 0 0 rgba(78, 240, 154, 0); }
}
.hero-deco {
  position: relative;
  z-index: 1;
  width: 140px;
  height: 100px;
}
.deco-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.25);
}
.deco-ring.r1 { width: 140px; height: 140px; top: -20px; right: -10px; }
.deco-ring.r2 { width: 100px; height: 100px; top: 0; right: 10px; }
.deco-ring.r3 { width: 60px; height: 60px; top: 20px; right: 30px; }
.deco-icon {
  position: absolute;
  top: 18px;
  right: 38px;
  opacity: 0.9;
}
/* ===== 统计卡片 ===== */
.stat-row { margin-bottom: 4px; }
.stat-card {
  display: flex;
  align-items: center;
  position: relative;
  padding: 22px 20px;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.25s, box-shadow 0.25s;
}
.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--card-color);
}
.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.1);
}
.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 14px;
  background: var(--card-bg);
  flex-shrink: 0;
}
.stat-info { flex: 1; min-width: 0; }
.stat-value {
  font-size: 30px;
  font-weight: 700;
  color: #303133;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 13px; color: #909399; margin-top: 5px; }
.stat-extra {
  position: absolute;
  bottom: 10px;
  right: 14px;
  font-size: 11px;
  color: #c0c4cc;
}
/* ===== 面板 ===== */
.panel {
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.panel-title {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.title-bar {
  display: inline-block;
  width: 4px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(180deg, #409eff, #6aa6ff);
  margin-right: 8px;
}
.panel-chips { display: flex; gap: 8px; }
.chip {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  white-space: nowrap;
}
.chip-danger { color: #f56c6c; background: #fef0f0; }
.chip-warn { color: #e6a23c; background: #fdf6ec; }
.chip-total { color: #909399; background: #f4f4f5; }
.trend-chart { height: 320px; }
/* 告警级别分布 */
.panel-severity { display: flex; flex-direction: column; }
.severity-chart { height: 200px; }
.severity-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding: 6px 0 14px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}
.row-dot { width: 9px; height: 9px; border-radius: 50%; }
.dot-crit { background: #f56c6c; }
.dot-warn { background: #e6a23c; }
.dot-info { background: #409eff; }
.alert-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  border-top: 1px solid #f0f2f5;
  font-size: 13px;
  color: #409eff;
  cursor: pointer;
  border-radius: 0 0 12px 12px;
  transition: background 0.2s;
}
.alert-foot:hover { background: #f5f8ff; }
/* 快捷入口 */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 14px;
}
.quick-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 22px 10px 18px;
  border-radius: 12px;
  cursor: pointer;
  border: 1px solid #f0f2f5;
  transition: transform 0.22s, box-shadow 0.22s, border-color 0.22s;
}
.quick-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
  border-color: #d9ecff;
}
.quick-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.quick-name { font-size: 14px; color: #303133; font-weight: 500; }
.quick-desc { font-size: 11px; color: #c0c4cc; margin-top: 4px; }
/* 底部实时列表 */
.panel-more {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}
.panel-more:hover { color: #409eff; }
.recent-list { display: flex; flex-direction: column; }
.recent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid #f0f2f5;
  transition: background 0.2s;
}
.recent-item:last-child { border-bottom: none; }
.recent-item:hover { background: #fafbfc; }
.recent-main { flex: 1; min-width: 0; }
.recent-title {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-time {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.session-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #c0c4cc;
  flex-shrink: 0;
}
.session-dot.on {
  background: #67c23a;
  animation: pulse 1.8s infinite;
}
/* 操作动态流 */
.activity-list { display: flex; flex-direction: column; }
.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid #f0f2f5;
  transition: background 0.2s;
}
.activity-item:last-child { border-bottom: none; }
.activity-item:hover { background: #fafbfc; }
.activity-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.activity-dot.login { background: #67c23a; }
.activity-dot.op { background: #409eff; }
.activity-main { flex: 1; min-width: 0; }
.activity-text {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.activity-sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.activity-time {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
</style>
