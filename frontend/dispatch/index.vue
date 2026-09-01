<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />

		<!-- 执行结果详情弹窗 -->
		<el-dialog
			v-model="detailStore.visible"
			:title="`下发结果 - ${detailStore.data?.name || ''}`"
			width="960px"
			top="5vh"
			:close-on-click-modal="false"
			destroy-on-close
			@close="detailStore.close()"
		>
			<div v-loading="detailStore.loading" class="dispatch-detail">
				<!-- 任务元数据 -->
				<el-descriptions
					v-if="detailStore.data?.id"
					:column="3"
					border
					size="default"
					class="meta-desc"
				>
					<el-descriptions-item label="任务ID">#{{ detailStore.data.id }}</el-descriptions-item>
					<el-descriptions-item label="状态">
						<el-tag :type="statusTagType(detailStore.data.status)" effect="dark" size="small">
							{{ statusLabel(detailStore.data.status) }}
						</el-tag>
					</el-descriptions-item>
					<el-descriptions-item label="凭据">{{ detailStore.data.credential_name || '-' }}</el-descriptions-item>
					<el-descriptions-item label="执行命令" :span="3">
						<code class="cmd-text">{{ detailStore.data.command }}</code>
					</el-descriptions-item>
					<el-descriptions-item label="开始时间">{{ detailStore.data.started_at || '-' }}</el-descriptions-item>
					<el-descriptions-item label="完成时间">{{ detailStore.data.finished_at || '-' }}</el-descriptions-item>
					<el-descriptions-item label="目标/成功/失败">
						{{ detailStore.data.total }} / {{ detailStore.data.success_count }} / {{ detailStore.data.failed_count }}
					</el-descriptions-item>
				</el-descriptions>

				<!-- 目标结果列表 -->
				<h4 class="items-title">
					目标执行结果（{{ detailStore.data?.items?.length || 0 }} 台）
				</h4>
				<el-empty
					v-if="!detailStore.loading && !(detailStore.data?.items?.length)"
					description="暂无目标结果"
				/>

				<div
					v-for="(item, idx) in detailStore.data?.items || []"
					:key="item.id"
					class="result-item"
				>
					<div class="result-header">
						<span class="ip-label">
							#{{ idx + 1 }}
							<strong>{{ item.label }}</strong>
							<span class="ip-mono">({{ item.ip }}:{{ item.ssh_port }})</span>
						</span>
						<el-tag :type="statusTagType(item.status)" size="small" effect="dark">
							{{ statusLabel(item.status) }}
						</el-tag>
						<span v-if="item.duration != null" class="meta-text">
							耗时 <b>{{ Number(item.duration).toFixed(2) }}</b>s · exit <b>{{ item.exit_code }}</b>
						</span>
					</div>

					<pre v-if="item.stdout" class="stdout-block">{{ item.stdout }}</pre>
					<pre v-if="item.stderr" class="stderr-block">STDERR: {{ item.stderr }}</pre>
					<el-alert
						v-if="item.error"
						:title="item.error"
						type="error"
						:closable="false"
						show-icon
					/>
				</div>
			</div>

			<template #footer>
				<el-button @click="detailStore.close()">关闭</el-button>
				<el-button type="primary" :loading="detailStore.loading" @click="detailStore.refresh()">
					刷新
				</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { detailStore } from './detailStore';

// 状态 → 标签映射
const STATUS_MAP: Record<string, { label: string; type: string }> = {
	pending: { label: '待执行', type: 'info' },
	running: { label: '执行中', type: 'primary' },
	success: { label: '成功', type: 'success' },
	partial: { label: '部分失败', type: 'warning' },
	failed: { label: '失败', type: 'danger' },
	timeout: { label: '超时', type: 'warning' },
};

export default defineComponent({
	name: 'bastionCommandDispatch',
	setup() {
		const instance = getCurrentInstance();
		const context: any = { componentName: instance?.type.name };
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const statusLabel = (s: string) => STATUS_MAP[s]?.label || s || '-';
		const statusTagType = (s: string) => STATUS_MAP[s]?.type || 'info';

		onMounted(() => {
			crudExpose.doRefresh();
		});
		return { crudBinding, crudRef, detailStore, statusLabel, statusTagType };
	},
});
</script>

<style scoped>
.dispatch-detail {
	padding: 0 8px;
}
.meta-desc :deep(.el-descriptions__label) {
	width: 90px;
	color: #606266;
}
.cmd-text {
	background: #f5f7fa;
	padding: 2px 6px;
	border-radius: 3px;
	font-family: Consolas, 'Courier New', monospace;
	font-size: 13px;
	word-break: break-all;
}
.items-title {
	margin: 20px 0 12px 0;
	font-size: 15px;
	font-weight: 600;
	color: #303133;
}
.result-item {
	border: 1px solid #ebeef5;
	border-radius: 6px;
	margin-bottom: 12px;
	padding: 12px 14px;
	background: #fafbfc;
}
.result-item:hover {
	border-color: #409eff;
}
.result-header {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 8px;
	flex-wrap: wrap;
}
.ip-label {
	flex: 1;
	min-width: 200px;
}
.ip-label strong {
	margin: 0 4px;
	color: #303133;
}
.ip-mono {
	color: #909399;
	font-family: Consolas, 'Courier New', monospace;
	font-size: 12px;
}
.meta-text {
	color: #606266;
	font-size: 13px;
}
.stdout-block,
.stderr-block {
	margin: 6px 0 0 0;
	padding: 10px 12px;
	border-radius: 4px;
	font-family: Consolas, 'Courier New', monospace;
	font-size: 12.5px;
	line-height: 1.6;
	white-space: pre-wrap;
	word-break: break-all;
	max-height: 320px;
	overflow-y: auto;
}
.stdout-block {
	background: #1e1e1e;
	color: #d4d4d4;
}
.stderr-block {
	background: #fff7e6;
	color: #874d00;
	border: 1px solid #ffd591;
}

/* 方案 A 布局：actionbar 浮动到搜索栏右侧 */
:deep(.fs-crud) {
	position: relative;
}
:deep(.fs-crud-actionbar) {
	position: absolute;
	top: 10px;
	right: 20px;
	z-index: 10;
	margin: 0;
	display: flex;
	justify-content: flex-end;
}
:deep(.fs-actionbar-buttons) {
	gap: 6px;
	flex-wrap: nowrap;
}
:deep(.fs-crud-search),
:deep(.fs-search-column) {
	padding-right: 200px;
}
</style>
