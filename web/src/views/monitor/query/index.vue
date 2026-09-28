<template>
	<fs-page>
		<div class="monitor-query">
			<!-- 查询工具栏 -->
			<el-card shadow="never" class="toolbar-card">
				<div class="toolbar">
					<el-select v-model="sourceId" placeholder="选择数据源" style="width: 220px" @change="onSourceChange">
						<el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
					</el-select>
					<el-input v-model="query" placeholder="输入 PromQL，如 node_memory_MemAvailable_bytes" clearable @keyup.enter="doQuery">
						<template #prepend>PromQL</template>
					</el-input>
					<el-button type="primary" :loading="queryLoading" @click="doQuery">查询</el-button>
				</div>
				<div class="quick-metrics">
					<span class="quick-label">常用指标：</span>
					<el-tag v-for="m in quickMetrics" :key="m.expr" class="quick-tag" effect="plain" @click="quickQuery(m)">{{ m.label }}</el-tag>
				</div>
			</el-card>

			<!-- 结果区域 -->
			<el-card shadow="never">
				<el-tabs v-model="activeTab">
					<el-tab-pane label="查询结果" name="result">
						<el-alert v-if="queryError" :title="queryError" type="error" show-icon :closable="false" style="margin-bottom: 10px" />
						<el-table :data="resultRows" border size="small" v-loading="queryLoading" empty-text="请输入 PromQL 并点击查询">
							<el-table-column prop="metric" label="标签 (Metric)" min-width="320" show-overflow-tooltip />
							<el-table-column prop="value" label="值" min-width="180" show-overflow-tooltip />
							<el-table-column prop="timestamp" label="时间" width="180" />
						</el-table>
					</el-tab-pane>
					<el-tab-pane label="告警" name="alerts">
						<div class="alert-bar">
							<el-button size="small" type="primary" :loading="alertLoading" @click="loadAlerts">刷新告警</el-button>
							<span class="alert-count" v-if="alerts.length">共 {{ alerts.length }} 条</span>
						</div>
						<el-table :data="alerts" border size="small" v-loading="alertLoading" empty-text="暂无告警">
							<el-table-column label="状态" width="90">
								<template #default="{ row }">
									<el-tag :type="row.state === 'firing' ? 'danger' : 'warning'" size="small">{{ row.state }}</el-tag>
								</template>
							</el-table-column>
							<el-table-column label="告警名" min-width="180">
								<template #default="{ row }">{{ row.labels?.alertname || '-' }}</template>
							</el-table-column>
							<el-table-column label="摘要" min-width="300" show-overflow-tooltip>
								<template #default="{ row }">{{ row.annotations?.summary || row.annotations?.description || '-' }}</template>
							</el-table-column>
							<el-table-column label="开始时间" width="180">
								<template #default="{ row }">{{ formatTime(row.activeAt) }}</template>
							</el-table-column>
						</el-table>
					</el-tab-pane>
				</el-tabs>
			</el-card>
		</div>
	</fs-page>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { GetSources, Query, GetAlerts } from './api';

interface MetricRow {
	metric: string;
	value: string;
	timestamp: string;
}

