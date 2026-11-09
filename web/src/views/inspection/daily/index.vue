<template>
	<div class="inspection-daily">
		<!-- ============ 工具栏 ============ -->
		<div class="toolbar">
			<div class="toolbar-left">
				<span class="field-label">巡检日期</span>
				<el-date-picker
					v-model="queryDate"
					type="date"
					value-format="YYYY-MM-DD"
					placeholder="选择日期"
					:clearable="false"
					:disabled-date="disableFuture"
					style="width: 156px"
					@change="load"
				/>
				<el-button-group class="quick-group">
					<el-button @click="pick('yesterday')">昨天</el-button>
					<el-button @click="pick('today')">今天</el-button>
				</el-button-group>
				<el-button type="primary" :loading="loading" @click="load">生成报告</el-button>
			</div>
			<div class="toolbar-right">
				<el-button :loading="exporting.word" :disabled="!report.total && report.total !== 0" @click="doExport('word')">
					导出 Word 报告
				</el-button>
				<el-button :loading="exporting.excel" :disabled="!report.total && report.total !== 0" @click="doExport('excel')">
					导出 Excel 附表
				</el-button>
			</div>
		</div>

		<div v-loading="loading" element-loading-text="正在汇总告警与监控数据…">
			<!-- ============ 报告头 ============ -->
			<div class="report-head">
				<div class="head-main">
					<div class="head-title">运维巡检报告</div>
					<div class="head-sub">
						巡检日期 {{ report.date || queryDate }}（{{ report.weekday || '—' }}）
						<span class="dot">·</span>
						生成时间 {{ report.generated_at || '—' }}
					</div>
				</div>
				<div class="head-tag">DevOps 平台自动生成</div>
			</div>

			<!-- ============ 概览卡片 ============ -->
			<div class="stat-row">
				<div class="stat-card">
					<div class="stat-label">告警总量</div>
					<div class="stat-num">{{ report.total ?? 0 }}<span class="unit">条</span></div>
					<div class="stat-foot" :class="deltaClass">{{ deltaText }}</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">严重</div>
					<div class="stat-num crit">{{ sevCount.critical }}</div>
					<div class="stat-foot">占 {{ pct(sevCount.critical) }}%</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">警告</div>
					<div class="stat-num warn">{{ sevCount.warning }}</div>
					<div class="stat-foot">占 {{ pct(sevCount.warning) }}%</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">提示</div>
					<div class="stat-num info">{{ sevCount.info }}</div>
					<div class="stat-foot">占 {{ pct(sevCount.info) }}%</div>
				</div>
				<div class="stat-card">
					<div class="stat-label">涉及节点</div>
					<div class="stat-num">{{ (report.nodes || []).length }}<span class="unit">个</span></div>
					<div class="stat-foot">{{ unresolvedCount }} 条未恢复</div>
				</div>
			</div>

			<!-- ============ 级别 + 类别 ============ -->
			<el-row :gutter="14" class="mt14">
				<el-col :xs="24" :sm="24" :md="9">
					<div class="panel">
						<div class="panel-title"><span class="bar"></span>告警级别分布</div>
						<div ref="sevChartRef" class="chart-sev"></div>
					</div>
				</el-col>
				<el-col :xs="24" :sm="24" :md="15">
					<div class="panel">
						<div class="panel-title">
							<span class="bar"></span>告警类别分布
							<span class="panel-hint">按技术域收敛，看哪一类问题最集中</span>
						</div>
						<div v-if="!report.categories || !report.categories.length" class="empty-tip">当日无告警</div>
						<div v-for="c in report.categories" :key="c.name" class="cat-row">
							<div class="cat-name">{{ c.name }}</div>
							<div class="cat-bar-wrap">
								<div class="cat-bar" :style="{ width: barWidth(c.count) }"></div>
							</div>
							<div class="cat-val">{{ c.count }} 条 · {{ c.ratio }}%</div>
							<div class="cat-top" :title="c.top_type">{{ c.top_type }}</div>
						</div>
					</div>
				</el-col>
			</el-row>

			<!-- ============ 时段分布 ============ -->
			<div class="panel mt14">
				<div class="panel-title">
					<span class="bar"></span>告警时段分布（0—23 时）
					<span class="panel-hint">峰值 {{ String(report.peak_hour ?? 0).padStart(2, '0') }} 时，{{ report.peak_count ?? 0 }} 条</span>
				</div>
				<div ref="hourChartRef" class="chart-hour"></div>
			</div>

			<!-- ============ 类型 + 节点 ============ -->
			<el-row :gutter="14" class="mt14">
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>告警类型 TOP {{ (report.top_types || []).length }}</div>
						<el-table :data="report.top_types || []" size="small" :show-header="true" class="tbl">
							<el-table-column type="index" label="#" width="42" align="center" />
							<el-table-column prop="name_cn" label="告警类型" min-width="130" show-overflow-tooltip />
							<el-table-column prop="category" label="类别" width="96" show-overflow-tooltip />
							<el-table-column prop="count" label="数量" width="66" align="center" />
							<el-table-column label="占比" width="72" align="center">
								<template #default="{ row }">{{ pct(row.count) }}%</template>
							</el-table-column>
						</el-table>
					</div>
				</el-col>
				<el-col :xs="24" :sm="24" :md="12">
					<div class="panel panel-fill">
						<div class="panel-title"><span class="bar"></span>告警节点 TOP {{ (report.top_nodes || []).length }}</div>
						<el-table :data="report.top_nodes || []" size="small" class="tbl">
							<el-table-column type="index" label="#" width="42" align="center" />
							<el-table-column prop="instance" label="节点 / 实例" min-width="130" show-overflow-tooltip />
							<el-table-column prop="hostname" label="主机名" width="100" show-overflow-tooltip>
								<template #default="{ row }">{{ row.hostname || '—' }}</template>
							</el-table-column>
							<el-table-column prop="count" label="数量" width="66" align="center" />
							<el-table-column label="占比" width="72" align="center">
								<template #default="{ row }">{{ pct(row.count) }}%</template>
							</el-table-column>
						</el-table>
					</div>
				</el-col>
			</el-row>

			<!-- ============ 监控覆盖 ============ -->
			<div class="panel mt14">
				<div class="panel-title"><span class="bar"></span>监控覆盖检查</div>
				<el-table :data="report.coverage || []" size="small" class="tbl">
					<el-table-column prop="item" label="检查项" min-width="180" />
					<el-table-column prop="expect" label="期望值" width="120" align="center" />
					<el-table-column prop="actual" label="实际值" width="160" align="center" />
					<el-table-column prop="result" label="结论" min-width="200">
						<template #default="{ row }">
							<span :class="row.result && row.result.indexOf('正常') === 0 ? 'txt-ok' : 'txt-warn'">{{ row.result }}</span>
						</template>
					</el-table-column>
				</el-table>
			</div>

			<!-- ============ 未恢复 ============ -->
			<div v-if="(report.unresolved || []).length" class="panel mt14">
				<div class="panel-title">
					<span class="bar bar-crit"></span>未恢复告警
					<span class="panel-hint">截至报告生成仍未闭环</span>
				</div>
				<el-table :data="report.unresolved" size="small" class="tbl">
					<el-table-column prop="alertname_cn" label="告警类型" min-width="160" show-overflow-tooltip />
					<el-table-column prop="instance" label="节点" min-width="130" show-overflow-tooltip />
					<el-table-column prop="severity_cn" label="级别" width="72" align="center" />
					<el-table-column prop="starts_at" label="触发时间" width="150" align="center" />
					<el-table-column label="持续时长" width="110" align="center">
						<template #default="{ row }">
							<span class="txt-crit">{{ row.duration_hours }} 小时</span>
						</template>
					</el-table-column>
				</el-table>
			</div>

			<!-- ============ 结论 ============ -->
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
				<p v-for="(n, i) in report.data_notes || []" :key="'n' + i">· {{ n }}</p>
				<p>· 统计口径：{{ report.caliber || '按告警触发时间落在当日统计' }}</p>
				<p v-if="report.extra_note">· {{ report.extra_note }}</p>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { computed, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { GetDaily, downloadReport } from './api';

defineOptions({ name: 'inspectionDaily' });

const loading = ref(false);
const exporting = ref({ word: false, excel: false });
const queryDate = ref('');
const report = ref<any>({});

const sevChartRef = ref();
const hourChartRef = ref();
let sevChart: echarts.ECharts | null = null;
let hourChart: echarts.ECharts | null = null;

const SEV_COLOR: Record<string, string> = {
	critical: '#C00000',
	warning: '#C55A11',
	info: '#8496B0',
	other: '#909399',
};
const CN_OF: Record<string, string> = { critical: '严重', warning: '警告', info: '提示', other: '其他' };

const sevCount = computed(() => {
	const c = report.value?.severity_counts || {};
	return { critical: c.critical || 0, warning: c.warning || 0, info: c.info || 0 };
});
const unresolvedCount = computed(() => (report.value?.unresolved || []).length);

const deltaText = computed(() => {
	const cur = report.value?.total;
	const prev = report.value?.prev_total;
	if (cur === undefined) return '—';
	if (!prev) return '前一日无告警';
	const d = cur - prev;
	if (d === 0) return '与前一日持平';
	return `较前一日 ${d > 0 ? '+' : ''}${d} 条`;
});
const deltaClass = computed(() => {
	const cur = report.value?.total ?? 0;
	const prev = report.value?.prev_total ?? 0;
	if (!prev || cur === prev) return 'flat';
	return cur > prev ? 'up' : 'down';
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

function disableFuture(d: Date) {
	return d.getTime() > Date.now();
}

function fmt(d: Date) {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
}

function pick(which: 'today' | 'yesterday') {
	const d = new Date();
	if (which === 'yesterday') d.setDate(d.getDate() - 1);
	queryDate.value = fmt(d);
	load();
}

async function load() {
	loading.value = true;
	try {
		const res: any = await GetDaily({ date: queryDate.value });
		if (res?.code === 2000) {
			report.value = res.data || {};
			await nextTick();
			renderSev();
			renderHour();
		} else {
			ElMessage.error(res?.msg || '查询失败');
		}
	} catch (e: any) {
		ElMessage.error(e?.msg || '查询失败');
	} finally {
		loading.value = false;
	}
}

function renderSev() {
	const el = sevChartRef.value;
	if (!el) return;
	if (!sevChart) sevChart = echarts.init(el);
	const data = Object.keys(CN_OF)
		.map((k) => ({ name: CN_OF[k], value: sevCount.value[k as 'critical'] || 0, key: k }))
		.filter((x) => x.value > 0);
	if (!data.length) {
		sevChart.setOption({ title: { text: '当日无告警', left: 'center', top: 'middle', textStyle: { color: '#909399', fontSize: 13, fontWeight: 'normal' } }, series: [] }, true);
		return;
	}
	sevChart.setOption({
		tooltip: { trigger: 'item', formatter: '{b}：{c} 条（{d}%）' },
		legend: { bottom: 0, itemWidth: 9, itemHeight: 9, textStyle: { fontSize: 12, color: '#606266' } },
		series: [
			{
				type: 'pie',
				radius: ['52%', '74%'],
				center: ['50%', '44%'],
				avoidLabelOverlap: true,
				itemStyle: { borderColor: '#fff', borderWidth: 2 },
				label: { show: false },
				emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', formatter: '{b}\n{c} 条' } },
				data: data.map((x) => ({ ...x, itemStyle: { color: SEV_COLOR[x.key] } })),
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
				data: hourly.map((h: any) => h.count),
				barMaxWidth: 22,
				itemStyle: {
					borderRadius: [3, 3, 0, 0],
					color: (p: any) => (p.value > 0 ? '#2E75B6' : '#EAF1F8'),
				},
			},
		],
	}, true);
}

async function doExport(kind: 'word' | 'excel') {
	exporting.value[kind] = true;
	try {
		const name = await downloadReport(kind, queryDate.value);
		ElMessage.success(`已导出 ${name}`);
	} catch (e: any) {
		ElMessage.error(e?.message || '导出失败');
	} finally {
		exporting.value[kind] = false;
	}
}

const handleResize = () => {
	sevChart?.resize();
	hourChart?.resize();
};

onMounted(() => {
	pick('yesterday');
	window.addEventListener('resize', handleResize);
});

onActivated(() => {
	// keep-alive 回到本页时不自动重查，避免打断用户已选的日期
});

onDeactivated(() => {});

onUnmounted(() => {
	window.removeEventListener('resize', handleResize);
	sevChart?.dispose();
	hourChart?.dispose();
	sevChart = null;
	hourChart = null;
});
</script>

<style scoped lang="scss">
.inspection-daily {
	padding: 14px 16px 24px;
	background: #f5f7fa;
	min-height: calc(100vh - 84px);
	box-sizing: border-box;
}

/* ---------- 工具栏 ---------- */
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
}

/* ---------- 报告头 ---------- */
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
	.head-tag {
		font-size: 12px;
		color: #2e75b6;
		background: #eaf1f8;
		border-radius: 4px;
		padding: 3px 10px;
	}
}

/* ---------- 概览卡 ---------- */
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
		&.crit {
			color: #c00000;
		}
		&.warn {
			color: #c55a11;
		}
		&.info {
			color: #8496b0;
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

/* ---------- 面板 ---------- */
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
			&.bar-crit {
				background: #c00000;
			}
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

.chart-sev {
	height: 210px;
}
.chart-hour {
	height: 190px;
}

/* ---------- 类别条形 ---------- */
.cat-row {
	display: grid;
	grid-template-columns: 82px 1fr 96px 1.1fr;
	align-items: center;
	gap: 10px;
	padding: 7px 0;
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
	.cat-top {
		font-size: 11.5px;
		color: #a8abb2;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
}

/* ---------- 表格 ---------- */
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

/* ---------- 结论 ---------- */
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

/* ---------- 附注 ---------- */
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

@media (max-width: 1200px) {
	.stat-row {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
