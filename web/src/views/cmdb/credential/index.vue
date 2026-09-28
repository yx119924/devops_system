<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';

export default defineComponent({
	name: "bastionCredential",
	setup() {
		const instance = getCurrentInstance();
		const context: any = {
			componentName: instance?.type.name
		};
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });
		onMounted(() => {
			crudExpose.doRefresh();
		});
		return { crudBinding, crudRef };
	}
});
</script>

<style scoped>
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
