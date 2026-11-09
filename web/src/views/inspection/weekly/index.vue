<template>
	<div class="inspection-weekly">
		<!-- ============ 工具栏 ============ -->
		<div class="toolbar">
			<div class="toolbar-left">
				<span class="field-label">选择周期</span>
				<el-date-picker
					v-model="pickDate"
					type="date"
					value-format="YYYY-MM-DD"
					placeholder="选任意一天，自动归到所在周"
					:clearable="false"
					:disabled-date="disableFuture"
					style="width: 230px"
					@change="load"
				/>
				<el-button-group class="quick-group">
					<el-button @click="pick('lastweek')">上周</el-button>
					<el-button @click="pick('thisweek')">本周</el-button>
				</el-button-group>
				<el-button type="primary" :loading="loading" @click="load">生成周报</el-button>
			</div>
			<div class="toolbar-right">
				<span class="tip">自然周：周一 00:00 — 周日 23:59</span>
				<el-button :loading="exporting.word" :disabled="report.total === undefined" @click="doExport('word')">
					导出 Word 周报
				</el-button>
				<el-button :loading="exporting.excel" :disabled="report.total === undefined" @click="doExport('excel')">
					导出 Excel 附表
				</el-button>
			</div>
		</div>

		<div v-loading="loading" element-loading-text="正在汇总 7 天数据…">
			<!-- ============ 报告头 ============ -->
			<div class="report-head">
				<div class="head-main">
					<div class="head-title">运维巡检报告<span class="head-badge">周报</span></div>
					<div class="head-sub">
						{{ report.week_label || '—' }}
						<span class="dot">·</span>
						{{ report.start || '—' }} 至 {{ report.end || '—' }}
						<span class="dot">·</span>
						共 {{ report.days || 0 }} 天
						<span class="dot">·</span>
						生成于 {{ generatedAt }}
					</div>
				</div>
			</div>

			<!-- ============ 概览卡 ============ -->
			<div class="stat-row">
				<div class="stat-card">
					<div class="stat-label">全周告警总量</div>
					<div class="stat-num">{{ report.total ?? 0 }}<span class="unit">条</span></div>
					<div class="stat-foot" :class="deltaClass">{{ deltaText }}</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">日均告警</div>
					<div class="stat-num">{{ report.avg_per_day ?? 0 }}<span class="unit">条/天</span></div>
					<div class="stat-foot">{{ peakText }}</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">严重 / 警告 / 提示</div>
					<div class="stat-num sev-line">
						<span class="crit">{{ sevCount.critical }}</span>
						<span class="slash">/</span>
						<span class="warn">{{ sevCount.warning }}</span>
						<span class="slash">/</span>
						<span class="info">{{ sevCount.info }}</span>
					</div>
					<div class="stat-foot">严重占比 {{ pct(sevCount.critical) }}%</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">涉及告警来源</div>
					<div class="stat-num">{{ (report.nodes || []).length }}<span class="unit">个</span></div>
					<div class="stat-foot">{{ topNodeText }}</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">告警类别</div>
					<div class="stat-num">{{ (report.categories || []).length }}<span class="unit">类</span></div>
					<div class="stat-foot">{{ topCatText }}</div>
				</div>
			</div>

			<!-- ============ 7 天趋势 ============ -->
			<div class="panel mt14">
				<div class="panel-title">
					<span class="bar"></span>每日告警趋势
					<span class="panel-hint">横轴为周一至周日，点高的那天值得回头看</span>
				</div>
				<div ref="dailyChartRef" class="chart-daily"></div>
			</div>

			<!-- ============ 类别 + 时段 ============ -->
			<el-row :gutter="14" class="mt14">
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>告警类别分布</div>
						<div v-if="!(report.categories || []).length" class="empty-tip">本周无告警</div>
						<div v-for="c in report.categories" :key="c.name" class="cat-row">
							<div class="cat-name">{{ c.name }}</div>
							<div class="cat-bar-wrap">
								<div class="cat-bar" :style="{ width: barWidth(c.count) }"></div>
							</div>
							<div class="cat-val">{{ c.count }} 条 · {{ c.ratio }}%</div>
						</div>
					</div>
				</el-col>
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title">
							<span class="bar"></span>告警时段分布
							<span class="panel-hint">全周累计</span>
						</div>
						<div ref="hourChartRef" class="chart-hour"></div>
					</div>
				</el-col>
			</el-row>

			<!-- ============ 每日明细 ============ -->
			<div class="panel mt14">
				<div class="panel-title"><span class="bar"></span>每日告警明细</div>
				<el-table :data="report.daily || []" size="small" class="tbl" :default-sort="{ prop: 'date', order: 'ascending' }">
					<el-table-column prop="date" label="日期" width="120" align="center" />
					<el-table-column prop="weekday" label="星期" width="80" align="center" />
					<el-table-column prop="total" label="总量" width="80" align="center" sortable />
					<el-table-column label="严重" width="80" align="center">
						<template #default="{ row }">
							<span :class="row.critical ? 'txt-crit' : 'txt-muted'">{{ row.critical }}</span>
						</template>
					</el-table-column>
					<el-table-column label="警告" width="80" align="center">
						<template #default="{ row }">
							<span :class="row.warning ? 'txt-warn' : 'txt-muted'">{{ row.warning }}</span>
						</template>
					</el-table-column>
					<el-table-column label="提示" width="80" align="center">
						<template #default="{ row }">
							<span :class="row.info ? 'txt-info' : 'txt-muted'">{{ row.info }}</span>
						</template>
					</el-table-column>
					<el-table-column label="主要类别" min-width="200">
						<template #default="{ row }">
							<span v-if="(row.categories || []).length">
								{{ row.categories[0].name }}（{{ row.categories[0].count }}）
								<span v-if="row.categories[1]" class="txt-muted">
									、{{ row.categories[1].name }}（{{ row.categories[1].count }}）
								</span>
							</span>
							<span v-else class="txt-muted">—</span>
						</template>
					</el-table-column>
					<el-table-column label="相对日均" width="110" align="center">
						<template #default="{ row }">
							<span :class="deviationClass(row.total)">{{ deviationText(row.total) }}</span>
						</template>
					</el-table-column>
				</el-table>
			</div>

			<!-- ============ 类型 + 节点 ============ -->
			<el-row :gutter="14" class="mt14">
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>告警类型 TOP 10</div>
						<el-table :data="(report.types || []).slice(0, 10)" size="small" class="tbl">
							<el-table-column type="index" label="#" width="42" align="center" />
							<el-table-column prop="alertname" label="告警类型" min-width="150" show-overflow-tooltip />
							<el-table-column prop="category" label="类别" width="96" show-overflow-tooltip />
							<el-table-column prop="count" label="数量" width="66" align="center" />
							<el-table-column label="占比" width="72" align="center">
								<template #default="{ row }">{{ row.ratio }}%</template>
							</el-table-column>
						</el-table>
					</div>
				</el-col>
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>告警节点 TOP 10</div>
						<el-table :data="(report.nodes || []).slice(0, 10)" size="small" class="tbl">
							<el-table-column type="index" label="#" width="42" align="center" />
							<el-table-column prop="instance" label="节点 / 实例" min-width="150" show-overflow-tooltip />
							<el-table-column prop="hostname" label="主机名" width="100" show-overflow-tooltip>
								<template #default="{ row }">{{ row.hostname || '—' }}</template>
							</el-table-column>
							<el-table-column prop="count" label="数量" width="66" align="center" />
							<el-table-column label="占比" width="72" align="center">
								<template #default="{ row }">{{ row.ratio }}%</template>
							</el-table-column>
						</el-table>
					</div>
				</el-col>
			</el-row>

			<!-- ============ 结论 + 建议 ============ -->
			<el-row :gutter="14" class="mt14">
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>巡检结论</div>
						<ul class="num-list">
							<li v-for="(f, i) in report.findings || []" :key="i">{{ f }}</li>
							<li v-if="!(report.findings || []).length" class="muted">暂无数据</li>
						</ul>
					</div>
				</el-col>
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>巡检建议</div>
						<ol class="num-list ordered">
							<li v-for="(s, i) in report.suggestions || []" :key="i">{{ s }}</li>
							<li v-if="!(report.suggestions || []).length" class="muted">暂无数据</li>
						</ol>
					</div>
				</el-col>
			</el-row>

			<!-- ============ 附注 ============ -->
			<div class="foot-note">
				<p v-if="report.caliber">· 统计口径：{{ report.caliber }}</p>
				<p v-if="report.source_desc">· 数据来源：{{ report.source_desc }}</p>
				<p>· 经 Alertmanager 独立 route 分流、未回调平台的告警不在此列。</p>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { GetWeekly, downloadWeekly } from './api';

