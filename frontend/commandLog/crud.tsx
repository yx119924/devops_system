import * as api from './api';
import { dict, UserPageQuery, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);

  return {
    crudOptions: {
      request: { pageRequest },
      actionbar: {
        buttons: { add: { show: false } },
      },
      rowHandle: {
        buttons: {
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
        command: {
          title: '命令',
          type: 'text',
          search: { show: true, component: { placeholder: '搜索命令' } },
          column: { minWidth: 300 },
        },
        source: {
          title: '来源',
          type: 'dict-select',
          search: { show: true },
          dict: dict({
            data: [
              { value: 'session', label: '交互会话' },
              { value: 'dispatch', label: '命令下发' },
            ],
          }),
          column: { width: 110, align: 'center' },
        },
        ip: {
          title: '目标IP',
          type: 'text',
          search: { show: true, component: { placeholder: '搜索目标IP' } },
          column: { width: 140, showOverflowTooltip: true },
        },
        dispatch: {
          title: '下发任务',
          type: 'text',
          search: { show: true, component: { placeholder: '任务ID' } },
          column: { width: 160, formatter: ({ row }: any) => row.dispatch_name || '-' },
        },
        is_dangerous: {
          title: '高危',
          type: 'dict-select',
          search: { show: true },
          dict: dict({
            data: [
              { value: true, label: '是', color: 'danger' },
              { value: false, label: '否', color: 'info' },
            ],
          }),
          column: {
            width: 80,
            align: 'center',
            formatter: ({ row }: any) => (row.is_dangerous ? '高危' : '正常'),
          },
        },
        timestamp: {
          title: '执行时间',
          type: 'datetime',
          column: { minWidth: 170 },
        },
      },
    },
  };
};
