<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />

		<el-dialog
			v-model="panelStore.visible"
			:title="panelStore.title"
			width="920px"
			top="5vh"
			:close-on-click-modal="false"
			destroy-on-close
			@close="closePanel()"
		>
			<div v-loading="panelStore.loading" class="collect-detail">
				<el-alert
					v-if="panelStore.error"
					:title="panelStore.error"
					type="error"
					show-icon
					:closable="false"
					class="mb12"
				/>
				<div v-else-if="panelStore.summary" class="summary-bar">{{ panelStore.summary }}</div>

				<!-- ① 环境检测 / 下发·停止的逐台结果 -->
				<template v-if="panelStore.mode === 'detect'">
					<el-empty v-if="!panelStore.loading && !panelStore.results.length" description="暂无目标结果" />
					<div v-for="(r, i) in panelStore.results" :key="i" class="target-card">
						<div class="target-head">
							<span class="target-name">
								<strong>{{ r.server || r.ip }}</strong>
								<span class="mono">({{ r.ip }})</span>
							</span>
							<el-tag :type="r.ok ? 'success' : 'danger'" size="small" effect="dark">
								{{ r.ok ? '正常' : '异常' }}
							</el-tag>
						</div>

						<el-descriptions v-if="r.ok && r.installed !== undefined" :column="3" border size="small">
							<el-descriptions-item label="filebeat">
								{{ r.installed ? '已安装' : '未安装' }}
							</el-descriptions-item>
							<el-descriptions-item label="版本">{{ r.version || '-' }}</el-descriptions-item>
							<el-descriptions-item label="服务状态">
								<el-tag :type="r.active === 'active' ? 'success' : 'warning'" size="small">
									{{ r.active || 'unknown' }}
								</el-tag>
							</el-descriptions-item>
							<el-descriptions-item label="加载片段目录">
								<el-tag :type="r.loads_inputs_dir ? 'success' : 'danger'" size="small">
									{{ r.loads_inputs_dir ? '已配置' : '未配置' }}
								</el-tag>
							</el-descriptions-item>
							<el-descriptions-item label="热加载">{{ r.reload_enabled ? '开' : '关（下发需重启）' }}</el-descriptions-item>
							<el-descriptions-item label="input 类型">{{ r.beat_type || '-' }}</el-descriptions-item>
							<el-descriptions-item label="落库 ES" :span="2">{{ r.es_hosts || '(主配置未显式指定)' }}</el-descriptions-item>
							<el-descriptions-item label="落库索引">{{ r.es_index || '(默认)' }}</el-descriptions-item>
						</el-descriptions>

						<el-alert
							v-for="(w, wi) in r.warnings || []"
							:key="wi"
							:title="w"
							type="warning"
							:closable="false"
							show-icon
							class="warn-line"
						/>
						<el-alert
							v-if="!r.ok"
							:title="r.message || '未知错误'"
							type="error"
							:closable="false"
							show-icon
						/>
					</div>
				</template>

				<!-- ② 规则试跑 -->
				<template v-else-if="panelStore.mode === 'preview'">
					<template v-if="panelStore.preview">
						<el-descriptions :column="3" border size="small" class="mb12">
							<el-descriptions-item label="样本行数">{{ panelStore.preview.total ?? 0 }}</el-descriptions-item>
							<el-descriptions-item label="保留">
								<span class="keep-num">{{ panelStore.preview.kept_count ?? 0 }}</span>
							</el-descriptions-item>
							<el-descriptions-item label="被过滤">
								<span class="drop-num">{{ panelStore.preview.dropped_count ?? 0 }}</span>
							</el-descriptions-item>
						</el-descriptions>

						<el-tabs v-if="(panelStore.preview.total ?? 0) > 0">
							<el-tab-pane :label="`保留（${panelStore.preview.kept_count ?? 0}）`">
								<pre class="log-block keep">{{ (panelStore.preview.kept || []).join('\n') || '（无）' }}</pre>
							</el-tab-pane>
							<el-tab-pane :label="`被过滤（${panelStore.preview.dropped_count ?? 0}）`">
								<div v-for="(d, di) in panelStore.preview.dropped || []" :key="di" class="drop-row">
									<el-tag type="warning" size="small">{{ d.reason }}</el-tag>
									<span class="drop-line">{{ d.line }}</span>
								</div>
								<div v-if="!(panelStore.preview.dropped || []).length" class="mono">（无）</div>
							</el-tab-pane>
						</el-tabs>
						<el-alert
							v-else
							:title="panelStore.preview.message || '没有读到内容'"
							type="info"
							:closable="false"
							show-icon
						/>
						<div class="tip-line">
							★ 试跑按「只对第一台目标」抓最后 {{ panelStore.lines }} 行样本，用平台侧规则复现过滤；
							实际采集由 filebeat 流式执行，边界情况可能略有差异。
						</div>
					</template>
					<el-empty v-else description="暂无试跑结果" />
				</template>

				<!-- ③ 操作台账 -->
				<el-table
					v-else-if="panelStore.mode === 'records'"
					:data="panelStore.records"
					border
					size="small"
					max-height="520"
					empty-text="暂无操作记录"
				>
					<el-table-column label="时间" width="160">
						<template #default="{ row }">{{ row.create_datetime || '-' }}</template>
					</el-table-column>
					<el-table-column label="操作" width="100">
						<template #default="{ row }">{{ row.action_label || row.action }}</template>
					</el-table-column>
					<el-table-column label="结果" width="80" align="center">
						<template #default="{ row }">
							<el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
								{{ row.status_label || row.status }}
							</el-tag>
						</template>
					</el-table-column>
					<el-table-column label="目标" width="160" show-overflow-tooltip>
						<template #default="{ row }">{{ row.target_label || '-' }}<span v-if="row.ip"> / {{ row.ip }}</span></template>
					</el-table-column>
					<el-table-column label="摘要" min-width="240" show-overflow-tooltip>
						<template #default="{ row }">{{ row.message || '-' }}</template>
					</el-table-column>
					<el-table-column label="操作人" width="100">
						<template #default="{ row }">{{ row.creator_name || '-' }}</template>
					</el-table-column>
				</el-table>

				<!-- ④ 目标机主配置待补内容 -->
				<template v-else-if="panelStore.mode === 'patch'">
					<el-alert
						type="info"
						:closable="false"
						show-icon
						title="平台不会自动修改 filebeat 主配置"
						description="如果「检测」显示目标机未加载片段目录，需要把下面这段追加到目标机的 /etc/filebeat/filebeat.yml 末尾（先备份原文件），再重启 filebeat。重启用 systemctl restart filebeat。"
						class="mb12"
					/>
					<div class="mono small mb12">本次片段路径：{{ panelStore.remoteFile || '-' }}</div>
					<pre class="log-block">{{ panelStore.patch || '（暂无）' }}</pre>
					<el-button size="small" class="mt8" @click="copyPatch">复制这段配置</el-button>
				</template>
			</div>

			<template #footer>
				<el-button @click="closePanel()">关闭</el-button>
				<el-button
					v-if="panelStore.mode !== 'patch'"
					type="primary"
					:loading="panelStore.loading"
					@click="refreshPanel()"
				>
					刷新
				</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent } from 'vue';
