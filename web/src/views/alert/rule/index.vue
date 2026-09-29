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
				// 后端现在会回读 Prometheus 做校验，msg 里带真实结论（含「读不到」的具体原因），
				// 所以这里必须回显 res.msg —— 不能再写死「已同步并热加载」，那正是以前的假成功。
				if (res.code === 2000) {
					ElMessage({ type: 'success', message: res.msg || '规则已同步并热加载', duration: 8000, showClose: true });
				} else {
					ElMessage({ type: 'error', message: res.msg || '同步失败', duration: 10000, showClose: true });
				}
			} catch (e: any) {
				// 拦截器 reject 的是后端整个对象，错误信息在 e.msg 上
				ElMessage({ type: 'error', message: e?.msg || e?.message || '同步异常', duration: 10000, showClose: true });
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
