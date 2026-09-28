import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet, compute } from '@fast-crud/fast-crud';
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
      actionbar: { buttons: { add: { show: hasAuth('esSource:Create') } } },
      rowHandle: {
        buttons: {
          edit: { show: compute(() => hasAuth('esSource:Update')) },
          remove: { show: compute(() => hasAuth('esSource:Delete')) },
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
          title: '数据源名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入数据源名称' } },
          form: { rules: [{ required: true, message: '请输入数据源名称' }], component: { placeholder: '如 内网 ES 日志' } },
          column: { minWidth: 160 },
        },
        url: {
          title: 'ES 地址',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入地址' } },
          form: { rules: [{ required: true, message: '请输入 ES 地址' }], component: { placeholder: '如 http://192.168.1.100:9200' } },
          column: { minWidth: 240 },
        },
        index_pattern: {
          title: '索引模式',
          type: 'input',
          form: { value: 'logs-*', component: { placeholder: '如 logs-* / app-*' } },
          column: { minWidth: 140 },
        },
        username: {
          title: '用户名',
          type: 'input',
          form: { component: { placeholder: 'Basic Auth 用户名（可选）' } },
          column: { width: 110 },
        },
        password: {
          title: '密码',
          type: 'password',
          form: { component: { placeholder: '留空则不修改' } },
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
          column: { width: 90, align: 'center' },
          form: { value: 1 },
        },
        sort: {
          title: '排序',
          type: 'number',
          column: { width: 90, align: 'center' },
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
