import * as api from './api';
import { openPanel, runAction } from './panelStore';
import {
	dict, compute, UserPageQuery, AddReq, DelReq, EditReq,
	CreateCrudOptionsProps, CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { ElMessage, ElMessageBox } from 'element-plus';
import { BtnPermissionStore } from '/@/stores/btnPermission';

/** 从服务器下拉的 dict 缓存（或回退调接口）拿 id → 服务器信息 的映射 */
async function loadServerMap(crudExpose: any): Promise<Record<number, any>> {
	let list: any[] = [];
	try {
		const dictMap: any = crudExpose?.crudBinding?.value?.dict || {};
		const d = dictMap['dispatch_options'] || dictMap['url#/api/cmdb/server/dispatch_options/'];
		list = d?.data || d?.dict?.data || [];
	} catch (e) {
		console.warn('[logCollect] dict 缓存未命中，回退调接口', e);
	}
	if (!list.length) {
		try {
			const resp: any = await api.GetServerOptions();
			list = resp?.data?.data || resp?.data || [];
		} catch (e) {
			console.error('[logCollect] 取服务器列表失败', e);
		}
	}
	return Object.fromEntries((list || []).map((s: any) => [s.id, s]));
}

/** CMDB 多选 id → 后端 targets。★ ip/ssh_port 只是展示用，后端会从 CMDB 回读覆盖 */
async function buildTargets(crudExpose: any, cmdbIds: number[] | null | undefined) {
	const targets: any[] = [];
	if (!cmdbIds || !cmdbIds.length) return targets;
	const map = await loadServerMap(crudExpose);
	cmdbIds.forEach((sid) => {
		const s = map[sid];
		if (s) {
			targets.push({
				server_id: s.id,
				label: s.hostname,
				ip: s.ip,
				ssh_port: s.ssh_port || 22,
			});
		}
	});
	return targets;
}

/** 表单 → 后端 payload。extra_fields 是 textarea 里的 JSON 文本 */
function buildPayload(form: any, targets: any[]) {
	let extra: any = {};
	const raw = (form.extra_fields_text || '').trim();
	if (raw) {
		try {
			extra = JSON.parse(raw);
			if (typeof extra !== 'object' || Array.isArray(extra)) {
				ElMessage.error('附加字段必须是 JSON 对象，如 {"app_name":"myapp"}');
				throw new Error('额外的字段格式错误');
			}
		} catch (e: any) {
			if (e?.message === '额外的字段格式错误') throw e;
			ElMessage.error('附加字段不是合法 JSON：' + (e?.message || e));
			throw new Error('附加字段不是合法 JSON');
		}
	}
	return {
		name: form.name,
		source: form.source || null,
		index_prefix: (form.index_prefix || '').trim(),
		collect_mode: 'filebeat',
		path_pattern: (form.path_pattern || '').trim(),
		include_regex: form.include_regex || '',
		exclude_regex: form.exclude_regex || '',
		min_level: form.min_level || '',
		// ★ 默认 true：用户拍板的是「只采新增」，不能因为表单没传就退化成全量采集
		tail_new_only: form.tail_new_only !== false,
		multiline_start: form.multiline_start || '',
		time_regex: form.time_regex || '',
		time_layout: form.time_layout || '',
		extra_fields: extra,
		// ★ 去掉尾部斜杠：和远程路径拼接时不能出现 "//"（后端 validate 也会 rstrip，
		//   但前端不该把「拼出干净路径」这件事推给后端兜底）
		remote_dir: (form.remote_dir || '/etc/filebeat/inputs.d').trim().replace(/\/+$/, '')
			|| '/etc/filebeat/inputs.d',
		targets,
		credential: form.credential,
		status: form.status === 0 ? 0 : 1,
		description: form.description || '',
	};
}

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
	const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);

	const btnStore = BtnPermissionStore();
	const hasAuth = (code: string) => (btnStore.data || []).includes(code);

	const addRequest = async ({ form }: AddReq) => {
		const targets = await buildTargets(crudExpose, form.cmdb_targets);
		if (!targets.length) {
			ElMessage.error('请至少选择一台 CMDB 服务器');
			throw new Error('未选择目标');
		}
		return await api.AddObj(buildPayload(form, targets));
	};

	const editRequest = async ({ form, row }: EditReq) => {
		const targets = await buildTargets(crudExpose, form.cmdb_targets);
		if (!targets.length) {
			ElMessage.error('请至少选择一台 CMDB 服务器');
			throw new Error('未选择目标');
		}
		return await api.UpdateObj({ id: row.id, ...buildPayload(form, targets) });
	};

	/** 下发/停止都要二次确认 —— 这两个动作会 SSH 改目标机并重启 filebeat */
	const confirmTouch = async (kind: 'apply' | 'stop', row: any) => {
		const isApply = kind === 'apply';
		try {
			await ElMessageBox.confirm(
				isApply
					? `将把配置片段下发到「${row.name}」的 ${row.target_count || 0} 台目标机，`
						+ `写 $(filebeat)/inputs.d/ 下的 xwops-task-${row.id}.yml 并重启 filebeat。`
						+ `\n\n目标机原有同名片段会先备份；平台不会修改 filebeat 主配置。确认继续？`
					: `将从 ${row.target_count || 0} 台目标机删除 xwops-task-${row.id}.yml 并重启 filebeat，`
						+ `该任务的采集会立即停止。\n\n其它任务的配置不受影响。确认继续？`,
				isApply ? '下发采集配置' : '停止采集',
				{ type: isApply ? 'info' : 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
			);
		} catch (e) {
			return;
		}
		await runAction(kind, row, () => crudExpose?.refresh?.());
	};

	return {
		crudOptions: {
			request: { pageRequest, addRequest, editRequest, delRequest },
			actionbar: {
				buttons: {
					add: { show: compute(() => hasAuth('logCollect:Create')), text: '新增采集任务' },
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 400,
				buttons: {
					view: { show: false },
					edit: { show: compute(() => hasAuth('logCollect:Update')) },
					remove: { show: compute(() => hasAuth('logCollect:Delete')), text: '删除' },
					preview: {
						type: 'primary',
						text: '试跑',
						size: 'small',
						order: 0,
						show: compute(() => hasAuth('logCollect:Preview')),
						click: (ctx: any) => openPanel('preview', ctx.row),
					},
					detect: {
						type: 'info',
						text: '检测',
						size: 'small',
						order: 1,
						show: compute(() => hasAuth('logCollect:Detect')),
						click: (ctx: any) => openPanel('detect', ctx.row),
					},
					apply: {
						type: 'success',
						text: '下发',
						size: 'small',
						order: 2,
						show: compute(() => hasAuth('logCollect:Apply')),
						click: (ctx: any) => confirmTouch('apply', ctx.row),
					},
					stop: {
						type: 'danger',
						text: '停止',
						size: 'small',
						order: 3,
						// 只有"已下发/下发失败"的任务才需要停止（未下发的没有片段可删）
						show: {
							row: (row: any) => hasAuth('logCollect:Stop')
								&& ['applied', 'failed'].includes(row.run_status),
						},
						click: (ctx: any) => confirmTouch('stop', ctx.row),
					},
					records: {
						type: 'text',
						text: '台账',
						size: 'small',
						order: 4,
						show: compute(() => hasAuth('logCollect:Records')),
						click: (ctx: any) => openPanel('records', ctx.row),
					},
					patch: {
						type: 'text',
						text: '主配置',
						size: 'small',
						order: 5,
						show: compute(() => hasAuth('logCollect:MainPatch')),
						click: (ctx: any) => openPanel('patch', ctx.row),
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
					title: '任务名称',
					type: 'input',
					search: { show: true, component: { placeholder: '请输入任务名称' } },
					form: { rules: [{ required: true, message: '请输入任务名称' }], component: { placeholder: '如 myapp-prod 应用日志' } },
					column: { minWidth: 160 },
				},
				path_pattern: {
					title: '日志路径',
					type: 'input',
					form: {
						rules: [{ required: true, message: '请输入日志路径' }],
						component: { placeholder: '如 /var/log/myapp/*.log' },
						helper: '绝对路径，支持通配 * 与 []；每台目标机上路径需一致',
						col: { span: 24 },
					},
					column: { minWidth: 220, showOverflowTooltip: true },
				},
				index_prefix: {
					title: '索引前缀',
					type: 'input',
					form: {
						rules: [
							{ required: true, message: '请输入索引前缀' },
							{ pattern: /^[a-z0-9][a-z0-9_.-]{0,63}$/, message: '只允许小写字母数字开头，含 _ - .' },
						],
						component: { placeholder: '如 myapp' },
						helper: '检索时用 myapp-* 通配。★ 实际落库索引由目标机 filebeat 的 output 决定，可用「检测」查看',
						col: { span: 12 },
					},
					column: { width: 130 },
				},
				source: {
					title: 'ES 数据源',
					type: 'dict-select',
					dict: dict({
						url: '/api/log/es/all/',
						value: 'id',
						label: 'name',
						getDataFromUrl: true,
					}),
					form: {
						component: { placeholder: '用于检索与比对', filterable: true, clearable: true },
						helper: '仅用于「用这个索引去检索」的跳转与比对，不决定写入目标',
					},
					column: { width: 140, formatter: ({ row }: any) => row.source_name || '-' },
				},
				cmdb_targets: {
					title: '目标服务器',
					type: 'dict-select',
					dict: dict({
						url: '/api/cmdb/server/dispatch_options/',
						value: 'id',
						label: 'hostname',
						getDataFromUrl: true,
					}),
					form: {
						rules: [{ required: true, message: '请选择目标服务器' }],
						component: {
							multiple: true,
							clearable: true,
							filterable: true,
							placeholder: '从 CMDB 服务器多选',
						},
						helper: '只能选到你有操作授权的服务器；连接地址取 CMDB 里的最新 IP',
						col: { span: 24 },
					},
					column: { show: false },
				},
				target_count: {
					title: '目标数',
					type: 'text',
					form: { show: false },
					column: { width: 80, align: 'center', formatter: ({ row }: any) => row.target_count ?? 0 },
				},
				credential: {
					title: '凭据',
					type: 'dict-select',
					dict: dict({
						url: '/api/bastion/credential/all/',
						value: 'id',
						label: 'name',
						getDataFromUrl: true,
					}),
					form: {
						rules: [{ required: true, message: '请选择凭据' }],
						component: { placeholder: '连接目标机的统一凭据', filterable: true },
						helper: '复用堡垒机凭据（已加密）；需要对这些机器有操作权限',
						col: { span: 12 },
					},
					column: { show: false },
				},
				include_regex: {
					title: '包含规则',
					type: 'input',
					form: {
						component: { placeholder: '如 ERROR|Exception（留空=全部采集）' },
						helper: '★ 只能用 RE2 正则：不支持 (?=) (?! ) 预查与 \\1 反向引用（保存时会校验）',
						col: { span: 12 },
					},
					column: { show: false },
				},
				exclude_regex: {
					title: '排除规则',
					type: 'input',
					form: {
						component: { placeholder: '如 healthcheck|ping（留空=不排除）' },
						helper: '优先级高于包含规则',
						col: { span: 12 },
					},
					column: { show: false },
				},
				min_level: {
					title: '最低级别',
					type: 'dict-select',
					dict: dict({
						data: [
							{ value: '', label: '不限（全部采集）' },
							{ value: 'debug', label: 'DEBUG 及以上' },
							{ value: 'info', label: 'INFO 及以上' },
							{ value: 'warn', label: 'WARN 及以上' },
							{ value: 'error', label: 'ERROR 及以上' },
						],
					}),
					form: { value: '', component: { placeholder: '低于该级别的日志直接丢弃' }, col: { span: 12 } },
					column: { show: false },
				},
				tail_new_only: {
					title: '只采新增',
					type: 'checkbox',
					form: {
						value: true,
						helper: '★ 开启后从文件**末尾**开始采集，接入前的历史日志不会进 ES。'
							+ '注意：目标机 filebeat ≥7.9 的 filestream 没有 tail_files 等价项，'
							+ '为兑现"只采新增"，平台会自动改用 log input 承载（下发结果里会说明原因）',
						col: { span: 12 },
					},
					column: {
						width: 90,
						align: 'center',
						formatter: ({ row }: any) => (row.tail_new_only === false ? '全量' : '仅新增'),
					},
				},
				multiline_start: {
					title: '多行起始正则',
					type: 'input',
					form: {
						component: { placeholder: '如 ^\\d{4}-\\d{2}-\\d{2}（留空=逐行采集）' },
						helper: 'Java 堆栈这类多行日志：匹配该正则的行作为新记录起点',
						col: { span: 12 },
					},
					column: { show: false },
				},
				time_regex: {
					title: '时间提取正则',
					type: 'input',
					form: {
						component: { placeholder: '^(?P<log_time>\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})' },
						helper: '★ 建议填：不填则 @timestamp 记的是采集时刻而非日志时间，时间范围检索会失真',
						col: { span: 12 },
					},
					column: { show: false },
				},
				time_layout: {
					title: '时间格式',
					type: 'input',
					form: {
						component: { placeholder: '如 2006-01-02 15:04:05' },
						helper: 'Go 时间布局（不是 Java 的 yyyy-MM-dd）',
						col: { span: 12 },
					},
					column: { show: false },
				},
				extra_fields_text: {
					title: '附加字段',
					type: 'textarea',
					form: {
						component: { rows: 3, placeholder: '{"app_name":"myapp","env_name":"prod"}' },
						// ★ 2026-09-24：原占位符写的是 {"service":"myapp"} —— 而 service 是
						//   ECS 的**对象型**顶层字段，照抄它会让 ES 以 HTTP 400 拒收**每一条**
						//   日志（filebeat 收到 400 直接丢弃事件，平台与 filebeat 都看不出异常）。
						//   示例本身是坑，已改成自定义名，并在 helper 里把原因讲清楚。
						helper: 'JSON 对象，随每条日志写入；留空则不附加。键请用自定义名，不要用 service/host/agent/log 等 ECS 名（ES 会拒收全部日志）',
						col: { span: 24 },
					},
					column: { show: false },
				},
				remote_dir: {
					title: '片段目录',
					type: 'input',
					form: {
						value: '/etc/filebeat/inputs.d',
						component: { placeholder: '/etc/filebeat/inputs.d' },
						helper: '目标机上 filebeat 加载配置片段的目录',
						col: { span: 12 },
					},
					column: { show: false },
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
				run_status: {
					title: '下发状态',
					type: 'dict-select',
					dict: dict({
						data: [
							{ value: 'pending', label: '未下发', color: 'info' },
							{ value: 'applied', label: '已下发', color: 'success' },
							{ value: 'failed', label: '下发失败', color: 'danger' },
							{ value: 'stopped', label: '已停止', color: 'warning' },
						],
					}),
					form: { show: false },
					column: { width: 100, align: 'center' },
				},
				last_action_at: {
					title: '最近操作',
					type: 'datetime',
					form: { show: false },
					column: { width: 160 },
				},
				last_message: {
					title: '最近结果',
					type: 'text',
					form: { show: false },
					column: { minWidth: 200, showOverflowTooltip: true },
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
