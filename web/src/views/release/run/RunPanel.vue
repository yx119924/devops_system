<template>
	<el-drawer
		v-model="show"
		:title="`执行详情 · ${detail?.pipeline_name || ''} #${runId || ''}`"
		size="70%"
		:close-on-click-modal="false"
		destroy-on-close
		@open="reload"
	>
		<div v-loading="loading">
			<!-- 概览 -->
			<div class="head">
				<el-tag :type="statusType(detail?.status)" effect="dark" size="large">
					{{ detail?.status_label || detail?.status || '-' }}
				</el-tag>
				<span class="meta">进度 {{ detail?.done_nodes ?? 0 }} / {{ detail?.total_nodes ?? 0 }} 节点</span>
				<span v-if="detail?.failed_nodes" class="meta danger">失败 {{ detail.failed_nodes }} 个</span>
				<span class="meta">发起人 {{ detail?.creator_name || '-' }}</span>
				<span class="meta">{{ detail?.trigger_type_label || '-' }}</span>
				<span class="meta">{{ detail?.started_at || '-' }} → {{ detail?.finished_at || '进行中' }}</span>
			</div>

			<el-alert v-if="detail?.last_error" type="error" :closable="false" show-icon :title="detail.last_error" class="mb12" />

			<div v-if="Object.keys(detail?.params || {}).length" class="params">
				<strong>本次参数：</strong>
				<el-tag v-for="(v, k) in detail.params" :key="k" size="small" class="param-tag">{{ k }} = {{ v }}</el-tag>
			</div>

			<!-- 操作 -->
			<div class="ops">
				<el-button
					v-if="hasAuth('pipelineRun:Advance') && !detail?.is_final"
					type="primary"
					:loading="stepping"
					:disabled="autoRunning"
					@click="step"
				>
					推进一步
				</el-button>
				<el-button
					v-if="hasAuth('pipelineRun:Advance') && !detail?.is_final"
					type="success"
					:loading="autoRunning"
					:disabled="stepping"
					@click="autoRun"
				>
					自动跑完
				</el-button>
				<el-button
					v-if="hasAuth('pipelineRun:Retry') && canRetry"
					type="warning"
					@click="retry"
				>
					重跑失败节点
				</el-button>
				<el-button
					v-if="hasAuth('pipelineRun:Abort') && !detail?.is_final"
					type="danger"
					plain
					@click="abort"
				>
					中止
				</el-button>
				<el-button @click="reload">刷新</el-button>
				<span class="hint-inline">
					★ 执行由本页面驱动：关掉浏览器/刷新页面，流水线会停在当前节点（这是"先前端驱动"方案的已知边界）。
				</span>
			</div>

			<!-- 节点时间线 -->
			<div class="timeline">
				<div v-for="(n, i) in detail?.nodes || []" :key="n.id" class="tl-row">
					<div class="tl-left">
						<div class="tl-dot" :class="`dot-${n.status}`">
							<el-icon v-if="n.status === 'success'"><Check /></el-icon>
							<el-icon v-else-if="n.status === 'failed'"><Close /></el-icon>
							<el-icon v-else-if="n.status === 'running'" class="is-loading"><Loading /></el-icon>
							<span v-else>{{ n.seq + 1 }}</span>
						</div>
						<div v-if="i < (detail?.nodes || []).length - 1" class="tl-line" />
					</div>
					<div class="tl-body">
						<div class="tl-head">
							<span class="tl-name">{{ n.name || '未命名节点' }}</span>
							<el-tag size="small" effect="plain">{{ n.node_type_label }}</el-tag>
							<el-tag size="small" :type="nodeStatusType(n.status)">{{ n.status_label }}</el-tag>
							<span v-if="n.on_failure === 'continue'" class="tag-warn">失败继续</span>
							<span v-if="n.duration != null" class="tag-dim">{{ n.duration }}s</span>
						</div>
						<div v-if="n.message" class="tl-msg" :class="{ 'msg-fail': n.status === 'failed' }">{{ n.message }}</div>
						<div v-if="hasResults(n)" class="tl-results">
							<el-collapse>
								<el-collapse-item :title="`逐台结果（${resultCount(n)} 条）`" :name="n.id">
									<el-table :data="n.targets_result || []" size="small" border>
										<el-table-column prop="label" label="目标" width="150" />
										<el-table-column prop="ip" label="地址" width="150" />
										<el-table-column label="结果" width="80" align="center">
											<template #default="{ row }">
												<el-tag size="small" :type="row.ok ? 'success' : 'danger'">{{ row.ok ? '成功' : '失败' }}</el-tag>
											</template>
										</el-table-column>
										<el-table-column prop="exit_code" label="退出码" width="80" />
										<el-table-column label="输出" min-width="240">
											<template #default="{ row }">
												<div class="mono">{{ (row.stdout || row.error || '').slice(0, 600) || '-' }}</div>
											</template>
										</el-table-column>
									</el-table>
								</el-collapse-item>
							</el-collapse>
						</div>
					</div>
				</div>
				<el-empty v-if="!(detail?.nodes || []).length" description="暂无节点" :image-size="70" />
			</div>
		</div>
	</el-drawer>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Check, Close, Loading } from '@element-plus/icons-vue';
