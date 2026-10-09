import * as api from './api';
import { openDesigner, openRunStart } from './panelStore';
import {
	dict, compute, UserPageQuery, AddReq, DelReq, EditReq,
	CreateCrudOptionsProps, CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/stores/btnPermission';

/** 表单 → 后端 payload */
function buildPayload(form: any, extra: any = {}) {
	return {
		name: (form.name || '').trim(),
		status: form.status === 0 ? 0 : 1,
		credential: form.credential || null,
		description: form.description || '',
		...extra,
	};
}

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
	const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);

	const btnStore = BtnPermissionStore();
	const hasAuth = (code: string) => (btnStore.data || []).includes(code);

	const addRequest = async ({ form }: AddReq) => {
		// 新流水线没有运行时参数，参数在编排页的「运行时参数」标签里维护
		return await api.AddObj(buildPayload(form, { params: [] }));
	};

	const editRequest = async ({ form, row }: EditReq) => {
		// ★ PUT 是**全量**更新（铁律 8）：`params` 不在这个表单里，
		//   不带回去就会被后端按空数组覆盖，把编排页维护的参数定义清掉。
		const params = Array.isArray(row.params) && row.params.length
			? row.params
			: (Array.isArray(form.params) ? form.params : []);
		return await api.UpdateObj({ id: row.id, ...buildPayload(form, { params }) });
	};

	return {
		crudOptions: {
			request: { pageRequest, addRequest, editRequest, delRequest },
			actionbar: {
				buttons: {
					add: { show: compute(() => hasAuth('pipeline:Create')), text: '新增流水线' },
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 320,
				buttons: {
					view: { show: false },
					edit: { show: compute(() => hasAuth('pipeline:Update')) },
					remove: {
						// 删除走 fast-crud 默认实现（会弹确认框）；后端在还有未结束执行时会拒绝
						show: compute(() => hasAuth('pipeline:Delete')),
						text: '删除',
					},
					design: {
						type: 'primary',
						text: '编排',
						size: 'small',
						order: 0,
						show: compute(() => hasAuth('pipeline:Nodes')),
						click: (ctx: any) => openDesigner(ctx.row),
					},
					run: {
						type: 'success',
						text: '发起执行',
						size: 'small',
						order: 1,
						show: {
							row: (row: any) => hasAuth('pipeline:Run') && row.status !== 0,
						},
						click: (ctx: any) => openRunStart(ctx.row),
					},
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
				name: {
					title: '流水线名称',
					type: 'input',
					search: { show: true, component: { placeholder: '请输入流水线名称' } },
					form: {
						rules: [{ required: true, message: '请输入流水线名称' }],
						component: { placeholder: '如 myapp 生产发布' },
					},
					column: { minWidth: 180 },
				},
				node_count: {
					title: '节点数',
					type: 'text',
					form: { show: false },
					column: { width: 80, align: 'center', formatter: ({ row }: any) => row.node_count ?? 0 },
				},
				credential: {
					title: '默认凭据',
					type: 'dict-select',
					dict: dict({
						url: '/api/bastion/credential/all/',
						value: 'id',
						label: 'name',
						getDataFromUrl: true,
					}),
					form: {
						component: { placeholder: '连接目标机的默认凭据', filterable: true, clearable: true },
						helper: '节点上没有单独指定凭据时用它；复用堡垒机凭据（已加密）',
						// ★ 编排页保存时会一起回写 credential，这里只是让新建时就有一个默认值
						col: { span: 12 },
					},
					column: { width: 140, formatter: ({ row }: any) => row.credential_name || '-' },
				},
				params: {
					title: '运行时参数',
					type: 'text',
					form: { show: false },
					column: {
						width: 120,
						formatter: ({ row }: any) => {
							const n = Array.isArray(row.params) ? row.params.length : 0;
							return n ? `${n} 个` : '无';
						},
					},
				},
				status: {
					title: '状态',
					type: 'dict-select',
					search: { show: true },
					dict: dict({
						data: [
							{ value: 1, label: '启用', color: 'success' },
							{ value: 0, label: '停用', color: 'info' },
						],
					}),
					form: { value: 1, col: { span: 12 } },
					column: { width: 80, align: 'center' },
				},
				creator_name: {
					title: '创建人',
					type: 'text',
					form: { show: false },
					column: { width: 110, formatter: ({ row }: any) => row.creator_name || '-' },
				},
				description: {
					title: '描述',
					type: 'textarea',
					form: { component: { rows: 2, placeholder: '选填' }, col: { span: 24 } },
					column: { show: false },
				},
				create_datetime: {
					title: '创建时间',
					type: 'datetime',
					form: { show: false },
					column: { width: 160 },
				},
			},
		},
	};
};
