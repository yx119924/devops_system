<template>
	<fs-page>
		<div class="jenkins-job">
			<!-- 工具栏 -->
			<el-card shadow="never" class="toolbar-card">
				<div class="toolbar">
					<el-select v-model="serverId" placeholder="选择 Jenkins 服务器" style="width: 240px" @change="onServerChange">
						<el-option v-for="s in servers" :key="s.id" :label="s.name" :value="s.id">
							<span>{{ s.name }}</span>
							<span class="opt-url">{{ s.url }}</span>
						</el-option>
					</el-select>
					<el-button type="primary" :loading="jobLoading" @click="loadJobs">刷新 Job 列表</el-button>
					<span class="job-count" v-if="jobs.length">共 {{ jobs.length }} 个 Job</span>
				</div>
			</el-card>

			<!-- Job 列表 -->
			<el-card shadow="never">
				<el-table :data="jobs" border size="small" v-loading="jobLoading" empty-text="请先选择 Jenkins 服务器">
					<el-table-column prop="name" label="Job 名称" min-width="240" show-overflow-tooltip>
						<template #default="{ row }">
							<el-link type="primary" :href="row.url" target="_blank" :underline="false">{{ row.name }}</el-link>
						</template>
					</el-table-column>
					<el-table-column label="状态" width="110" align="center">
						<template #default="{ row }">
							<el-tag :type="colorInfo(row.color).type" size="small" effect="light">{{ colorInfo(row.color).label }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column label="最近构建" width="120" align="center">
						<template #default="{ row }">
							<span v-if="row.lastBuild">{{ row.lastBuild.number }} / {{ row.lastBuild.result }}</span>
							<span v-else>-</span>
						</template>
					</el-table-column>
					<el-table-column label="描述" min-width="180" show-overflow-tooltip>
						<template #default="{ row }">{{ row.description || '-' }}</template>
					</el-table-column>
					<el-table-column label="操作" width="200" align="center" fixed="right">
						<template #default="{ row }">
							<el-button size="small" type="primary" @click="onBuild(row)">触发构建</el-button>
							<el-button size="small" @click="onViewLog(row)">查看日志</el-button>
						</template>
					</el-table-column>
				</el-table>
			</el-card>

			<!-- 日志弹窗 -->
			<el-dialog v-model="logDialogVisible" :title="`构建日志 - ${logJob}`" width="72%" top="6vh" destroy-on-close>
				<div class="log-toolbar">
					<el-button size="small" :loading="logLoading" @click="loadLog">刷新日志</el-button>
					<el-checkbox v-model="autoScroll" size="small" style="margin-left: 10px">自动滚动</el-checkbox>
					<span class="log-status" v-if="logBuilding">
						<el-tag type="warning" size="small">构建中...</el-tag>
					</span>
					<span class="log-status" v-else-if="logLoaded">
						<el-tag :type="logResult === 'SUCCESS' ? 'success' : 'danger'" size="small">{{ logResult || '已结束' }}</el-tag>
					</span>
				</div>
				<pre class="log-body" ref="logBodyRef" v-html="logText"></pre>
			</el-dialog>
		</div>
	</fs-page>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { GetServers, GetJobs, Build, GetJobStatus, GetConsole } from './api';

export default defineComponent({
	name: "jenkinsJob",
	setup() {
		const servers = ref<any[]>([]);
		const serverId = ref<number | null>(null);
		const jobs = ref<any[]>([]);
		const jobLoading = ref(false);

		// 日志弹窗
		const logDialogVisible = ref(false);
		const logJob = ref('');
		const logText = ref('');
		const logLoading = ref(false);
		const logBuilding = ref(false);
		const logLoaded = ref(false);
		const logResult = ref('');
		const autoScroll = ref(true);
		const logBodyRef = ref<any>(null);
		let logTimer: any = null;

		const colorInfo = (color: string) => {
			const map: Record<string, { label: string; type: string }> = {
				'blue': { label: '成功', type: 'success' },
				'blue_anime': { label: '构建中', type: 'success' },
				'red': { label: '失败', type: 'danger' },
				'red_anime': { label: '构建中', type: 'danger' },
				'aborted': { label: '已中止', type: 'info' },
				'aborted_anime': { label: '中止中', type: 'info' },
				'notbuilt': { label: '未构建', type: 'info' },
				'notbuilt_anime': { label: '构建中', type: 'info' },
				'disabled': { label: '已禁用', type: 'info' },
				'yellow': { label: '不稳定', type: 'warning' },
				'yellow_anime': { label: '构建中', type: 'warning' },
			};
			return map[color] || { label: color || '未知', type: 'info' };
		};

		const loadServers = async () => {
			const res: any = await GetServers();
			if (res.code === 2000 && res.data?.length) {
				servers.value = res.data;
				if (!serverId.value) {
					serverId.value = res.data[0].id;
					loadJobs();
				}
			} else if (res.code === 2000) {
				ElMessage.info('还没有 Jenkins 服务器，请先到「Jenkins 服务器」页面添加');
			}
		};

		const onServerChange = () => {
			jobs.value = [];
			loadJobs();
		};

		const loadJobs = async () => {
			if (!serverId.value) { ElMessage.warning('请先选择 Jenkins 服务器'); return; }
			jobLoading.value = true;
			try {
				const res: any = await GetJobs(serverId.value);
				if (res.code === 2000) {
					jobs.value = res.data?.jobs || [];
				} else {
					ElMessage.error(res.msg || '获取 Job 列表失败');
					jobs.value = [];
				}
			} finally {
				jobLoading.value = false;
			}
		};

		const onBuild = async (row: any) => {
			if (!serverId.value) return;
			try {
				const { value } = await ElMessageBox.prompt(
					'可选填参数化构建参数（JSON 格式，如 {"branch":"master"}），留空则为普通构建',
					`触发构建：${row.name}`,
					{ confirmButtonText: '触发', cancelButtonText: '取消', inputPlaceholder: '{"branch":"master"}（可留空）' }
				);
				let parameters: any = {};
				if (value && value.trim()) {
					try {
						parameters = JSON.parse(value.trim());
					} catch {
						ElMessage.error('参数不是合法 JSON，请重新输入');
						return;
					}
				}
				const res: any = await Build(serverId.value, row.name, parameters);
				if (res.code === 2000) {
					ElMessage.success(res.msg || '已触发构建');
					// 触发后自动打开日志
					openLog(row.name);
				} else {
					ElMessage.error(res.msg || '触发构建失败');
				}
			} catch (e: any) {
				if (e === 'cancel' || e === 'close') return;
				ElMessage.error(e?.message || '触发构建异常');
			}
		};

		const onViewLog = (row: any) => {
			openLog(row.name);
		};

		const openLog = (jobName: string) => {
			logJob.value = jobName;
			logText.value = '';
			logBuilding.value = true;
			logLoaded.value = false;
			logResult.value = '';
			logDialogVisible.value = true;
			loadLog(true);
			startLogPolling();
		};

		const loadLog = async (first = false) => {
			if (!serverId.value || !logJob.value) return;
			logLoading.value = true;
			try {
				if (first) {
					// 先拿 lastBuild 号
					const st: any = await GetJobStatus(serverId.value, logJob.value);
					if (st.code === 2000 && st.data?.number != null) {
						logBuildNumber.value = st.data.number;
					} else {
						logText.value = '该 Job 还没有构建记录';
						logBuilding.value = false;
						logLoaded.value = true;
						return;
					}
				}
				const res: any = await GetConsole(serverId.value, logJob.value, logBuildNumber.value, logStart.value);
				if (res.code === 2000) {
					logText.value += res.data?.text || '';
					logStart.value = Number(res.data?.size || logStart.value);
					const more = res.data?.more;
					// 同步构建状态
					const st2: any = await GetJobStatus(serverId.value, logJob.value);
					logBuilding.value = !!st2.data?.building;
					logResult.value = st2.data?.result || '';
					logLoaded.value = true;
					if (!more && !logBuilding.value) {
						stopLogPolling();
					}
					if (autoScroll.value) scrollToBottom();
				}
			} finally {
				logLoading.value = false;
			}
		};

		const logBuildNumber = ref('lastBuild');
		const logStart = ref(0);

		const startLogPolling = () => {
			stopLogPolling();
			logTimer = setInterval(() => {
				if (!logDialogVisible.value) { stopLogPolling(); return; }
				loadLog();
			}, 3000);
		};

		const stopLogPolling = () => {
			if (logTimer) { clearInterval(logTimer); logTimer = null; }
		};

		const scrollToBottom = async () => {
			await nextTick();
			const el = logBodyRef.value;
			if (el) el.scrollTop = el.scrollHeight;
		};

		onMounted(() => {
			loadServers();
		});

		onBeforeUnmount(() => {
			stopLogPolling();
		});

		return {
			servers, serverId, jobs, jobLoading,
			logDialogVisible, logJob, logText, logLoading, logBuilding, logLoaded, logResult,
			autoScroll, logBodyRef,
			colorInfo, onServerChange, loadJobs, onBuild, onViewLog, loadLog,
		};
	}
});
</script>

<style scoped>
.jenkins-job .toolbar-card {
	margin-bottom: 12px;
}
.toolbar {
	display: flex;
	gap: 10px;
	align-items: center;
}
.opt-url {
	float: right;
	color: #909399;
	font-size: 12px;
	margin-left: 12px;
}
.job-count {
	color: #909399;
	font-size: 13px;
}
.log-toolbar {
	display: flex;
	align-items: center;
	margin-bottom: 8px;
}
.log-status {
	margin-left: 10px;
}
.log-body {
	background: #1e1e1e;
	color: #d4d4d4;
	padding: 12px;
	border-radius: 4px;
	max-height: 60vh;
	overflow: auto;
	font-size: 13px;
	line-height: 1.6;
	white-space: pre-wrap;
	word-break: break-all;
	margin: 0;
}
</style>
