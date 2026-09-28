import { ref, reactive } from 'vue';
import * as api from './api';

/**
 * 命令下发详情弹窗的全局 store
 * - crud.tsx（执行/查看按钮 click）通过 detailStore.open(id) 触发
 * - index.vue 监听 detailStore.visible 显示 el-dialog
 * - 不上 pinia，避免新增依赖
 */
export const detailStore = reactive({
	visible: false as boolean,
	loading: false as boolean,
	data: {} as any, // { id, name, command, status, credential_name, started_at, finished_at, items: [...] }

	async open(id: number) {
		this.visible = true;
		this.loading = true;
		this.data = {};
		try {
			const [d, items] = await Promise.all([
				api.GetObj(id),
				api.GetItems(id),
			]);
			const meta = d.data?.data ?? d.data ?? {};
			const list = items.data?.data ?? items.data ?? [];
			this.data = { ...meta, items: list };
		} catch (e: any) {
			console.error('[dispatch detail] 拉取详情失败', e);
		} finally {
			this.loading = false;
		}
	},

	close() {
		this.visible = false;
		this.data = {};
	},

	refresh() {
		const id = this.data?.id;
		if (id) this.open(id);
	},
});