defineOptions({ name: 'inspectionWeekly' });

const loading = ref(false);
const exporting = ref({ word: false, excel: false });
const pickDate = ref('');
const report = ref<any>({});
const generatedAt = ref('');

const dailyChartRef = ref();
const hourChartRef = ref();
let dailyChart: echarts.ECharts | null = null;
let hourChart: echarts.ECharts | null = null;

const sevCount = computed(() => {
	const c = report.value?.severity_counts || {};
	return { critical: c.critical || 0, warning: c.warning || 0, info: c.info || 0 };
});

const deltaText = computed(() => {
	const cur = report.value?.total;
	const prev = report.value?.prev_total;
	if (cur === undefined) return '—';
	if (!prev) return '上周无告警，无可比基数';
	const d = cur - prev;
	if (d === 0) return '与上周持平';
	const p = ((d * 100) / prev).toFixed(1);
	return `较上周 ${d > 0 ? '+' : ''}${d} 条（${d > 0 ? '+' : ''}${p}%）`;
});
const deltaClass = computed(() => {
	const cur = report.value?.total ?? 0;
	const prev = report.value?.prev_total ?? 0;
	if (!prev || cur === prev) return 'flat';
	return cur > prev ? 'up' : 'down';
});

const peakText = computed(() => {
	const p = report.value?.peak_day;
	if (!p || !p.date) return '本周无告警';
	return `峰值 ${p.date.slice(5)}（${p.weekday || ''}）${p.total} 条`;
});
const topNodeText = computed(() => {
	const n = (report.value?.nodes || [])[0];
	return n ? `最多 ${n.instance}（${n.count} 条）` : '—';
});
const topCatText = computed(() => {
	const c = (report.value?.categories || [])[0];
	return c ? `${c.name} 占 ${c.ratio}%` : '—';
});

