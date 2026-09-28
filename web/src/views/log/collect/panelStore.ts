import { reactive } from 'vue';
import { ElMessage } from 'element-plus';
import * as api from './api';

/**
 * 详情面板状态：环境检测 / 规则试跑 / 操作台账 / 主配置补丁
 *
 * ★ 错误提示必须同时读 `e.msg` 和 `e.message`：
 *   axios 响应拦截器 reject 的是**后端返回的整个对象**（业务失败时只有 `msg`，
 *   没有 `message`）。只读 `e.message` 会恒为 undefined，
 *   于是"正则不兼容"这类明确的后端报错会被显示成"网络不通"——
 *   AI 助手那次就是栽在这个细节上。
 */
function errText(e: any): string {
	const msg = e?.msg || e?.message || e?.data?.msg;
	if (typeof msg === 'string' && msg) return msg;
	if (e?.response?.data?.msg) return String(e.response.data.msg);
	return String(e || '请求失败');
}

export const panelStore = reactive({
	visible: false,
	mode: 'detect', // detect | preview | records | patch
	title: '',
	row: null as any,
	loading: false,
	lines: 200,
	error: '',
	// 各模式的数据
	results: [] as any[],
	summary: '',
	preview: null as any,
	records: [] as any[],
	recordsTotal: 0,
	patch: '',
	remoteFile: '',
});

export function openPanel(mode: string, row: any) {
	panelStore.mode = mode;
	panelStore.row = row;
	panelStore.error = '';
	panelStore.visible = true;
	panelStore.title = {
		detect: `环境检测 - ${row?.name || ''}`,
		preview: `规则试跑 - ${row?.name || ''}`,
		records: `操作台账 - ${row?.name || ''}`,
		patch: `目标机主配置待补内容 - ${row?.name || ''}`,
	}[mode] || '详情';
	void refreshPanel();
}

export function closePanel() {
	panelStore.visible = false;
}

export async function refreshPanel() {
	const row = panelStore.row;
	if (!row?.id) return;
	panelStore.loading = true;
	panelStore.error = '';
	try {
		if (panelStore.mode === 'detect') {
			const res: any = await api.Detect(row.id);
			panelStore.results = res?.data?.results || [];
			panelStore.summary = res?.msg || '';
		} else if (panelStore.mode === 'preview') {
			const res: any = await api.Preview(row.id, panelStore.lines);
			panelStore.preview = res?.data || null;
			panelStore.summary = res?.msg || '';
		} else if (panelStore.mode === 'records') {
			const res: any = await api.GetRecords(row.id, 1, 50);
			panelStore.records = res?.data?.list || [];
			panelStore.recordsTotal = res?.data?.total || 0;
		} else if (panelStore.mode === 'patch') {
			const res: any = await api.GetMainPatch(row.id);
			panelStore.patch = res?.data?.content || '';
			panelStore.remoteFile = res?.data?.remote_file || '';
		}
	} catch (e: any) {
		panelStore.error = errText(e);
	} finally {
		panelStore.loading = false;
	}
}

/** 从列表页直接触发的一次动作（下发/停止），成功失败都给出明确提示 */
export async function runAction(kind: 'apply' | 'stop', row: any, refreshList: () => any) {
	try {
		const res: any = (kind === 'apply')
			? await api.ApplyCfg(row.id)
			: await api.StopCfg(row.id);
		const results = res?.data?.results || [];
		const failed = results.filter((r: any) => !r.ok);
		if (failed.length) {
			ElMessage.warning(`${res?.msg || '完成'}；首个失败：${failed[0]?.message || '未知原因'}`);
			// 失败时把逐台明细摊开给用户看，而不是只闪一句
			panelStore.row = row;
			panelStore.mode = 'detect';
			panelStore.title = `${kind === 'apply' ? '下发' : '停止'}结果 - ${row?.name || ''}`;
			panelStore.results = results;
			panelStore.summary = res?.msg || '';
			panelStore.visible = true;
		} else {
			ElMessage.success(res?.msg || '操作完成');
		}
		if (refreshList) await refreshList();
		return true;
	} catch (e: any) {
		ElMessage.error(errText(e));
		return false;
	}
}
