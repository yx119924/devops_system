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
					<el-button type="primary" :loading="jobLoading" @click="loadJobs(true)">刷新 Job 列表</el-button>
					<span class="job-count" v-if="jobs.length">共 {{ jobs.length }} 项（含目录）</span>
					<span class="job-count restricted" v-if="restricted && allowedPaths && allowedPaths.length">
						可见目录：{{ allowedPaths.join('、') }}
					</span>
				</div>
			</el-card>

			<!-- Job 列表（树形，folder 可点击展开/收起） -->
			<el-card shadow="never">
				<el-table :data="jobTree" border size="small" v-loading="jobLoading" :empty-text="emptyText"
					row-key="full_path" :tree-props="{ children: 'children' }">
					<el-table-column label="Job / 目录" min-width="300" show-overflow-tooltip>
						<template #default="{ row }">
							<span v-if="row.is_folder" class="folder-name">{{ row.name }}</span>
							<el-link v-else type="primary" :href="row.url" target="_blank" :underline="false">{{ row.name }}</el-link>
						</template>
					</el-table-column>
					<el-table-column label="状态" width="100" align="center">
						<template #default="{ row }">
							<span v-if="row.is_folder">-</span>
							<el-tag v-else :type="colorInfo(row.color).type" size="small" effect="light">{{ colorInfo(row.color).label }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column label="完整路径" min-width="220" show-overflow-tooltip>
						<template #default="{ row }">
							<span class="path-text">{{ row.full_path }}</span>
						</template>
					</el-table-column>
					<el-table-column label="操作" width="200" align="center" fixed="right">
						<template #default="{ row }">
							<template v-if="!row.is_folder">
								<el-button v-if="hasAuth('jenkinsJob:Build')" size="small" type="primary" :loading="probingJob === row.full_path" @click="onBuild(row)">触发构建</el-button>
								<el-button v-if="hasAuth('jenkinsJob:Console')" size="small" @click="onViewLog(row)">查看日志</el-button>
								<span v-if="!hasAuth('jenkinsJob:Build') && !hasAuth('jenkinsJob:Console')" class="op-empty">无操作权限</span>
							</template>
							<span v-else class="op-empty">-</span>
						</template>
					</el-table-column>
				</el-table>
			</el-card>

			<!-- 触发构建：参数填写弹窗（像 Jenkins 那样勾选/填写，不用手写 JSON） -->
			<BuildParamDialog
				v-model="buildDialogVisible"
				:server-id="serverId ?? 0"
				:job="buildJob"
				:submitting="building"
				:preload-error="buildProbeError"
				@confirm="onBuildConfirm"
			/>

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
				<pre class="log-body" ref="logBodyRef">{{ logText }}</pre>
			</el-dialog>
		</div>
	</fs-page>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { BtnPermissionStore } from '/@/stores/btnPermission';
import { GetServers, GetJobs, Build, GetJobParams, GetJobStatus, GetConsole } from './api';
import BuildParamDialog from './BuildParamDialog.vue';

export default defineComponent({
	name: "jenkinsJob",
	components: { BuildParamDialog },
	setup() {
		// 按钮级权限：与后端 menu_button_all_permission 同源
		const btnStore = BtnPermissionStore();
		const hasAuth = (code: string) => (btnStore.data || []).includes(code);

		const servers = ref<any[]>([]);
		const serverId = ref<number | null>(null);
		const jobs = ref<any[]>([]);      // 后端返回的扁平列表（用于计数）
		const jobTree = ref<any[]>([]);   // 树形结构（用于表格渲染，folder 可展开/收起）
		const jobLoading = ref(false);
		// 后端返回 restricted（该角色是否被目录授权限制）+ allowed_paths（可见前缀）
		const restricted = ref(false);
		const allowedPaths = ref<string[] | null>(null);

		const emptyText = computed(() => {
			if (!serverId.value) return '请先选择 Jenkins 服务器';
			if (jobLoading.value) return '';
			if (!jobTree.value.length && restricted.value) {
				if (allowedPaths.value && allowedPaths.value.length) {
					return `当前账号只被授权了这些目录：${allowedPaths.value.join('、')}，该服务器下没有可见的 Job`;
				}
				return '当前账号还没有被授权任何发布目录，请联系运维开通';
			}
			return '该服务器下没有 Job';
		});

		// 把后端深度优先的扁平列表重建为嵌套树（父子相邻、depth 决定层级）
		const buildTree = (rows: any[]) => {
			const root: any[] = [];
			const stack: any[] = [];
			rows.forEach((r: any) => {
				const node: any = { ...r };
				if (r.is_folder) node.children = [];
				while (stack.length && stack[stack.length - 1].depth >= r.depth) stack.pop();
				if (!stack.length) root.push(node);
				else stack[stack.length - 1].children.push(node);
				stack.push(node);
			});
			// 空 folder 去掉 children，避免出现无效展开箭头
			const prune = (nodes: any[]) => {
				nodes.forEach((n) => {
					if (n.children && !n.children.length) delete n.children;
					else if (n.children) prune(n.children);
				});
			};
			prune(root);
			return root;
		};

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

		const loadJobs = async (refresh = false) => {
			if (!serverId.value) { ElMessage.warning('请先选择 Jenkins 服务器'); return; }
			jobLoading.value = true;
			try {
				const res: any = await GetJobs(serverId.value, refresh);
				if (res.code === 2000) {
					jobs.value = res.data?.jobs || [];
					jobTree.value = buildTree(jobs.value);
					restricted.value = !!res.data?.restricted;
					allowedPaths.value = res.data?.allowed_paths ?? null;
				} else {
					ElMessage.error(res.msg || '获取 Job 列表失败');
					jobs.value = [];
					jobTree.value = [];
				}
			} catch (e: any) {
				// axios 超时/网络错误走这里（不是业务码分支）
				const msg = String(e?.message || '');
				ElMessage.error(
					msg.includes('timeout') ? '读取 Jenkins 超时，Jenkins 可能较慢或网络抖动，请点「刷新 Job 列表」重试' : msg || '获取 Job 列表失败'
				);
				jobs.value = [];
				jobTree.value = [];
			} finally {
				jobLoading.value = false;
			}
		};

		// ── 触发构建 ────────────────────────────────────────────────────────────
		// 流程：点「触发构建」→ 先探一次该 Job 的参数定义
		//   · 有参数 → 打开动态表单弹窗（下拉/多选/勾选，和 Jenkins 一致）
		//   · 无参数 → 直接触发，不给用户多一个空弹窗
		//   · 探测失败 → 仍然打开弹窗，但直接进高级模式（JSON 兜底），不阻塞发版
		// 探测走的是后端 job_params 接口，结果按 (服务器, Job) 缓存 10 分钟，
		// 所以第二次点同一个 Job 是毫秒级返回。
		const buildDialogVisible = ref(false);
		const buildJob = ref('');
		const building = ref(false);      // 弹窗里「触发构建」按钮的 loading
		const probingJob = ref('');       // 正在探测参数的那个 Job（控制行内按钮 loading）
		const buildProbeError = ref('');  // 探测失败的提示，原样透传给弹窗

		/** 真正发构建请求；成功返回 true（由调用方决定是关弹窗还是继续） */
		const doBuild = async (job: string, parameters: any) => {
			if (!serverId.value) return false;
			building.value = true;
			try {
				const res: any = await Build(serverId.value, job, parameters || {});
				if (res.code === 2000) {
					ElMessage.success(res.msg || '已触发构建');
					buildDialogVisible.value = false;
					// 触发后自动打开日志，能立刻看到排队/执行情况
					openLog(job);
					return true;
				}
				ElMessage.error(res.msg || '触发构建失败');
				return false;
			} catch (e: any) {
				ElMessage.error(e?.message || '触发构建异常');
				return false;
			} finally {
				building.value = false;
			}
		};

		const onBuild = async (row: any) => {
			if (!serverId.value) return;
			if (!hasAuth('jenkinsJob:Build')) { ElMessage.warning('无权限触发构建，请联系管理员开通'); return; }
			buildJob.value = row.full_path;
			buildProbeError.value = '';
			probingJob.value = row.full_path;
			let hasParams = false;
			try {
				const res: any = await GetJobParams(serverId.value, row.full_path);
				if (res.code === 2000) {
					hasParams = !!res.data?.has_params;
				} else {
					buildProbeError.value = res.msg || '读取参数定义失败';
				}
			} catch (e: any) {
				const msg = String(e?.message || '');
				buildProbeError.value = msg.includes('timeout')
					? '读取参数定义超时（Jenkins 响应较慢），可点「刷新 Job 列表」后重试'
					: msg || '读取参数定义失败';
			} finally {
				probingJob.value = '';
			}
			// 有参数 → 弹表单；探测失败 → 弹 JSON 兜底；两者都没有才真正"无参数"
			if (hasParams || buildProbeError.value) { buildDialogVisible.value = true; return; }
			await doBuild(row.full_path, {});
		};

		/** 弹窗点「触发构建」→ 拿表单拼好的参数去构建 */
		const onBuildConfirm = async (payload: any) => {
			if (!serverId.value || !buildJob.value) return;
			await doBuild(buildJob.value, payload);
		};

		const onViewLog = (row: any) => {
			if (!hasAuth('jenkinsJob:Console')) { ElMessage.warning('无权限查看构建日志，请联系管理员开通'); return; }
			openLog(row.full_path);
		};

		const openLog = (jobName: string) => {
			stopLogPolling();
			logStart.value = 0;
			logBuildNumber.value = 'lastBuild';
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
			servers, serverId, jobs, jobTree, jobLoading, emptyText, restricted, allowedPaths,
			hasAuth,
			buildDialogVisible, buildJob, building, probingJob, buildProbeError,
			logDialogVisible, logJob, logText, logLoading, logBuilding, logLoaded, logResult,
			autoScroll, logBodyRef,
			colorInfo, onServerChange, loadJobs, onBuild, onBuildConfirm, onViewLog, loadLog,
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
.job-count.restricted {
	color: #e6a23c;
}
.folder-name {
	color: #606266;
	font-weight: 500;
}
.path-text {
	color: #909399;
	font-size: 12px;
}
.op-empty {
	color: #c0c4cc;
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
