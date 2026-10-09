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
  /* ★ top 必须让操作栏与「搜索行自带的按钮（查询/重置）」站在同一条水平线上。
     F12 实测（2026-10-09，告警规则页，视口宽 ~1918）：
       查询 / 重置              y = 113.0  h = 32
       添加 / 同步 Prom / 同步规则  y = 107.0  h = 32   ← 原 top:10px 的结果，高了 6px
     即：搜索按钮在行内「垂直居中」，距 .fs-crud 顶部 16px；而 top:10px 对齐的是行「顶部」。
     ⇒ 改成 16px，两组 y 都是 113，水平线一致。 */
  top: 16px;
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
  /* ★ 这个 padding-right 是给「悬浮操作栏」让位用的（操作栏是 position:absolute + right:20px）。
     所以它必须 ≥ 操作栏实际宽度 + 20px，否则操作栏会盖住搜索行自带的「查询 / 重置」。

     本页的操作栏有 3 个按钮，比其它页宽：
       添加(≈58) + 同步 Prom(≈92) + 同步规则(≈86) + 2×6 gap(≈12) ≈ 248px，再 + right:20 ≈ 268px
     而其它页只有 1~2 个短按钮（≤180px），所以用默认的 200px 就够 —— 本页不够，
     表现为「重置」被压成「重」、按钮叠在一起。

     ★ 以后再往本页 actionbar 加按钮，记得同步加大这个值（用浏览器 F12 量一下新宽度）。 */
  padding-right: 320px;
}
</style>