function pct(n: number) {
	const t = report.value?.total || 0;
	return t ? ((n * 100) / t).toFixed(1) : '0.0';
}
function barWidth(n: number) {
	const list = report.value?.categories || [];
	const max = Math.max(...list.map((x: any) => x.count), 1);
	return Math.max((n / max) * 100, 2) + '%';
}
function deviationText(n: number) {
	const avg = report.value?.avg_per_day || 0;
	if (!avg) return '—';
	const d = n - avg;
	if (Math.abs(d) < 0.05) return '持平';
	return (d > 0 ? '+' : '') + d.toFixed(1);
}
function deviationClass(n: number) {
	const avg = report.value?.avg_per_day || 0;
	if (!avg || Math.abs(n - avg) < 0.05) return 'txt-muted';
	return n > avg ? 'txt-crit' : 'txt-ok';
}

function disableFuture(d: Date) {
	return d.getTime() > Date.now();
}
function fmt(d: Date) {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
}
function mondayOf(d: Date) {
	const day = d.getDay() || 7; // 周日 0 → 7
	const m = new Date(d);
	m.setDate(d.getDate() - (day - 1));
	return m;
}

function pick(which: 'lastweek' | 'thisweek') {
	const base = new Date();
	if (which === 'lastweek') base.setDate(base.getDate() - 7);
	pickDate.value = fmt(mondayOf(base));
	load();
}

async function load() {
	if (!pickDate.value) return;
	loading.value = true;
	try {
		const res: any = await GetWeekly({ week: pickDate.value });
		if (res?.code === 2000) {
			report.value = res.data || {};
			generatedAt.value = new Date().toLocaleString('zh-CN', { hour12: false });
			await nextTick();
			renderDaily();
			renderHour();
		} else {
			ElMessage.error(res?.msg || '查询失败');
		}
	} catch (e: any) {
		ElMessage.error(e?.msg || '查询失败，周报需汇总 7 天数据，请稍候重试');
	} finally {
		loading.value = false;
	}
}