import { BtnPermissionStore } from '/@/stores/btnPermission';
import * as api from './api';

export default defineComponent({
	name: 'ReleaseRunPanel',
	props: {
		modelValue: { type: Boolean, default: false },
		runId: { type: Number, default: null },
	},
	emits: ['update:modelValue', 'refresh'],
	setup(props, { emit }) {
		const show = computed({
			get: () => props.modelValue,
			set: (v: boolean) => emit('update:modelValue', v),
		});

		const loading = ref(false);
		const stepping = ref(false);
		const autoRunning = ref(false);
		const detail = ref<any>({});

		const btnStore = BtnPermissionStore();
		const hasAuth = (code: string) => (btnStore.data || []).includes(code);

		const canRetry = computed(() =>
			['failed', 'partial', 'aborted'].includes(detail.value?.status)
			&& (detail.value?.failed_nodes || 0) > 0);

		function statusType(status?: string) {
			return ({
				success: 'success', partial: 'warning', failed: 'danger',
				aborted: 'info', running: 'primary', pending: 'info',
			} as any)[status || ''] || 'info';
		}

		function nodeStatusType(status?: string) {
			return ({ success: 'success', failed: 'danger', running: 'primary', pending: 'info' } as any)[status || ''] || 'info';
		}

		function hasResults(node: any) {
			return node.status === 'success' || node.status === 'failed';
		}

		function resultCount(node: any) {
			// 详情接口会带 targets_result；advance 的返回只给条数（避免循环调用时响应过大）
			return node.result_count ?? (node.targets_result || []).length;
		}

		async function reload() {
			if (!props.runId) return;
			loading.value = true;
			try {
				const resp: any = await api.GetObj(props.runId);
				detail.value = resp?.data?.data || resp?.data || {};
			} finally {
				loading.value = false;
			}
		}

		async function step() {
			if (!props.runId) return;
			stepping.value = true;
			try {
				const resp: any = await api.Advance(props.runId);
				detail.value = resp?.data?.data || resp?.data || detail.value;
				emit('refresh');
			} finally {
				stepping.value = false;
			}
		}

		/**
		 * 自动跑完：循环调 advance，直到 run 进入终态。
		 *
		 * ★ 三道保护：
		 *   ① 最多 500 次迭代（节点上限 100，正常远用不到），避免任何情况下死循环；
		 *   ② 连续两轮 `done_nodes` 没变就停 —— 说明推进不动了
		 *      （另一个页面在跑 / 已无待执行节点），继续循环只会白刷请求；
		 *   ③ 任何一次请求抛错都直接退出循环（拦截器已经提示过原因），
		 *      不然会把一个报错重复弹 500 次。
		 */
		async function autoRun() {
			if (!props.runId || autoRunning.value) return;
			autoRunning.value = true;
			try {
				let lastDone = detail.value?.done_nodes ?? -1;
				let stall = 0;
				for (let i = 0; i < 500; i++) {
					const resp: any = await api.Advance(props.runId);
					const d = resp?.data?.data || resp?.data;
					if (d) detail.value = d;
					if (d?.is_final) {
						// 终态后用详情接口补一次完整结果（含逐台 stdout）
						await reload();
						ElMessage.success(`执行结束：${d.status_label || d.status}`);
						break;
					}
					const done = d?.done_nodes ?? 0;
					if (done === lastDone) {
						stall += 1;
					} else {
						stall = 0;
						lastDone = done;
					}
					if (stall >= 2) {
						ElMessage.warning('连续两轮没有推进，可能是另一个页面正在执行或已无待执行节点，已停止自动推进');
						break;
					}
				}
			} catch (e) {
				// 拦截器已提示；这里只负责停止循环
			} finally {
				autoRunning.value = false;
				emit('refresh');
			}
		}

		async function abort() {
			try {
				await ElMessageBox.confirm(
					'中止后未执行的节点会保持「待执行」，本次执行标记为「已中止」。确认中止？',
					'中止执行', { type: 'warning', confirmButtonText: '确认中止', cancelButtonText: '取消' });
			} catch (e) {
				return;
			}
			const resp: any = await api.Abort(props.runId!);
			detail.value = resp?.data?.data || detail.value;
			await reload();      // 重新拉详情，把逐台结果补齐（advance/abort 的返回不含输出）
			emit('refresh');
		}

		async function retry() {
			try {
				await ElMessageBox.confirm(
					'将把所有「失败」节点重置为「待执行」，成功的节点保留不动。确认重跑？',
					'重跑失败节点', { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' });
			} catch (e) {
				return;
			}
			const resp: any = await api.Retry(props.runId!);
			detail.value = resp?.data?.data || detail.value;
			await reload();
			ElMessage.success('已重置失败节点，点「自动跑完」继续');
			emit('refresh');
		}

		watch(() => props.runId, (v) => {
			if (v && props.modelValue) reload();
		});

		return {
			show, loading, stepping, autoRunning, detail, canRetry,
			hasAuth, statusType, nodeStatusType, hasResults, resultCount,
			reload, step, autoRun, abort, retry,
		};
	},
});
</script>

<style scoped>
.head {
	display: flex;
	align-items: center;
	gap: 14px;
	flex-wrap: wrap;
	margin-bottom: 12px;
}
.meta {
	color: #606266;
	font-size: 13px;
}
.meta.danger {
	color: #f56c6c;
}
.mb12 {
	margin-bottom: 12px;
}
.params {
	margin-bottom: 12px;
	font-size: 13px;
	color: #606266;
	display: flex;
	align-items: center;
	gap: 6px;
	flex-wrap: wrap;
}
.param-tag {
	font-family: Consolas, 'Courier New', monospace;
}
.ops {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
	padding: 10px 0 14px;
	border-bottom: 1px solid #ebeef5;
	margin-bottom: 14px;
}
.hint-inline {
	color: #909399;
	font-size: 12px;
	margin-left: 6px;
}
.timeline {
	padding-left: 4px;
}
.tl-row {
	display: flex;
	gap: 12px;
}
.tl-left {
	display: flex;
	flex-direction: column;
	align-items: center;
	width: 28px;
	flex: none;
}
.tl-dot {
	width: 24px;
	height: 24px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 12px;
	color: #fff;
	background: #c0c4cc;
	flex: none;
}
.dot-success {
	background: #67c23a;
}
.dot-failed {
	background: #f56c6c;
}
.dot-running {
	background: #409eff;
}
.dot-pending {
	background: #dcdfe6;
	color: #909399;
}
.tl-line {
	flex: 1;
	width: 2px;
	background: #ebeef5;
	margin: 2px 0;
	min-height: 18px;
}
.tl-body {
	flex: 1;
	padding-bottom: 16px;
	min-width: 0;
}
.tl-head {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}
.tl-name {
	font-weight: 600;
	color: #303133;
}
.tag-warn {
	color: #e6a23c;
	font-size: 12px;
}
.tag-dim {
	color: #909399;
	font-size: 12px;
}
.tl-msg {
	margin-top: 6px;
	color: #606266;
	font-size: 13px;
	line-height: 1.7;
}
.msg-fail {
	color: #f56c6c;
}
.tl-results {
	margin-top: 6px;
}
.mono {
	font-family: Consolas, 'Courier New', monospace;
	font-size: 12px;
	color: #606266;
	white-space: pre-wrap;
	word-break: break-all;
	max-height: 160px;
	overflow: auto;
}
</style>
