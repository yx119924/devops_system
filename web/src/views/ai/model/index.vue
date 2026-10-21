<template>
	<fs-page>
		<el-tabs v-model="activeTab" class="ai-model-tabs" @tab-change="handleTabChange">
			<!-- ===== Tab 1: 大模型供应商 ===== -->
			<el-tab-pane name="provider">
				<template #label><span class="tab-label">我的模型配置</span></template>
				<div class="tab-tip">
					这里录入<b>你自己的</b>大模型接口 —— 配置<b>只对你自己可见</b>，别人看不到也用不到；谁提问就消耗谁的 Key（BYOK）。
					API Key 只写不读，保存后不再回显。保存后点「测试连接」可立即验证 Key 是否可用。
				</div>
				<fs-crud ref="crudRef" v-bind="crudBinding" />
			</el-tab-pane>

			<!-- ===== Tab 2: 安全护栏（仅管理员：能改白名单 = 能决定 AI 跑什么命令） ===== -->
			<el-tab-pane v-if="canGuard" name="guard">
				<template #label><span class="tab-label">安全护栏</span></template>
				<guard-panel />
			</el-tab-pane>
		</el-tabs>
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent, ref, computed } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/stores/btnPermission';
import { createCrudOptions } from './crud';
import guardPanel from './guard.vue';

export default defineComponent({
	name: 'aiModel',
	components: { guardPanel },
	setup() {
		const instance = getCurrentInstance();
		const context: any = {
			componentName: instance?.type.name,
		};
		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const activeTab = ref('provider');

		/**
		 * 「安全护栏」页签的可见性。
		 *
		 * ★ 只看 `ai_guard:Update`，不看 is_superuser：护栏是**全局**配置（白名单决定 AI
		 *   能跑什么命令），只有被授了这个权限码的角色才该看见 —— 否则会出现"页签露出来、
		 *   点保存报 4000"的体验，比直接不显示更让人困惑。
		 *   与后端 `CustomPermission` 判定的是同一份数据（RoleMenuButtonPermission），
		 *   所以前端藏了就是真没权限，不是"藏起来但接口能调"。
		 */
		const btnStore = BtnPermissionStore();
		const canGuard = computed(() => (btnStore.data || []).includes('ai_guard:Update'));

		// 切回供应商页签时刷新一次：fs-crud 的表格在隐藏容器里待过，回来重取数据最稳
		const handleTabChange = (name: any) => {
			if (name === 'provider') {
				crudExpose.doRefresh();
			}
		};

		onMounted(() => {
			crudExpose.doRefresh();
		});

		return { crudBinding, crudRef, activeTab, handleTabChange, canGuard };
	},
});
</script>

<style scoped>
.ai-model-tabs :deep(.el-tabs__header) {
	margin-bottom: 12px;
}
/* ★ 2026-10-21 这里**不要**用 CSS 修表格高度，踩过两次：
 *   ① fast-crud 的 FsPage 结构是 .fs-page > [.fs-page-header] + .fs-page-content + [.fs-page-footer]，
 *      而 .fs-page-content 是 `flex:1; overflow:auto` 的 **block** ⇒ 给里面的 el-tabs 写 flex:1
 *      拿不到任何剩余高度（父级没开 flex 分配），改了等于没改。
 *   ② 改成 height:100% 能拿到高度，但 .fs-container{height:100%} 会撑满整个 content，
 *      而它的 .inner 是相对 .box 绝对定位的 ⇒ 表格会直接盖住上面那条 .tab-tip 提示语，比现状更糟。
 *   正解在 crud.tsx 的 container.fixedHeight = false：让表格按数据行数自己撑开，
 *   不再依赖任何祖先高度，表格与提示语保持正常流关系。 */
.tab-label {
	display: inline-flex;
	align-items: center;
}
.tab-tip {
	font-size: 12px;
	color: #606266;
	background: #f5f7fa;
	border-radius: 6px;
	padding: 8px 12px;
	margin-bottom: 12px;
	line-height: 1.7;
}
/* 悬浮操作栏：与告警/告警渠道页保持一致 */
:deep(.fs-crud) {
	position: relative;
}
:deep(.fs-crud-actionbar) {
	position: absolute;
	top: 16px /* 与搜索行自带按钮对齐：它们距 .fs-crud 顶部 16px（行内垂直居中）；原 10px 会高 6px */;
	right: 0;
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
