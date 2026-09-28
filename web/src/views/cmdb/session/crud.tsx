import * as api from './api';
import { dict, UserPageQuery, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);

  return {
    crudOptions: {
      request: { pageRequest },
      actionbar: {
        buttons: { add: { show: false } },
      },
      rowHandle: {
        buttons: {
          replay: {
            text: '回放',
            iconRight: 'VideoPlay',
            type: 'text',
            show: ({ row }: any) => !!row.recording,
            click: ({ row }: any) => {
              context.openReplay(row);
            },
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
        server_name: {
          title: '服务器',
          type: 'text',
          search: { show: true, component: { placeholder: '服务器主机名' } },
          column: { minWidth: 130 },
        },
        operator_name: {
          title: '操作人',
          type: 'text',
          search: { show: true, component: { placeholder: '平台账号/姓名' } },
          column: { minWidth: 110 },
        },
        username: {
          title: '服务器账户',
          type: 'text',
          column: { minWidth: 100 },
        },
        ip: {
          title: '目标IP',
          type: 'text',
          search: { show: true },
          column: { minWidth: 130 },
        },
        status: {
          title: '状态',
          type: 'dict-select',
          dict: dict({
            data: [
              { value: 'active', label: '进行中', color: 'success' },
              { value: 'closed', label: '已结束', color: 'info' },
            ],
          }),
          column: { width: 90, align: 'center' },
        },
        start_time: {
          title: '开始时间',
          type: 'datetime',
          column: { minWidth: 170 },
        },
        end_time: {
          title: '结束时间',
          type: 'datetime',
          column: { minWidth: 170 },
        },
        duration: {
          title: '时长(秒)',
          type: 'number',
          column: { width: 90, align: 'center' },
        },
      },
    },
  };
};
