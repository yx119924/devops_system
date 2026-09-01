import * as api from './api';
import { dict, UserPageQuery, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { ElMessage, ElMessageBox } from 'element-plus';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => await api.GetList(query);

	// 历史告警只读，新增/编辑/删除都返回错误
	const addRequest = async () => {
		ElMessage.error('历史告警由 Alertmanager webhook 自动采集，不支持手动新增');
		return { code: 4000, msg: '历史告警只读' };
	};
	const editRequest = async () => {
		ElMessage.error('历史告警由 Alertmanager webhook 自动采集，不支持手动编辑');
		return { code: 4000, msg: '历史告警只读' };
	};
	const delRequest = async () => {
		ElMessage.error('历史告警由 Alertmanager webhook 自动采集，不支持手动删除');
		return { code: 4000, msg: '历史告警只读' };
	};

	const showDetail = (row: any) => {
		const labelsText = Object.entries(row.labels || {}).map(([k, v]) => `${k}=${v}`).join('\n');
		const desc = row.description ? `\n\n描述：${row.description}` : '';
		const receivers = row.labels?.instance ? `\n\n实例：${row.instance}` : '';
		const time = `\n\n开始：${row.starts_at || '-'}\n恢复：${row.ends_at || '-'}`;
		const labels = labelsText ? `\n\n全部标签：\n${labelsText}` : '';
		ElMessageBox.alert(
			`<div style="font-size:13px;line-height:1.8;white-space:pre-wrap;">告警名称：<b>${row.alertname}</b>\n指纹：${row.fingerprint}\n摘要：${row.summary || '-'}${desc}${receivers}${time}${labels}</div>`,
			'告警详情',
			{ dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
		);
	};

	return {
		crudOptions: {
			request: { pageRequest, addRequest, editRequest, delRequest },
			// 只读页面，隐藏右上角"添加"按钮
			actionbar: {
				buttons: { add: { show: false } },
			},
			// 关闭行内编辑/删除按钮
			rowHandle: {
				show: false,
				buttons: {
					detail: {
						text: '详情',
						type: 'text',
						show: true,
						click: ({ row }: any) => showDetail(row),
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
				severity: {
					title: '级别',
					type: 'dict-select',
					search: { show: true },
					dict: dict({
						data: [
							{ value: 'critical', label: '严重', color: 'danger' },
							{ value: 'warning', label: '警告', color: 'warning' },
							{ value: 'info', label: '提示', color: 'info' },
						],
					}),
					column: { width: 90, align: 'center' },
				},
				alertname: {
					title: '告警名称',
					type: 'input',
					search: { show: true, component: { placeholder: '请输入告警名称' } },
					column: { minWidth: 160, showOverflowTooltip: true },
				},
				status: {
					title: '状态',
					type: 'dict-select',
					search: { show: true },
					dict: dict({
						data: [
							{ value: 'firing', label: '告警中', color: 'danger' },
							{ value: 'resolved', label: '已恢复', color: 'success' },
						],
					}),
					column: {
						width: 100,
						align: 'center',
						formatter: ({ row }: any) => row.status_label || row.status,
					},
				},
				instance: {
					title: '实例',
					type: 'input',
					search: { show: true, component: { placeholder: '请输入实例' } },
					column: { minWidth: 140, showOverflowTooltip: true },
				},
				summary: {
					title: '告警摘要',
					type: 'input',
					search: { show: true },
					column: { minWidth: 180, showOverflowTooltip: true },
				},
				starts_at: {
					title: '开始时间',
					type: 'datetime',
					form: { show: false },
					column: { minWidth: 170, align: 'center' },
				},
				ends_at: {
					title: '恢复时间',
					type: 'datetime',
					form: { show: false },
					column: { minWidth: 170, align: 'center' },
				},
				create_datetime: {
					title: '入库时间',
					type: 'datetime',
					form: { show: false },
					column: { minWidth: 170, align: 'center' },
				},
			},
		},
	};
};