async function doExport(kind: 'word' | 'excel') {
	exporting.value[kind] = true;
	try {
		const name = await downloadWeekly(kind, pickDate.value);
		ElMessage.success(`已导出 ${name}`);
	} catch (e: any) {
		ElMessage.error(e?.message || '导出失败');
	} finally {
		exporting.value[kind] = false;
	}
}

function renderDaily() {
	const el = dailyChartRef.value;
	if (!el) return;
	if (!dailyChart) dailyChart = echarts.init(el);
	const list = report.value?.daily || [];
	if (!list.length) {
		dailyChart.clear();
		return;
	}
	const peak = report.value?.peak_day?.date || '';
	dailyChart.setOption({
		grid: { left: 44, right: 20, top: 26, bottom: 30 },
		tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}：${p[0].value} 条` },
		xAxis: {
			type: 'category',
			data: list.map((d: any) => `${d.date.slice(5)} ${d.weekday}`),
			axisLine: { lineStyle: { color: '#DCDFE6' } },
			axisLabel: { color: '#909399', fontSize: 11 },
			axisTick: { show: false },
		},
		yAxis: {
			type: 'value',
			minInterval: 1,
			splitLine: { lineStyle: { color: '#F0F2F5' } },
			axisLabel: { color: '#909399', fontSize: 11 },
		},
		series: [
			{
				type: 'bar',
				barMaxWidth: 38,
				data: list.map((d: any) => ({
					value: d.total,
					itemStyle: {
						borderRadius: [3, 3, 0, 0],
						color: d.date === peak && d.total > 0 ? '#C00000' : '#2E75B6',
					},
				})),
				label: { show: true, position: 'top', fontSize: 11, color: '#606266' },
			},
		],
	}, true);
}

function renderHour() {
	const el = hourChartRef.value;
	if (!el) return;
	if (!hourChart) hourChart = echarts.init(el);
	const hourly = report.value?.hourly || [];
	const max = Math.max(...hourly.map((h: any) => h.count), 1);
	hourChart.setOption({
		grid: { left: 40, right: 16, top: 18, bottom: 28 },
		tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue} 时：${p[0].value} 条` },
		xAxis: {
			type: 'category',
			data: hourly.map((h: any) => String(h.hour).padStart(2, '0')),
			axisLine: { lineStyle: { color: '#DCDFE6' } },
			axisLabel: { color: '#909399', fontSize: 11, interval: 1 },
			axisTick: { show: false },
		},
		yAxis: {
			type: 'value',
			minInterval: 1,
			max: Math.max(max, 2),
			splitLine: { lineStyle: { color: '#F0F2F5' } },
			axisLabel: { color: '#909399', fontSize: 11 },
		},
		series: [
			{
				type: 'bar',
				barMaxWidth: 16,
				data: hourly.map((h: any) => h.count),
				itemStyle: { borderRadius: [2, 2, 0, 0], color: '#5B9BD5' },
			},
		],
	}, true);
}

const handleResize = () => {
	dailyChart?.resize();
	hourChart?.resize();
};

onMounted(() => {
	pick('lastweek');
	window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
	window.removeEventListener('resize', handleResize);
	dailyChart?.dispose();
	hourChart?.dispose();
	dailyChart = null;
	hourChart = null;
});
</script>

<style scoped lang="scss">
.inspection-weekly {
	padding: 14px 16px 24px;
	background: #f5f7fa;
	min-height: calc(100vh - 84px);
	box-sizing: border-box;
}

.toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	flex-wrap: wrap;
	gap: 10px;
	margin-bottom: 14px;
	.field-label {
		font-size: 13px;
		color: #606266;
		margin-right: 8px;
	}
	.toolbar-left,
	.toolbar-right {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.quick-group {
		margin-left: 4px;
	}
	.tip {
		font-size: 12px;
		color: #a8abb2;
	}
}

