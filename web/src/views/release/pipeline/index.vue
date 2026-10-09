<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />

		<!-- 编排：顺序列表 + 右侧配置面板（不做自由拖拽） -->
		<Designer
			v-model="designerStore.visible"
			:pipeline="designerStore.pipeline"
			@saved="onSaved"
		/>

		<!-- 发起执行：填运行时参数 -->
		<RunDialog
			v-model="runStartStore.visible"
			:pipeline="runStartStore.pipeline"
			@started="onStarted"
		/>

		<!-- 执行详情：推进 / 中止 / 重跑（与「执行记录」页共用同一个组件） -->
		<RunPanel v-model="runPanelStore.visible" :run-id="runPanelStore.runId" />
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import Designer from './Designer.vue';
import RunDialog from './RunDialog.vue';
import RunPanel from '../run/RunPanel.vue';
import { designerStore, runStartStore, runPanelStore, openRunPanel } from './panelStore';

export default defineComponent({
	name: 'releasePipeline',
	components: { Designer, RunDialog, RunPanel },
	setup() {
		const instance = getCurrentInstance();
		const context: any = { componentName: instance?.type.name };
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const onSaved = () => crudExpose.doRefresh();

		/** 发起执行成功后，直接打开执行详情把这条流水线推下去 */
		const onStarted = (runId: number) => {
			crudExpose.doRefresh();
			if (runId) openRunPanel(runId);
		};

		onMounted(() => {
			crudExpose.doRefresh();
		});

		return { crudBinding, crudRef, designerStore, runStartStore, runPanelStore, onSaved, onStarted };
	},
});
</script>

<style scoped>
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
