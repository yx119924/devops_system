import * as api from './api';
import { detailStore } from './detailStore';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { ElMessage, ElMessageBox } from 'element-plus';
import { BtnPermissionStore } from '/@/stores/btnPermission';

// 高危命令关键词（与后端 dvadmin.bastion.models.DANGEROUS_PATTERNS 保持一致）
const DANGEROUS_PATTERNS = [
	'rm -rf', 'rm -fr', 'rm -r /', 'mkfs', 'fdisk', 'dd if=', 'dd of=/dev/sd',
	'drop table', 'drop database', 'truncate table', ':(){', 'shutdown', 'reboot',
	'halt', 'poweroff', 'init 0', 'init 6', 'chmod -R 777 /', '> /dev/sda',
	'> /dev/sdb', 'mv / ', 'curl', 'wget',
];
const isDangerous = (cmd: string) => DANGEROUS_PATTERNS.some((p) => (cmd || '').includes(p));

/**
 * 把 CMDB 多选 + 手动 IP 输入拼装成后端 targets 字段：
 * - CMDB 来源：[{server_id, label, ip, ssh_port}]
 * - 手动 IP：[{server_id: null, label: ip, ip, ssh_port}]
 */
async function buildTargets(crudExpose: any, cmdbIds: number[] | null | undefined, manualText: string | null | undefined) {
  const targets: any[] = [];
  if (cmdbIds && cmdbIds.length) {
    // 从 dict 缓存拿完整服务器数据（label/ip/ssh_port）
    const dictStore = crudExpose?.crudBinding?.value?.dict;
    let serverMap: Record<number, any> = {};
    try {
      // fast-crud 的 dict 缓存结构：crudExpose.crudBinding.value.dict['dispatch_options'] 是 dict 对象
      const dictMap: any = crudExpose?.crudBinding?.value?.dict || {};
      const dispatchDict = dictMap['dispatch_options'] || dictMap['url#/api/cmdb/server/dispatch_options/'];
      const list: any[] = dispatchDict?.data || dispatchDict?.dict?.data || [];
      serverMap = Object.fromEntries(list.map((s: any) => [s.id, s]));
    } catch (e) {
      console.warn('[dispatch] dict 缓存未命中，回退调接口', e);
    }
    if (!Object.keys(serverMap).length) {
      try {
        const resp: any = await api.GetDispatchOptions();
        const list: any[] = resp?.data?.data || resp?.data || [];
        serverMap = Object.fromEntries(list.map((s: any) => [s.id, s]));
      } catch (e) {
        console.error('[dispatch] 取服务器列表失败', e);
      }
    }
    cmdbIds.forEach((sid) => {
      const s = serverMap[sid];
      if (s) {
        targets.push({
          server_id: s.id,
          label: s.hostname,
          ip: s.ip,
          ssh_port: s.ssh_port || 22,
        });
      }
    });
  }
  // 手动 IP
  (manualText || '')
    .split(/\r?\n/)
    .map((s: string) => s.trim())
    .filter(Boolean)
    .forEach((line: string) => {
      const [ip, port] = line.split(':');
      targets.push({
        server_id: null,
        label: ip,
        ip,
        ssh_port: port ? parseInt(port, 10) || 22 : 22,
      });
    });
  return targets;
}

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);

  // v-auth 权限判断：命令下发按钮权限（dispatch:Execute / dispatch:Retry / dispatch:Delete / dispatch:View）
  const btnStore = BtnPermissionStore();
  const hasAuth = (code: string) => (btnStore.data || []).includes(code);

  const confirmDangerous = async (command: string) => {
    if (!isDangerous(command)) return true;
    try {
      await ElMessageBox.confirm(
        '该命令包含高危关键词（如 rm -rf / mkfs / dd / shutdown 等），可能造成不可逆影响。请确认是否继续？',
        '高危命令警告',
        { type: 'warning', confirmButtonText: '确认执行', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
      );
      return true;
    } catch (e) {
      return false;
    }
  };

  const addRequest = async ({ form }: AddReq) => {
    const targets = await buildTargets(crudExpose, form.cmdb_targets, form.manual_ips);
    if (!targets.length) {
      ElMessage.error('请至少选择一个 CMDB 目标或填写手动 IP');
      throw new Error('未选择目标');
    }
    const payload: any = {
      name: form.name,
      command: form.command,
      credential: form.credential,
      targets,
      timeout: form.timeout || 30,
      max_workers: form.max_workers || 10,
    };
    return await api.AddObj(payload);
  };

  const editRequest = async ({ form, row }: EditReq) => {
    form.id = row.id;
    const targets = await buildTargets(crudExpose, form.cmdb_targets, form.manual_ips);
    if (!targets.length) {
      ElMessage.error('请至少选择一个 CMDB 目标或填写手动 IP');
      throw new Error('未选择目标');
    }
    return await api.UpdateObj({
      id: row.id,
      name: form.name,
      command: form.command,
      credential: form.credential,
      targets,
      timeout: form.timeout || 30,
      max_workers: form.max_workers || 10,
    });
  };

  // 执行/重试共用逻辑：高危确认 → 调接口 → 刷新列表 → 自动弹详情
  const doExecute = async (id: number, retry: boolean, command: string) => {
    if (!(await confirmDangerous(command))) {
      return;
    }
    ElMessage.info(retry ? '正在重试失败项…' : '正在下发命令…');
    try {
      const res = await api.ExecuteObj(id, retry);
      const data = res.data?.data ?? res.data ?? {};
      const succ = data.success_count ?? 0;
      const total = data.total ?? 0;
      const fail = data.failed_count ?? 0;
      if (fail > 0) {
        ElMessage.warning(`执行完成：${succ}/${total} 成功，${fail} 失败`);
      } else {
        ElMessage.success(`执行完成：${succ}/${total} 全部成功`);
      }
      if (crudExpose?.refresh) {
        await crudExpose.refresh();
      }
      detailStore.open(id);
    } catch (e: any) {
      ElMessage.error('执行失败：' + (e?.message || e));
    }
  };

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      actionbar: {
        buttons: { add: { show: true } },
      },
      rowHandle: {
        fixed: 'right',
        minWidth: 340,
        buttons: {
          view: { show: false },
          edit: { show: false },
          remove: {
            type: 'danger',
            text: '删除',
            show: { row: () => hasAuth('dispatch:Delete') },
          },
          detail: {
            type: 'primary',
            text: '查看',
            size: 'small',
            order: 0,
            show: { row: () => hasAuth('dispatch:View') },
            click: (ctx: any) => {
              detailStore.open(ctx.row.id);
            },
          },
          execute: {
            type: 'success',
            text: '执行',
            size: 'small',
            order: 1,
            show: { row: (row: any) => hasAuth('dispatch:Execute') && ['pending', 'failed', 'partial'].includes(row.status) },
            click: (ctx: any) => {
              doExecute(ctx.row.id, false, ctx.row.command);
            },
          },
          retry: {
            type: 'warning',
            text: '重试失败',
            size: 'small',
            order: 2,
            show: { row: (row: any) => hasAuth('dispatch:Retry') && ['partial', 'failed'].includes(row.status) },
            click: (ctx: any) => {
              doExecute(ctx.row.id, true, ctx.row.command);
            },
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
          form: { rules: [{ required: true, message: '请输入任务名称' }], component: { placeholder: '如 批量重启 nginx' } },
          column: { minWidth: 180 },
        },
        command: {
          title: '命令',
          type: 'textarea',
          form: {
            rules: [{ required: true, message: '请输入要执行的命令' }],
            component: { placeholder: '单条命令，每台目标都会执行', rows: 3 },
            col: { span: 24 },
          },
          column: { minWidth: 200, showOverflowTooltip: true },
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
            component: { placeholder: '选择执行命令用的凭据（任务级统一）', filterable: true },
          },
          column: { minWidth: 140, formatter: ({ row }: any) => row.credential_name || '-' },
        },
        cmdb_targets: {
          title: 'CMDB 目标',
          type: 'dict-select',
          dict: dict({
            url: '/api/cmdb/server/dispatch_options/',
            value: 'id',
            label: 'hostname',
            getDataFromUrl: true,
          }),
          form: {
            component: {
              multiple: true,
              clearable: true,
              filterable: true,
              placeholder: '从 CMDB 服务器多选（在线状态）',
            },
            helper: '从 CMDB 已录入的服务器里选，会用每个服务器的 IP 连接',
          },
          column: { show: false },
        },
        manual_ips: {
          title: '手动 IP（兜底）',
          type: 'textarea',
          form: {
            component: {
              placeholder: '每行一个 IP，可指定端口：192.168.1.10 或 192.168.1.10:2222',
              rows: 3,
            },
            helper: 'CMDB 之外的目标（临时机器）。每行一个 IP[:port]',
            col: { span: 24 },
          },
          column: { show: false },
        },
        timeout: {
          title: '超时(秒)',
          type: 'number',
          form: { value: 30, component: { min: 5, max: 600 } },
          column: { width: 100, align: 'center' },
        },
        max_workers: {
          title: '并发数',
          type: 'number',
          form: { value: 10, component: { min: 1, max: 50 } },
          column: { width: 80, align: 'center' },
        },
        status: {
          title: '状态',
          type: 'text',
          dict: dict({
            data: [
              { value: 'pending', label: '待执行', color: 'info' },
              { value: 'running', label: '执行中', color: 'primary' },
              { value: 'success', label: '全部成功', color: 'success' },
              { value: 'partial', label: '部分失败', color: 'warning' },
              { value: 'failed', label: '全部失败', color: 'danger' },
            ],
          }),
          column: { width: 110, align: 'center' },
          form: { show: false },
        },
        total: {
          title: '目标',
          type: 'text',
          column: { width: 70, align: 'center' },
          form: { show: false },
        },
        success_count: {
          title: '成功',
          type: 'text',
          column: { width: 70, align: 'center' },
          form: { show: false },
        },
        failed_count: {
          title: '失败',
          type: 'text',
          column: { width: 70, align: 'center' },
          form: { show: false },
        },
        last_error: {
          title: '最近错误',
          type: 'text',
          column: { minWidth: 200, showOverflowTooltip: true },
          form: { show: false },
        },
        started_at: {
          title: '开始执行',
          type: 'datetime',
          form: { show: false },
          column: { width: 160 },
        },
        finished_at: {
          title: '完成时间',
          type: 'datetime',
          form: { show: false },
          column: { width: 160 },
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