.report-head {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	background: #fff;
	border: 1px solid #e4e7ed;
	border-radius: 8px;
	padding: 18px 22px;
	border-left: 4px solid #1f3864;
	.head-title {
		font-size: 20px;
		font-weight: 700;
		color: #1f3864;
		letter-spacing: 0.5px;
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.head-badge {
		font-size: 12px;
		font-weight: 500;
		color: #fff;
		background: #2e75b6;
		border-radius: 3px;
		padding: 2px 8px;
	}
	.head-sub {
		margin-top: 6px;
		font-size: 12.5px;
		color: #909399;
		.dot {
			margin: 0 6px;
			color: #c0c4cc;
		}
	}
}

.stat-row {
	display: grid;
	grid-template-columns: repeat(5, minmax(0, 1fr));
	gap: 14px;
	margin-top: 14px;
}
.stat-card {
	background: #fff;
	border: 1px solid #e4e7ed;
	border-radius: 8px;
	padding: 14px 16px 12px;
	.stat-label {
		font-size: 12.5px;
		color: #909399;
	}
	.stat-num {
		margin-top: 6px;
		font-size: 26px;
		font-weight: 700;
		color: #1f3864;
		line-height: 1.15;
		&.sev-line {
			font-size: 22px;
			.crit {
				color: #c00000;
			}
			.warn {
				color: #c55a11;
			}
			.info {
				color: #8496b0;
			}
			.slash {
				color: #dcdfe6;
				font-weight: 400;
				margin: 0 4px;
			}
		}
		.unit {
			font-size: 12px;
			font-weight: 400;
			color: #909399;
			margin-left: 3px;
		}
	}
	.stat-foot {
		margin-top: 4px;
		font-size: 11.5px;
		color: #909399;
		&.up {
			color: #c00000;
		}
		&.down {
			color: #548235;
		}
	}
}

.panel {
	background: #fff;
	border: 1px solid #e4e7ed;
	border-radius: 8px;
	padding: 14px 18px 16px;
	&.panel-fill {
		height: 100%;
		box-sizing: border-box;
	}
	.panel-title {
		display: flex;
		align-items: center;
		font-size: 14px;
		font-weight: 600;
		color: #1f3864;
		margin-bottom: 10px;
		.bar {
			width: 3px;
			height: 14px;
			background: #2e75b6;
			border-radius: 2px;
			margin-right: 8px;
		}
		.panel-hint {
			margin-left: 10px;
			font-size: 12px;
			font-weight: 400;
			color: #a8abb2;
		}
	}
}
.mt14 {
	margin-top: 14px;
}
.chart-daily {
	height: 220px;
}
.chart-hour {
	height: 200px;
}

.cat-row {
	display: grid;
	grid-template-columns: 82px 1fr 104px;
	align-items: center;
	gap: 10px;
	padding: 8px 0;
	border-bottom: 1px dashed #f0f2f5;
	&:last-child {
		border-bottom: none;
	}
	.cat-name {
		font-size: 12.5px;
		color: #303133;
	}
	.cat-bar-wrap {
		height: 10px;
		background: #f2f5fa;
		border-radius: 5px;
		overflow: hidden;
	}
	.cat-bar {
		height: 100%;
		background: linear-gradient(90deg, #2e75b6, #5b9bd5);
		border-radius: 5px;
		transition: width 0.35s ease;
	}
	.cat-val {
		font-size: 12px;
		color: #606266;
		text-align: right;
	}
}

.tbl {
	:deep(.el-table__header th) {
		background: #f7f9fc;
		color: #1f3864;
		font-weight: 600;
		font-size: 12.5px;
	}
	:deep(.el-table__body td) {
		font-size: 12.5px;
	}
}

.num-list {
	margin: 0;
	padding-left: 20px;
	li {
		font-size: 12.8px;
		line-height: 1.85;
		color: #303133;
		&.muted {
			color: #a8abb2;
			list-style: none;
			margin-left: -20px;
		}
	}
	&.ordered {
		padding-left: 22px;
	}
}

.foot-note {
	margin-top: 14px;
	padding: 10px 16px;
	background: #fafbfc;
	border: 1px dashed #e4e7ed;
	border-radius: 6px;
	p {
		margin: 3px 0;
		font-size: 11.5px;
		color: #a8abb2;
		line-height: 1.6;
	}
}

.empty-tip {
	padding: 24px 0;
	text-align: center;
	color: #a8abb2;
	font-size: 12.5px;
}
.txt-ok {
	color: #548235;
}
.txt-warn {
	color: #c55a11;
}
.txt-crit {
	color: #c00000;
	font-weight: 600;
}
.txt-info {
	color: #8496b0;
}
.txt-muted {
	color: #c0c4cc;
}

@media (max-width: 1200px) {
	.stat-row {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
