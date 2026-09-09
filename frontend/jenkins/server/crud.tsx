import * as api from './api';
import { UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet, compute } from '@fast-crud/fast-crud';
import { ElMessage } from 'element-plus';
import { BtnPermissionStore } from '/@/stores/btnPermission';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  const btnStore = BtnPermissionStore();
  const hasAuth = (code: string) => (btnStore.data || []).includes(code);

  const testSource = async (row: any) => {
    const res: any = await api.TestSource(row.id);
    if (res.code === 2000) {
      ElMessage.success(res.msg || '连接正常');
    } else {
      ElMessage.error(res.msg || '连接失败');
    }
  };

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      actionbar: { buttons: { add: { show: hasAuth('jenkinsServer:Create') } } },
      rowHandle: {
        buttons: {
          edit: { show: compute(() => hasAuth('jenkinsServer:Update')) },
          remove: { show: compute(() => hasAuth('jenkinsServer:Delete')) },
          test: {
            text: '测试连接',
            iconRight: 'Connection',
            type: 'text',
            show: true,
            click: ({ row }: any) => testSource(row),
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
          title: '服务器名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入服务器名称' } },
          form: { rules: [{ required: true, message: '请输入服务器名称' }], component: { placeholder: '如 内网 Jenkins' } },
          column: { minWidth: 150 },
        },
        url: {
          title: 'Jenkins 地址',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入地址' } },
          form: { rules: [{ required: true, message: '请输入 Jenkins 地址' }], component: { placeholder: '如 http://192.168.1.100:8080' } },
          column: { minWidth: 220 },
        },
        username: {
          title: '用户名',
          type: 'input',
          form: { component: { placeholder: '认证用户名，可留空用匿名' } },
          column: { minWidth: 120 },
        },
        token: {
          title: 'API Token',
          type: 'password',
          form: { component: { placeholder: '编辑时留空表示不修改' } },
          column: { show: false },
        },
        has_token: {
          title: '已配凭据',
          type: 'dict-select',
          dict: {
            data: [
              { value: true, label: '已配置', color: 'success' },
              { value: false, label: '未配置', color: 'info' },
            ],
          },
          form: { show: false },
          column: { width: 100, align: 'center' },
        },
        status: {
          title: '状态',
          type: 'dict-select',
          search: { show: true },
          dict: {
            data: [
              { value: 1, label: '启用', color: 'success' },
              { value: 0, label: '停用', color: 'info' },
            ],
          },
          column: { width: 90, align: 'center' },
          form: { value: 1 },
        },
        sort: {
          title: '排序',
          type: 'number',
          column: { width: 80, align: 'center' },
          form: { value: 1, component: { min: 1 } },
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
