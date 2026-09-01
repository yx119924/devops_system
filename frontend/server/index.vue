<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding">
			<template #actionbar-right>
				<importExcel api="api/cmdb/server/">批量导入</importExcel>
			</template>
		</fs-crud>
		<webSsh v-model="sshVisible" :server="sshServer" />
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import importExcel from '/@/components/importExcel/index.vue';
import webSsh from './webSsh/index.vue';

export default defineComponent({
	name: "cmdbServer",
	components: { importExcel, webSsh },
	setup() {
		const instance = getCurrentInstance();
		const sshVisible = ref(false);
		const sshServer = ref<any>(null);
		const context: any = {
			componentName: instance?.type.name,
			openSsh: (row: any) => {
				sshServer.value = row;
				sshVisible.value = true;
			},
		};
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });
		onMounted(() => {
			crudExpose.doRefresh();
		});
		return { crudBinding, crudRef, sshVisible, sshServer };
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
