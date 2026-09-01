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
        </div>
      </div>
      <div class="hero-deco">
        <span class="deco-ring r1"></span>
        <span class="deco-ring r2"></span>
        <span class="deco-ring r3"></span>
        <el-icon class="deco-icon" :size="64" color="#ffffff"><Monitor /></el-icon>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col v-for="(c, k) in statCards" :key="k" :xs="12" :sm="12" :md="6">
        <div class="stat-card" :style="{ '--card-color': c.color, '--card-bg': c.bg }" @click="goTo(c.path)">
          <div class="stat-icon">
            <el-icon :size="28" :color="c.color"><component :is="c.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ c.display }}</div>
            <div class="stat-label">{{ c.label }}</div>
          </div>
          <div class="stat-extra" v-if="c.extra">{{ c.extra }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 中部：告警趋势 + 告警概览 -->
    <el-row :gutter="16">
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
        <div class="panel panel-alert">
          <div class="panel-head">
            <div class="panel-title"><span class="title-bar"></span>告警概览</div>
          </div>
          <div class="alert-overview">
            <div class="alert-big">
              <div class="alert-num" :style="{ color: activeAlerts > 0 ? '#f56c6c' : '#67c23a' }">{{ activeAlerts }}</div>
              <div class="alert-txt">当前活跃告警</div>
            </div>
            <div class="alert-split"></div>
            <div class="alert-rows">
              <div class="alert-row">
                <span class="row-dot dot-crit"></span>
                <span class="row-label">严重</span>
                <span class="row-val">{{ alertSummary.critical }}</span>
              </div>
              <div class="alert-row">
                <span class="row-dot dot-warn"></span>
                <span class="row-label">警告</span>
                <span class="row-val">{{ alertSummary.warning }}</span>
              </div>
              <div class="alert-row">
                <span class="row-dot dot-info"></span>
                <span class="row-label">本周告警总量</span>
                <span class="row-val">{{ alertSummary.week_total }}</span>
              </div>
            </div>
          </div>
          <div class="alert-foot" @click="goTo('/alertEvent')">
            <span>查看历史告警</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 底部实时列表：最近告警 + 最近会话 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="24" :md="12">
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
      <el-col :xs="24" :sm="24" :md="12">
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
    </el-row>

    <!-- 底部：快捷入口 -->
    <div class="panel">
      <div class="panel-head">
        <div class="panel-title"><span class="title-bar"></span>快捷入口</div>
      </div>
      <div class="quick-grid">
        <div v-for="(q, k) in quickNav" :key="k" class="quick-card" @click="goTo(q.path)">
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
import * as echarts from 'echarts';
import { useUserInfo } from '/@/stores/userInfo';
import { request } from '/@/utils/service';
import {
  Monitor, Bell, Connection, Promotion, Key, Timer, DataLine,
  ArrowRight, Cpu, VideoPlay, Document, Position,
} from '@element-plus/icons-vue';

export default defineComponent({
  name: 'opsHome',
  setup() {
    const router = useRouter();
    const userInfo = useUserInfo();
    const chartRef = ref();
    let chart: echarts.ECharts | null = null;
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
    const activeAlerts = ref(0);
    const onlineSessions = ref(0);
    const trend = ref<{ date: string; weekday: string; count: number }[]>([]);
    const alertSummary = ref({ critical: 0, warning: 0, week_total: 0 });
    const recentAlerts = ref<any[]>([]);
    const recentSessions = ref<any[]>([]);

    // 数字递增动画（直接操作 reactive 数组里的 display，保证响应式）
    const animateDisplay = (card: any, target: number, duration = 800) => {
      const start = performance.now();
      const step = (now: number) => {
        const p = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
        card.display = Math.round(target * eased);
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

    const goTo = (path: string) => {
      if (path) router.push(path);
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
        activeAlerts.value = d.alerts?.active ?? 0;
        onlineSessions.value = d.sessions?.active ?? 0;
        trend.value = d.trend || [];
        alertSummary.value = {
          critical: d.alerts?.critical ?? 0,
          warning: d.alerts?.warning ?? 0,
          week_total: d.alerts?.week_total ?? 0,
        };
        recentAlerts.value = d.recent_alerts || [];
        recentSessions.value = d.recent_sessions || [];
        buildCards();
        nextTick(() => renderChart());
      } catch (e) {
        console.error('获取首页统计失败', e);
      }
    };

    const buildCards = () => {
      const offline = serverTotal.value - serverOnline.value;
      const cards = [
        {
          label: '服务器总数', icon: Cpu, color: '#409eff', bg: '#ecf5ff',
          path: '/server', extra: `在线 ${serverOnline.value} · 离线 ${offline}`,
          target: serverTotal.value, display: 0,
        },
        {
          label: '活跃告警', icon: Bell, color: '#f56c6c', bg: '#fef0f0',
          path: '/alertEvent', extra: `本周 ${alertSummary.value.week_total} 条`,
          target: activeAlerts.value, display: 0,
        },
        {
          label: '在线会话', icon: Connection, color: '#67c23a', bg: '#f0f9eb',
          path: '/session', extra: '实时连接数',
          target: onlineSessions.value, display: 0,
        },
        {
          label: '严重告警(周)', icon: Promotion, color: '#e6a23c', bg: '#fdf6ec',
          path: '/alertEvent', extra: `警告 ${alertSummary.value.warning} 条`,
          target: alertSummary.value.critical, display: 0,
        },
      ];
      statCards.splice(0, statCards.length, ...cards);
      statCards.forEach((card) => animateDisplay(card, card.target));
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

    const handleResize = () => chart?.resize();

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
    });

    return {
      userInfo, greeting, clock, onlineSessions, activeAlerts, alertSummary,
      statCards, quickNav, chartRef, goTo,
      recentAlerts, recentSessions, severityTag, severityText,
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
  gap: 24px;
  margin-top: 16px;
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
}
.stat-info { flex: 1; }
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
/* 告警概览 */
.panel-alert { display: flex; flex-direction: column; }
.alert-overview {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 0;
  flex: 1;
}
.alert-big { text-align: center; min-width: 110px; }
.alert-num { font-size: 46px; font-weight: 700; line-height: 1; }
.alert-txt { font-size: 13px; color: #909399; margin-top: 8px; }
.alert-split { width: 1px; height: 90px; background: #ebeef5; }
.alert-rows { flex: 1; display: flex; flex-direction: column; gap: 16px; }
.alert-row { display: flex; align-items: center; gap: 10px; }
.row-dot { width: 9px; height: 9px; border-radius: 50%; }
.dot-crit { background: #f56c6c; }
.dot-warn { background: #e6a23c; }
.dot-info { background: #409eff; }
.row-label { flex: 1; font-size: 13px; color: #606266; }
.row-val { font-size: 16px; font-weight: 600; color: #303133; }
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
</style>
