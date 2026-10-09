<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding">
			<template #actionbar-right v-if="canImport">
				<importExcel api="api/cmdb/server/">批量导入</importExcel>
			</template>
		</fs-crud>
		<webSsh v-model="sshVisible" :server="sshServer" />
		<serverGrant v-model="grantVisible" :server="grantServer" @saved="onGrantSaved" />
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/stores/btnPermission';
import { createCrudOptions } from './crud';
import importExcel from '/@/components/importExcel/index.vue';
import webSsh from './webSsh/index.vue';
import serverGrant from './serverGrant/index.vue';

export default defineComponent({
	name: "cmdbServer",
	components: { importExcel, webSsh, serverGrant },
	setup() {
		const instance = getCurrentInstance();
		// 批量导入按钮与后端 /import_data/ 的 server:Create 权限对齐，无权限时不显示
		const btnStore = BtnPermissionStore();
		const canImport = (btnStore.data || []).includes('server:Create');

		const sshVisible = ref(false);
		const sshServer = ref<any>(null);
		const grantVisible = ref(false);
		const grantServer = ref<any>(null);

		const context: any = {
			componentName: instance?.type.name,
			openSsh: (row: any) => {
				sshServer.value = row;
				sshVisible.value = true;
			},
			openGrant: (row: any) => {
				grantServer.value = row;
				grantVisible.value = true;
			},
		};
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });
		onMounted(() => {
			crudExpose.doRefresh();
		});
		// 授权变更后刷新列表，让「授权范围」列立刻反映最新状态
		const onGrantSaved = () => {
			crudExpose.doRefresh();
		};
		return { crudBinding, crudRef, sshVisible, sshServer, grantVisible, grantServer, canImport, onGrantSaved };
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
