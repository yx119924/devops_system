import * as api from './api';
import { openRunPanel } from '../pipeline/panelStore';
import {
	dict, compute, UserPageQuery,
	CreateCrudOptionsProps, CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/stores/btnPermission';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => await api.GetList(query);

	const btnStore = BtnPermissionStore();
	const hasAuth = (code: string) => (btnStore.data || []).includes(code);

	return {
		crudOptions: {
			// 执行记录是只读的：只能由流水线的「发起执行」产生，不能在这里增删改
			request: { pageRequest },
			actionbar: { buttons: { add: { show: false } } },
			rowHandle: {
				fixed: 'right',
				width: 150,
				buttons: {
					view: {
						type: 'primary',
						text: '详情 / 推进',
						size: 'small',
						show: compute(() => hasAuth('pipelineRun:View')),
						click: (ctx: any) => openRunPanel(ctx.row.id),
					},
					edit: { show: false },
					remove: { show: false },
				},
			},
			columns: {
				_index: {
					title: '序号',
					form: { show: false },
					column: {
						align: 'center',
						width: '70px',
						columnSetDisabled: true,
						formatter: (context: any) => {
							const index = context.index ?? 1;
							const pagination = crudExpose!.crudBinding.value.pagination;
							return ((pagination!.currentPage ?? 1) - 1) * pagination!.pageSize + index + 1;
						},
					},
				},
				pipeline_name: {
					title: '流水线',
					type: 'input',
					search: { show: true, component: { placeholder: '请输入流水线名称' } },
					form: { show: false },
					column: { minWidth: 170 },
				},
				status: {
					title: '状态',
					type: 'dict-select',
					search: { show: true },
					dict: dict({
						data: [
							{ value: 'pending', label: '待执行', color: 'info' },
							{ value: 'running', label: '执行中', color: 'primary' },
							{ value: 'success', label: '全部成功', color: 'success' },
							// ★ partial 不是"failed 的别名"：节点配了「失败继续」时后面会照跑完，
							//   报成 success 就是一条绿色的"发布成功"，而实际上某一步是失败的。
							{ value: 'partial', label: '部分失败', color: 'warning' },
							{ value: 'failed', label: '失败', color: 'danger' },
							{ value: 'aborted', label: '已中止', color: 'info' },
						],
					}),
					form: { show: false },
					column: { width: 100, align: 'center' },
				},
				progress: {
					title: '进度',
					type: 'text',
					form: { show: false },
					column: {
						width: 140,
						align: 'center',
						formatter: ({ row }: any) => `${row.done_nodes ?? 0} / ${row.total_nodes ?? 0} 节点`,
					},
				},
				failed_nodes: {
					title: '失败节点',
					type: 'text',
					form: { show: false },
					column: {
						width: 90,
						align: 'center',
						formatter: ({ row }: any) => (row.failed_nodes ? row.failed_nodes : '—'),
					},
				},
				trigger_type: {
					title: '触发方式',
					type: 'dict-select',
					search: { show: true },
					dict: dict({
						data: [
							{ value: 'manual', label: '手动触发' },
							{ value: 'schedule', label: '定时触发' },
						],
					}),
					form: { show: false },
					column: { width: 100, align: 'center' },
				},
				creator_name: {
					title: '发起人',
					type: 'text',
					form: { show: false },
					column: { width: 110, formatter: ({ row }: any) => row.creator_name || '-' },
				},
				started_at: {
					title: '开始时间',
					type: 'datetime',
					form: { show: false },
					column: { width: 160 },
				},
				finished_at: {
					title: '结束时间',
					type: 'datetime',
					form: { show: false },
					column: {
						width: 160,
						formatter: ({ row }: any) => row.finished_at || (row.status === 'running' ? '进行中' : '—'),
					},
				},
				last_error: {
					title: '最近错误',
					type: 'text',
					form: { show: false },
					column: { minWidth: 200, showOverflowTooltip: true },
				},
			},
		},
	};
};
