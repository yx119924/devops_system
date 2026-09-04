import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet, compute } from '@fast-crud/fast-crud';
import { BtnPermissionStore } from '/@/stores/btnPermission';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  const btnStore = BtnPermissionStore();
  const hasAuth = (code: string) => (btnStore.data || []).includes(code);

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      actionbar: { buttons: { add: { show: hasAuth('server:Create') } } },
      rowHandle: {
        buttons: {
          edit: { show: compute(() => hasAuth('server:Update')) },
          remove: { show: compute(() => hasAuth('server:Delete')) },
          ssh: {
            text: '终端',
            iconRight: 'Monitor',
            type: 'text',
            show: true,
            click: ({ row }: any) => {
              context.openSsh(row);
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
        hostname: {
          title: '主机名',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入主机名' } },
          form: { rules: [{ required: true, message: '请输入主机名' }], component: { placeholder: '请输入主机名' } },
          column: { minWidth: 130 },
        },
        ip: {
          title: '主管理IP',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入管理IP' } },
          form: { rules: [{ required: true, message: '请输入主管理IP' }], component: { placeholder: '如 192.168.1.10' } },
          column: { minWidth: 130 },
        },
        extra_ips: {
          title: '其他内网IP',
          type: 'input',
          form: { component: { placeholder: '多网卡其他内网IP，逗号分隔' } },
          column: { minWidth: 150, show: false },
        },
        idc: {
          title: '机房',
          type: 'dict-select',
          dict: dict({
            url: '/api/cmdb/idc/all/',
            value: 'id',
            label: 'name',
          }),
          column: { minWidth: 100, formatter: ({ row }: any) => row.idc_name },
          form: { component: { placeholder: '请选择机房', clearable: true } },
        },
        environment: {
          title: '环境',
          type: 'dict-select',
          dict: dict({
            url: '/api/cmdb/environment/all/',
            value: 'id',
            label: 'name',
          }),
          column: { minWidth: 90, formatter: ({ row }: any) => row.environment_name },
          form: { component: { placeholder: '请选择环境', clearable: true } },
        },
        business_line: {
          title: '业务线',
          type: 'dict-select',
          dict: dict({
            url: '/api/cmdb/business_line/all/',
            value: 'id',
            label: 'name',
          }),
          column: { minWidth: 100, formatter: ({ row }: any) => row.business_line_name },
          form: { component: { placeholder: '请选择业务线', clearable: true } },
        },
        deploy_content: {
          title: '部署内容',
          type: 'input',
          search: { show: true },
          form: { component: { placeholder: '如 nginx / mysql' } },
          column: { minWidth: 130 },
        },
        os: {
          title: '操作系统',
          type: 'input',
          form: { component: { placeholder: '如 CentOS 7.9 / Ubuntu 24.04' } },
          column: { minWidth: 150, show: false },
        },
        cpu: {
          title: 'CPU核数',
          type: 'number',
          column: { width: 90, align: 'center', show: false },
          form: { component: { min: 0 } },
        },
        memory: {
          title: '内存(GB)',
          type: 'number',
          column: { width: 90, align: 'center', show: false },
          form: { component: { min: 0 } },
        },
        disk: {
          title: '磁盘',
          type: 'input',
          form: { component: { placeholder: '如 100G SSD' } },
          column: { minWidth: 110, show: false },
        },
        ssh_port: {
          title: 'SSH端口',
          type: 'number',
          column: { width: 90, align: 'center', show: false },
          form: { value: 22, component: { min: 1, max: 65535 } },
        },
        serial_number: {
          title: '设备序列号',
          type: 'input',
          form: { component: { placeholder: '设备序列号' } },
          column: { minWidth: 130, show: false },
        },
        purchase_date: {
          title: '采购日期',
          type: 'date',
          form: { component: { valueFormat: 'YYYY-MM-DD' } },
          column: { minWidth: 120, show: false },
        },
        warranty_expiry: {
          title: '维保到期',
          type: 'date',
          form: { component: { valueFormat: 'YYYY-MM-DD' } },
          column: { minWidth: 120, show: false },
        },
        status: {
          title: '状态',
          type: 'dict-select',
          search: { show: true },
          dict: dict({
            data: [
              { value: 'online', label: '在线', color: 'success' },
              { value: 'offline', label: '离线', color: 'info' },
              { value: 'maintenance', label: '维护中', color: 'warning' },
              { value: 'offline_shelf', label: '已下架', color: 'danger' },
            ],
          }),
          column: { width: 90, align: 'center' },
          form: { value: 'online' },
        },
        tags: {
          title: '标签',
          type: 'input',
          form: { component: { placeholder: '标签，逗号分隔' } },
          column: { minWidth: 120, show: false },
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
