import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { ElMessage, ElMessageBox } from 'element-plus';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
	const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
	const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
	const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

	// 预览：用当前行的 body 调用后端 preview 接口，显示渲染结果（支持在表单中预览）
	const onPreview = async ({ row }: any) => {
		// 优先取表单中正在编辑的内容（添加/编辑对话框打开时），否则取当前行的 body
		const editable = (crudExpose as any).editableForm?.value?.form;
		const body = (editable && editable.body) || row?.body || '';
		if (!body.trim()) {
			ElMessage.warning('模板内容为空');
			return;
		}
		try {
			const res: any = await api.Preview(body);
			if (res.code === 2000) {
				const rendered = res.data?.rendered || '';
				const sample = res.data?.sample || {};
				const sampleText = Object.entries(sample)
					.filter(([k]) => k !== 'labels')
					.map(([k, v]) => `${k} = ${JSON.stringify(v)}`)
					.join('\n');
				const labelsText = Object.entries(sample.labels || {})
					.map(([k, v]) => `${k}=${v}`)
					.join('\n');
				const safe = (s: string) => s.replace(/[<>&]/g, (c: string) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' } as any)[c]);
				ElMessageBox.alert(
					`<div style="font-size:13px;line-height:1.7;">
						<div style="margin-bottom:8px;"><b>渲染结果：</b></div>
						<pre style="white-space:pre-wrap;background:#f5f7fa;padding:10px;border-radius:4px;">${safe(rendered)}</pre>
						<div style="margin-top:10px;"><b>使用的示例数据：</b></div>
						<pre style="white-space:pre-wrap;background:#fafafa;padding:8px;border-radius:4px;color:#666;">${safe(sampleText)}\nlabels:\n${safe(labelsText)}</pre>
					</div>`,
					'模板预览',
					{ dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
				);
			} else {
				ElMessage.error(res.msg || '预览失败');
			}
		} catch (e: any) {
			ElMessage.error(e?.message || '预览请求异常');
		}
	};

	return {
		crudOptions: {
			request: { pageRequest, addRequest, editRequest, delRequest },
			rowHandle: {
				buttons: {
					preview: {
						text: '预览',
						type: 'text',
						show: true,
						click: ({ row }: any) => onPreview({ row }),
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
					title: '模板名称',
					type: 'input',
					search: { show: true, component: { placeholder: '请输入模板名称' } },
					form: { rules: [{ required: true, message: '请输入模板名称' }], component: { placeholder: '如 高 CPU 告警模板' } },
					column: { minWidth: 160 },
				},
				description: {
					title: '描述',
					type: 'input',
					form: { component: { placeholder: '请输入描述' } },
					column: { minWidth: 140, showOverflowTooltip: true },
				},
				body: {
					title: '模板内容（Jinja2）',
					type: 'input',
					form: {
						rules: [{ required: true, message: '请输入模板内容' }],
						component: {
							type: 'textarea',
							rows: 8,
							placeholder: '可用变量：{{ alertname }} / {{ severity }} / {{ status }} / {{ instance }} / {{ summary }} / {{ description }} / {{ startsAt }} / {{ endsAt }} / {{ value }} / {{ labels.xxx }}',
						},
						helper: '支持 Jinja2 语法：{{ 变量 }}、{% if %}、{% for %}。可用变量见左侧提示。',
					},
					column: {
						minWidth: 260,
						showOverflowTooltip: true,
						formatter: ({ row }: any) => {
							const b = (row.body || '').replace(/\s+/g, ' ').trim();
							return b.length > 60 ? b.slice(0, 60) + '...' : b;
						},
					},
				},
				variables: {
					title: '使用变量',
					form: { show: false },
					column: {
						minWidth: 160,
						formatter: ({ row }: any) => {
							const vars = row.variables || [];
							return vars.length ? vars.join(', ') : '-';
						},
					},
				},
				is_default: {
					title: '默认模板',
					type: 'switch',
					column: { width: 90, align: 'center' },
					form: { value: false, helper: '勾选后作为兜底模板，未指定模板的规则触发时使用' },
				},
				enabled: {
					title: '启用',
					type: 'switch',
					search: { show: true },
					column: { width: 80, align: 'center' },
					form: { value: true },
				},
				create_datetime: {
					title: '创建时间',
					type: 'datetime',
					form: { show: false },
					column: { minWidth: 160 },
				},
			},
		},
	};
};