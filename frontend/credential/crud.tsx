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
      actionbar: { buttons: { add: { show: hasAuth('credential:Create') } } },
      rowHandle: {
        buttons: {
          edit: { show: compute(() => hasAuth('credential:Update')) },
          remove: { show: compute(() => hasAuth('credential:Delete')) },
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
          title: '凭据名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入凭据名称' } },
          form: { rules: [{ required: true, message: '请输入凭据名称' }], component: { placeholder: '如 生产服务器 root' } },
          column: { minWidth: 150 },
        },
        username: {
          title: '用户名',
          type: 'input',
          search: { show: true },
          form: { value: 'root', component: { placeholder: '登录用户名' } },
          column: { minWidth: 100 },
        },
        auth_type: {
          title: '认证类型',
          type: 'dict-select',
          dict: dict({
            data: [
              { value: 'password', label: '密码', color: 'primary' },
              { value: 'private_key', label: '私钥', color: 'success' },
            ],
          }),
          column: { width: 100, align: 'center' },
          form: { value: 'password' },
        },
        password: {
          title: '密码',
          type: 'password',
          form: { component: { placeholder: '认证类型为密码时填写；编辑留空则不修改', showPassword: true } },
          column: { show: false },
        },
        private_key: {
          title: '私钥',
          type: 'textarea',
          form: { component: { placeholder: '认证类型为私钥时粘贴私钥内容；编辑留空则不修改', rows: 6 } },
          column: { show: false },
        },
        server: {
          title: '关联服务器',
          type: 'dict-select',
          dict: dict({
            url: '/api/cmdb/server/all/',
            value: 'id',
            label: 'hostname',
          }),
          column: { minWidth: 130, formatter: ({ row }: any) => row.server_name },
          form: { component: { placeholder: '留空为通用凭据', clearable: true, filterable: true } },
        },
        has_password: {
          title: '密码',
          type: 'text',
          column: {
            minWidth: 80,
            align: 'center',
            formatter: ({ row }: any) => (row.has_password ? '已设置' : '未设置'),
          },
          form: { show: false },
        },
        has_private_key: {
          title: '私钥',
          type: 'text',
          column: {
            minWidth: 80,
            align: 'center',
            formatter: ({ row }: any) => (row.has_private_key ? '已设置' : '未设置'),
          },
          form: { show: false },
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