import { ElMessage } from 'element-plus';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { panelStore, closePanel, refreshPanel } from './panelStore';

export default defineComponent({
	name: 'logCollect',
	setup() {
		const instance = getCurrentInstance();
		const context: any = { componentName: instance?.type.name };
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const copyPatch = async () => {
			try {
				await navigator.clipboard.writeText(panelStore.patch || '');
				ElMessage.success('已复制到剪贴板');
			} catch (e: any) {
				ElMessage.warning('复制失败，请手动选中复制');
			}
		};

		onMounted(() => {
			crudExpose.doRefresh();
		});

		return { crudBinding, crudRef, panelStore, closePanel, refreshPanel, copyPatch };
	},
});
</script>

<style scoped>
.collect-detail {
	padding: 0 4px;
}
.mb12 {
	margin-bottom: 12px;
}
.mt8 {
	margin-top: 8px;
}
.summary-bar {
	color: #606266;
	font-size: 13px;
	margin-bottom: 10px;
}
.target-card {
	border: 1px solid #ebeef5;
	border-radius: 6px;
	padding: 12px 14px;
	margin-bottom: 12px;
	background: #fafbfc;
}
.target-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8px;
}
.target-name strong {
	color: #303133;
	margin-right: 6px;
}
.mono {
	font-family: Consolas, 'Courier New', monospace;
	color: #909399;
	font-size: 12px;
}
.small {
	font-size: 12px;
}
.warn-line {
	margin-top: 6px;
}
.log-block {
	background: #1e1e1e;
	color: #d4d4d4;
	padding: 12px;
	border-radius: 4px;
	max-height: 420px;
	overflow: auto;
	font-size: 12.5px;
	line-height: 1.65;
	white-space: pre-wrap;
	word-break: break-all;
	margin: 0;
}
.log-block.keep {
	background: #f0f9eb;
	color: #2c3e50;
	border: 1px solid #c2e7b0;
}
.drop-row {
	display: flex;
	gap: 10px;
	align-items: flex-start;
	padding: 6px 0;
	border-bottom: 1px dashed #ebeef5;
}
.drop-line {
	font-family: Consolas, 'Courier New', monospace;
	font-size: 12.5px;
	color: #606266;
	word-break: break-all;
	flex: 1;
}
.keep-num {
	color: #67c23a;
	font-weight: 600;
}
.drop-num {
	color: #e6a23c;
	font-weight: 600;
}
.tip-line {
	margin-top: 10px;
	color: #909399;
	font-size: 12px;
	line-height: 1.7;
}

/* 方案 A 布局：actionbar 浮动到搜索栏右侧 */
:deep(.fs-crud) {
	position: relative;
}
:deep(.fs-crud-actionbar) {
	position: absolute;
	top: 16px /* 与搜索行自带按钮对齐：它们距 .fs-crud 顶部 16px（行内垂直居中）；原 10px 会高 6px */;
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