export default defineComponent({
	name: "monitorQuery",
	setup() {
		const sources = ref<any[]>([]);
		const sourceId = ref<number | null>(null);
		const query = ref('up');
		const queryLoading = ref(false);
		const queryError = ref('');
		const resultRows = ref<MetricRow[]>([]);
		const activeTab = ref('result');
		const alerts = ref<any[]>([]);
		const alertLoading = ref(false);

		const quickMetrics = [
			{ label: '实例存活', expr: 'up' },
			{ label: '可用内存', expr: 'node_memory_MemAvailable_bytes' },
			{ label: '磁盘可用', expr: 'node_filesystem_avail_bytes{fstype=~"ext4|xfs"}' },
			{ label: 'CPU 使用率', expr: '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)' },
			{ label: '系统负载', expr: 'node_load1' },
			{ label: '内存使用率', expr: '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100' },
		];

		const loadSources = async () => {
			const res: any = await GetSources();
			if (res.code === 2000 && res.data?.length) {
				sources.value = res.data;
				if (!sourceId.value) {
					sourceId.value = res.data[0].id;
				}
			}
		};

		const onSourceChange = () => {
			if (activeTab.value === 'alerts') loadAlerts();
		};

		const parseResult = (data: any): MetricRow[] => {
			if (!data || data.status !== 'success') return [];
			const rows: MetricRow[] = [];
			const resultType = data.data?.resultType;
			const result = data.data?.result;
			if (resultType === 'vector' || resultType === 'matrix') {
				for (const item of result || []) {
					const metric = Object.entries(item.metric || {})
						.map(([k, v]) => `${k}="${v}"`)
						.join(', ');
					let value = '-';
					let timestamp = '-';
					if (resultType === 'vector' && item.value) {
						value = String(item.value[1]);
						timestamp = formatTime(item.value[0]);
					} else if (resultType === 'matrix' && item.values?.length) {
						const last = item.values[item.values.length - 1];
						value = String(last[1]);
						timestamp = formatTime(last[0]);
					}
					rows.push({ metric: metric || '-', value, timestamp });
				}
			} else if (resultType === 'scalar' && Array.isArray(result)) {
				rows.push({ metric: '(scalar)', value: String(result[1]), timestamp: formatTime(result[0]) });
			} else if (resultType === 'string' && Array.isArray(result)) {
				rows.push({ metric: '(string)', value: String(result[1]), timestamp: formatTime(result[0]) });
			}
			return rows;
		};

		const doQuery = async () => {
			if (!sourceId.value) { ElMessage.warning('请先选择数据源'); return; }
			if (!query.value.trim()) { ElMessage.warning('请输入 PromQL'); return; }
			queryLoading.value = true;
			queryError.value = '';
			try {
				const res: any = await Query(sourceId.value, query.value.trim());
				if (res.code === 2000) {
					resultRows.value = parseResult(res.data);
					if (!resultRows.value.length) {
						queryError.value = '查询无结果';
					}
				} else {
					queryError.value = res.msg || '查询失败';
					resultRows.value = [];
				}
			} catch (e: any) {
				queryError.value = e?.message || '查询异常';
				resultRows.value = [];
			} finally {
				queryLoading.value = false;
			}
		};

		const quickQuery = (m: any) => {
			query.value = m.expr;
			doQuery();
		};

		const loadAlerts = async () => {
			if (!sourceId.value) { ElMessage.warning('请先选择数据源'); return; }
			alertLoading.value = true;
			try {
				const res: any = await GetAlerts(sourceId.value);
				if (res.code === 2000) {
					alerts.value = res.data?.data?.alerts || [];
				}
			} finally {
				alertLoading.value = false;
			}
		};

		const formatTime = (ts: any): string => {
			if (ts == null) return '-';
			const t = typeof ts === 'number' ? ts : Number(ts);
			if (!t) return '-';
			const d = new Date(t * 1000);
			return d.toLocaleString('zh-CN', { hour12: false });
		};

		onMounted(() => {
			loadSources().then(() => doQuery());
		});

		return {
			sources, sourceId, query, queryLoading, queryError, resultRows,
			activeTab, alerts, alertLoading, quickMetrics,
			onSourceChange, doQuery, quickQuery, loadAlerts, formatTime,
		};
	}
});
</script>

<style scoped>
.monitor-query .toolbar-card {
	margin-bottom: 12px;
}
.toolbar {
	display: flex;
	gap: 10px;
	align-items: center;
}
.toolbar .el-input {
	flex: 1;
}
.quick-metrics {
	margin-top: 10px;
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px;
}
.quick-label {
	color: #909399;
	font-size: 13px;
}
.quick-tag {
	cursor: pointer;
}
.alert-bar {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-bottom: 10px;
}
.alert-count {
	color: #909399;
	font-size: 13px;
}
</style>
