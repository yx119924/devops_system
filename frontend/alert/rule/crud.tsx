import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet, compute } from '@fast-crud/fast-crud';
import { ElMessage, ElMessageBox } from 'element-plus';
import { BtnPermissionStore } from '/@/stores/btnPermission';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  const btnStore = BtnPermissionStore();
  const hasAuth = (code: string) => (btnStore.data || []).includes(code);

  const syncFromProm = async () => {
    try {
      const res: any = await api.SyncFromProm();
      if (res.code !== 2000) {
        ElMessage.error(res.msg || '同步失败');
        return;
      }
      const d = res.data || {};
      const lines: string[] = [];
      lines.push(`<b>${res.msg || '同步完成'}</b>`);
      if ((d.created || []).length) {
        lines.push('<br/><b>新增：</b>');
        lines.push((d.created as any[]).map((r) => `${r.name} <span style="color:#909399">(${r.source_group || '-'}，state=${r.state})</span>`).join('<br/>'));
      }
      if ((d.updated || []).length) {
        lines.push('<br/><b>更新：</b>');
        lines.push((d.updated as any[]).map((r) => `${r.name} <span style="color:#909399">(${r.source_group || '-'}，state=${r.state})</span>`).join('<br/>'));
      }
      if ((d.errors || []).length) {
        lines.push('<br/><b style="color:#f56c6c">错误：</b>');
        lines.push((d.errors as any[]).map((r) => `${r.rule}: ${r.reason}`).join('<br/>'));
      }
      if (!d.total_in_prom) {
        lines.push('<br/><span style="color:#909399">Prometheus 中暂无告警规则</span>');
      }
      ElMessageBox.alert(
        `<div style="font-size:13px;line-height:1.7;max-height:60vh;overflow:auto">${lines.join('')}</div>`,
        '从 Prometheus 同步告警规则',
        { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
      );
      crudExpose?.refresh?.();
    } catch (e: any) {
      ElMessage.error(e?.message || '同步异常');
    }
  };

  const preview = async (row: any) => {
    const res: any = await api.Preview(row.expr);
    if (res.code !== 2000) {
      ElMessage.error(res.msg || '预览失败');
      return;
    }
    const result = res.data?.data?.result || [];
    const resultType = res.data?.data?.resultType || 'vector';
    const lines = result.map((it: any) => {
      const metric = Object.entries(it.metric || {}).map(([k, v]) => `${k}="${v}"`).join(', ');
      const val = resultType === 'vector' ? it.value?.[1] : it.values?.length ? it.values[it.values.length - 1][1] : '-';
      return `${metric || '-'} => ${val}`;
    });
    ElMessageBox.alert(
      `<div style="font-size:13px;line-height:1.8"><b>类型：</b>${resultType}<br/><b>命中 ${result.length} 条：</b><br/>${lines.join('<br/>') || '无结果'}</div>`,
      `表达式预览：${row.name}`,
      { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
    );
  };

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      actionbar: {
        buttons: {
          add: { show: hasAuth('rule:Create') },
          sync: {
            text: '同步 Prom',
            type: 'primary',
            plain: true,
            icon: 'Refresh',
            show: hasAuth('rule:Create'),
            click: syncFromProm,
          },
        },
      },
      rowHandle: {
        buttons: {
          edit: { show: compute(() => hasAuth('rule:Update')) },
          remove: { show: compute(() => hasAuth('rule:Delete')) },
          preview: {
            text: '预览',
            iconRight: 'View',
            type: 'text',
            show: true,
            click: ({ row }: any) => preview(row),
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
          title: '规则名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入规则名称' } },
          form: { rules: [{ required: true, message: '请输入规则名称' }], component: { placeholder: '如 节点宕机告警' } },
          column: { minWidth: 160 },
        },
        expr: {
          title: 'PromQL 表达式',
          type: 'textarea',
          search: { show: true },
          form: { rules: [{ required: true, message: '请输入 PromQL 表达式' }], component: { placeholder: '如 up == 0 或 (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90', rows: 3 } },
          column: { minWidth: 300, showOverflowTooltip: true },
        },
        duration: {
          title: '持续时间',
          type: 'input',
          form: { value: '1m', component: { placeholder: '如 30s / 1m / 5m' } },
          column: { width: 100, align: 'center' },
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
          form: { value: 'warning' },
        },
        summary: {
          title: '告警摘要',
          type: 'input',
          form: { component: { placeholder: '告警标题摘要' } },
          column: { minWidth: 160, showOverflowTooltip: true },
        },
        description: {
          title: '告警描述',
          type: 'textarea',
          form: { component: { placeholder: '告警详细描述' } },
          column: { minWidth: 200, showOverflowTooltip: true },
        },
        enabled: {
          title: '启用',
          type: 'switch',
          search: { show: true },
          column: { width: 80, align: 'center' },
          form: { value: true },
        },
        group: {
          title: '告警群组',
          type: 'dict-select',
          dict: dict({
            url: '/api/alert/group/all/',
            value: 'id',
            label: 'name',
            getDataFromUrl: true,
          }),
          form: {
            component: { clearable: true, placeholder: '选择群组（不选则发所有启用渠道）' },
          },
          column: { width: 140, align: 'center', formatter: ({ row }: any) => row.group_name || '全部渠道' },
        },
        template: {
          title: '通知模板',
          type: 'dict-select',
          dict: dict({
            url: '/api/alert/template/all/',
            value: 'id',
            label: 'name',
            getDataFromUrl: true,
          }),
          form: {
            component: { clearable: true, placeholder: '选择模板（不选则用默认模板或内置格式）' },
          },
          column: { width: 150, align: 'center', formatter: ({ row }: any) => row.template_name || '默认模板' },
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
