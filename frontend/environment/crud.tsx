import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet, compute } from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/stores/btnPermission';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  const btnStore = BtnPermissionStore();
  const hasAuth = (code: string) => (btnStore.data || []).includes(code);

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      actionbar: { buttons: { add: { show: hasAuth('environment:Create') } } },
      rowHandle: {
        buttons: {
          edit: { show: compute(() => hasAuth('environment:Update')) },
          remove: { show: compute(() => hasAuth('environment:Delete')) },
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
          title: '环境名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入环境名称' } },
          form: { rules: [{ required: true, message: '请输入环境名称' }], component: { placeholder: '请输入环境名称' } },
          column: { minWidth: 140 },
        },
        code: {
          title: '环境编码',
          type: 'input',
          search: { show: true },
          form: { component: { placeholder: '请输入环境编码' } },
          column: { minWidth: 110 },
        },
        sort: {
          title: '排序',
          type: 'number',
          column: { width: 80, align: 'center' },
          form: { value: 1 },
        },
        status: {
          title: '状态',
          type: 'dict-radio',
          dict: dict({
            data: [
              { value: 1, label: '启用', color: 'success' },
              { value: 0, label: '停用', color: 'info' },
            ],
          }),
          column: { width: 90, align: 'center' },
          form: { value: 1 },
        },
        description: {
          title: '描述',
          type: 'textarea',
          form: { component: { placeholder: '请输入描述' } },
          column: { show: false },
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
