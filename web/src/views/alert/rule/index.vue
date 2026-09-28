<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding">
			<template #actionbar-right>
				<el-button type="primary" :loading="reloadLoading" @click="doReload">同步规则</el-button>
			</template>
		</fs-crud>
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { ElMessage } from 'element-plus';
import { createCrudOptions } from './crud';
import * as api from './api';

export default defineComponent({
	name: "alertRule",
	setup() {
		const instance = getCurrentInstance();
		const reloadLoading = ref(false);
		const context: any = {
			componentName: instance?.type.name,
		};
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const doReload = async () => {
			reloadLoading.value = true;
			try {
				const res: any = await api.ReloadRules();
				if (res.code === 2000) {
					ElMessage.success('规则已同步并热加载');
				} else {
					ElMessage.error(res.msg || '同步失败');
				}
			} finally {
				reloadLoading.value = false;
			}
		};

		onMounted(() => {
			crudExpose.doRefresh();
		});
		return { crudBinding, crudRef, reloadLoading, doReload };
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
