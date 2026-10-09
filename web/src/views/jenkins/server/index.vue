<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />
		<rolePerm v-model="grantVisible" :server="grantServer" />
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import rolePerm from './rolePerm/index.vue';

export default defineComponent({
	name: "jenkinsServer",
	components: { rolePerm },
	setup() {
		const instance = getCurrentInstance();
		const grantVisible = ref(false);
		const grantServer = ref<any>(null);
		const context: any = {
			componentName: instance?.type.name,
			openGrant: (row: any) => {
				grantServer.value = row;
				grantVisible.value = true;
			},
		};
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });
		onMounted(() => {
			crudExpose.doRefresh();
		});
		return { crudBinding, crudRef, grantVisible, grantServer };
	}
});
</script>

<style scoped>
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
