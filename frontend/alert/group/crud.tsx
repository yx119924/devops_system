import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
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
          title: '群组名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入群组名称' } },
          form: { rules: [{ required: true, message: '请输入群组名称' }], component: { placeholder: '如 运维核心告警' } },
          column: { minWidth: 160 },
        },
        channels: {
          title: '通知渠道',
          type: 'dict-select',
          dict: dict({
            url: '/api/alert/channel/all/',
            value: 'id',
            label: 'name',
            getDataFromUrl: true,
          }),
          form: {
            rules: [{ required: true, message: '请选择至少一个渠道', type: 'array', min: 1 }],
            component: {
              mode: 'multiple',
              placeholder: '选择群组包含的渠道（多选）',
            },
          },
          column: {
            minWidth: 220,
            formatter: ({ row }: any) => {
              const list = row.channel_list || [];
              return list.map((c: any) => `${c.name}(${c.type})`).join(', ') || '-';
            },
          },
        },
        enabled: {
          title: '启用',
          type: 'switch',
          search: { show: true },
          column: { width: 80, align: 'center' },
          form: { value: true },
        },
        description: {
          title: '描述',
          type: 'input',
          form: { component: { placeholder: '请输入描述' } },
          column: { minWidth: 150, showOverflowTooltip: true },
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