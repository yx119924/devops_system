<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />
		<RunPanel v-model="runPanelStore.visible" :run-id="runPanelStore.runId" @refresh="onRefresh" />
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import RunPanel from './RunPanel.vue';
import { runPanelStore } from '../pipeline/panelStore';

export default defineComponent({
	name: 'releaseRun',
	components: { RunPanel },
	setup() {
		const instance = getCurrentInstance();
		const context: any = { componentName: instance?.type.name };
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const onRefresh = () => crudExpose.doRefresh();

		onMounted(() => {
			crudExpose.doRefresh();
		});

		return { crudBinding, crudRef, runPanelStore, onRefresh };
	},
});
</script>

<style scoped>
/* 方案 A 布局：actionbar 浮动到搜索栏右侧（本页没有新增按钮，保持与其它页一致） */
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
