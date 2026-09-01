import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { ElMessage } from 'element-plus';
import { ref, computed } from 'vue';

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  // 当前渠道类型，用于控制表单里配置字段的显隐
  const typeRef = ref('feishu');
  const isWebhookType = computed(() => ['feishu', 'dingtalk', 'wechat'].includes(typeRef.value));

  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => { form.id = row.id; return await api.UpdateObj(form); };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  const testChannel = async (row: any) => {
    const res: any = await api.TestChannel(row.id);
    if (res.code === 2000) {
      ElMessage.success(res.msg || '测试消息已发送');
    } else {
      ElMessage.error(res.msg || '发送失败');
    }
  };

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      rowHandle: {
        buttons: {
          test: {
            text: '测试发送',
            iconRight: 'Promotion',
            type: 'text',
            show: true,
            click: ({ row }: any) => testChannel(row),
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
          title: '渠道名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入渠道名称' } },
          form: { rules: [{ required: true, message: '请输入渠道名称' }], component: { placeholder: '如 运维告警飞书群' } },
          column: { minWidth: 150 },
        },
        type: {
          title: '渠道类型',
          type: 'dict-select',
          search: { show: true },
          dict: dict({
            data: [
              { value: 'feishu', label: '飞书', color: 'success' },
              { value: 'dingtalk', label: '钉钉', color: 'primary' },
              { value: 'wechat', label: '企业微信', color: 'warning' },
              { value: 'email', label: '邮箱', color: 'info' },
            ],
          }),
          column: { width: 110, align: 'center' },
          form: {
            value: 'feishu',
            valueChange: {
              immediate: true,
              handle: ({ value }: any) => { typeRef.value = value || 'feishu'; },
            },
          },
        },
        // ===== 结构化配置字段（按渠道类型动态显示，无需手写 JSON）=====
        webhook: {
          title: 'Webhook 地址',
          type: 'input',
          form: {
            show: isWebhookType,
            helper: '飞书/钉钉/企业微信机器人的 Webhook 地址，以 https:// 开头',
            component: { placeholder: '如 https://open.feishu.cn/open-apis/bot/v2/hook/xxx' },
          },
          column: { show: false },
        },
        secret: {
          title: '钉钉加签密钥',
          type: 'input',
          form: {
            show: computed(() => typeRef.value === 'dingtalk'),
            helper: '钉钉机器人若开启了「加签」安全设置才需要填（SEC 开头），未开启请留空',
            component: { placeholder: '如 SECxxxxxxxx（未开启加签则留空）' },
          },
          column: { show: false },
        },
        smtp_host: {
          title: 'SMTP 服务器',
          type: 'input',
          form: {
            show: computed(() => typeRef.value === 'email'),
            component: { placeholder: '如 smtp.163.com' },
          },
          column: { show: false },
        },
        smtp_port: {
          title: 'SMTP 端口',
          type: 'number',
          form: {
            show: computed(() => typeRef.value === 'email'),
            value: 465,
            component: { min: 1, max: 65535, placeholder: 'SSL 通常 465，非加密 25' },
          },
          column: { show: false },
        },
        smtp_username: {
          title: '发件账号',
          type: 'input',
          form: {
            show: computed(() => typeRef.value === 'email'),
            component: { placeholder: '如 your_email@example.com' },
          },
          column: { show: false },
        },
        smtp_password: {
          title: '密码 / 授权码',
          type: 'password',
          form: {
            show: computed(() => typeRef.value === 'email'),
            component: { placeholder: '邮箱 SMTP 授权码（非登录密码）', showPassword: true },
          },
          column: { show: false },
        },
        smtp_to: {
          title: '收件人',
          type: 'input',
          form: {
            show: computed(() => typeRef.value === 'email'),
            helper: '多个收件人用英文逗号分隔',
            component: { placeholder: '如 a@163.com, b@163.com' },
          },
          column: { show: false },
        },
        // ===== 配置汇总（列表展示用，不参与表单编辑）=====
        config: {
          title: '渠道配置',
          form: { show: false, submit: false },
          column: {
            minWidth: 260,
            showOverflowTooltip: true,
            formatter: ({ row }: any) => {
              const cfg = row.config || {};
              if (row.type === 'email') {
                const to = (cfg.to_addrs || []).join(', ');
                return `${cfg.smtp_host || '-'}:${cfg.smtp_port || ''} → ${to || '-'}`;
              }
              const w = cfg.webhook || '';
              if (row.type === 'dingtalk' && cfg.secret) return `${w}（加签）`;
              return w || '-';
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
