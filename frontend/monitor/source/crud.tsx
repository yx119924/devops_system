import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { ElMessage } from 'element-plus';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

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
      rowHandle: {
        buttons: {
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
          form: { rules: [{ required: true, message: '请输入数据源名称' }], component: { placeholder: '如 本机 Prometheus' } },
          column: { minWidth: 160 },
        },
        source_type: {
          title: '类型',
          type: 'dict-select',
          search: { show: true },
          dict: dict({
            data: [
              { value: 'prometheus', label: 'Prometheus', color: 'primary' },
              { value: 'alertmanager', label: 'Alertmanager', color: 'warning' },
            ],
          }),
          column: { width: 130, align: 'center' },
          form: { value: 'prometheus', rules: [{ required: true, message: '请选择类型' }] },
        },
        url: {
          title: '监控地址',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入地址' } },
          form: { rules: [{ required: true, message: '请输入监控地址' }], component: { placeholder: '如 http://192.168.1.100:9090' } },
          column: { minWidth: 240 },
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
