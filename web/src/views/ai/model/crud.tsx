import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { ElMessage, ElMessageBox } from 'element-plus';
import { BtnPermissionStore } from '/@/stores/btnPermission';

/** 转义，避免把后端返回的文本当 HTML 渲染 */
const esc = (v: any) =>
  String(v === null || v === undefined ? '' : v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

export const createCrudOptions = function ({ crudExpose, context }: CreateCrudOptionsProps): CreateCrudOptionsRet {
  const pageRequest = async (query: UserPageQuery) => await api.GetList(query);
  const editRequest = async ({ form, row }: EditReq) => {
    form.id = row.id;
    // API Key 留空 = 保留原值（后端 validate 里处理），这里不做拦截
    return await api.UpdateObj(form);
  };
  const delRequest = async ({ row }: DelReq) => await api.DelObj(row.id);
  const addRequest = async ({ form }: AddReq) => await api.AddObj(form);

  const btnStore = BtnPermissionStore();
  const hasAuth = (code: string) => (btnStore.data || []).includes(code);

  // ---------------- 测试连接 ----------------
  // 真实请求大模型，耗时可能到几十秒；前端全局超时 5s，已在 api.ts 里把该接口放宽到 120s
  const testProvider = async (row: any) => {
    if (!row.has_api_key) {
      ElMessage.warning('该配置还没保存 API Key，请先「编辑」填入后再测试');
      return;
    }
    const tip = ElMessage({
      message: `正在请求 ${row.model}，最长等待 ${row.timeout || 60} 秒…`,
      type: 'info',
      duration: 0,
    });

    let res: any = null;
    try {
      res = await api.TestProvider(row.id);
    } catch (e: any) {
      tip.close();
      // ★★ 这里必须**优先取 `e.msg`**，只取 `e.message` 是错的。
      //   `web/src/utils/service.ts` 的响应拦截器对「非 2000」的收尾是
      //   `Promise.reject(dataAxios)` —— reject 出去的是**后端返回的整个对象**，
      //   上面带的是后端字段 `msg`，**根本没有 `message`**。
      //   旧代码只取 e.message → 恒 undefined → 退化成下面的兜底文案，
      //   于是「模型名不对（400）」「API Key 无效（401）」被说成「网络不通或超时」，
      //   排查方向被整体带偏（2026-09-23 实际踩过：业务错误被显示成网络问题）。
      //   注意：业务错误那条红条拦截器已经弹过一次，这里补一个可复制的详情弹窗。
      const bizMsg = e && typeof e === 'object' ? e.msg || '' : '';
      const netMsg = e?.message || '';
      const detail = bizMsg || netMsg;
      if (detail) {
        ElMessageBox.alert(
          `<div style="font-size:13px;line-height:1.9;word-break:break-all">${esc(detail)}</div>`,
          bizMsg ? '连接测试失败' : '请求未完成',
          { dangerouslyUseHTMLString: true, type: 'error', confirmButtonText: '知道了' }
        );
      } else {
        // 到这儿才是真的「拿不到任何错误信息」——这时才提网络/超时
        ElMessage.error(
          `连接测试未完成：请确认服务器能访问 ${row.base_url}，或等待已超过 ${row.timeout || 60} 秒超时`
        );
      }
      return;
    }
    tip.close();

    if (res && res.code === 2000) {
      const d = res.data || {};
      ElMessageBox.alert(
        `<div style="font-size:13px;line-height:2;word-break:break-all">
           <b>接口地址：</b>${esc(row.base_url)}<br/>
           <b>模型回显：</b>${esc(d.model || row.model)}<br/>
           <b>模型回答：</b>${esc(d.reply || 'OK')}<br/>
           <b>响应延迟：</b>${d.latency != null ? esc(Number(d.latency).toFixed(2)) + ' 秒' : '-'}<br/>
           <b>消耗 token：</b>${d.tokens != null ? esc(d.tokens) : '-'}
         </div>`,
        '连接成功',
        { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
      );
    } else {
      ElMessageBox.alert(
        `<div style="font-size:13px;line-height:1.9;word-break:break-all">${esc(res && res.msg ? res.msg : '连接失败')}</div>`,
        '连接失败',
        { dangerouslyUseHTMLString: true, type: 'error', confirmButtonText: '知道了' }
      );
    }
  };

  // ---------------- 设为默认 ----------------
  const setDefault = async (row: any) => {
    try {
      const res: any = await api.SetDefault(row.id);
      if (res.code === 2000) {
        ElMessage.success(res.msg || '已设为默认供应商');
        crudExpose.doRefresh();
      } else {
        ElMessage.error(res.msg || '设置失败');
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '设置失败');
    }
  };

  return {
    crudOptions: {
      request: { pageRequest, addRequest, editRequest, delRequest },
      actionbar: { buttons: { add: { show: hasAuth('ai_provider:Create') } } },
      rowHandle: {
        fixed: 'right',
        width: 300,
        buttons: {
          edit: { show: hasAuth('ai_provider:Update') },
          remove: { show: hasAuth('ai_provider:Delete') },
          test: {
            text: '测试连接',
            type: 'text',
            order: -2,
            show: true,
            click: ({ row }: any) => testProvider(row),
          },
          setDefault: {
            text: '设为默认',
            type: 'text',
            order: -1,
            show: true,
            click: ({ row }: any) => setDefault(row),
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
          title: '配置名称',
          type: 'input',
          search: { show: true, component: { placeholder: '请输入配置名称' } },
          form: {
            rules: [{ required: true, message: '请输入配置名称' }],
            component: { placeholder: '如 我的 DeepSeek' },
            helper: '★ 配置只对你自己可见（每人各配各的 Key），同名冲突只在你自己名下判断',
          },
          column: { minWidth: 150 },
        },
        provider_type: {
          title: '接口类型',
          type: 'dict-select',
          search: { show: true },
          dict: dict({
            data: [{ value: 'openai_compat', label: 'OpenAI 兼容', color: 'primary' }],
          }),
          column: { width: 120, align: 'center' },
          form: { value: 'openai_compat' },
        },
        base_url: {
          title: '接口地址',
          type: 'input',
          search: { show: true, component: { placeholder: '按地址搜索' } },
          form: {
            rules: [{ required: true, message: '请输入接口地址' }],
            component: { placeholder: 'https://api.deepseek.com/v1' },
            helper: 'DeepSeek 官方填 https://api.deepseek.com/v1；末尾不要带斜杠，后端会自动去掉',
          },
          column: { minWidth: 210, showOverflowTooltip: true },
        },
        model: {
          title: '模型名称',
          type: 'input',
          search: { show: true, component: { placeholder: '按模型名搜索' } },
          form: {
            rules: [{ required: true, message: '请输入模型名称' }],
            component: { placeholder: 'deepseek-flash' },
            helper:
              'DeepSeek 现役：deepseek-flash（快而省）／ deepseek-v4-pro（重推理）。' +
              '★ 模型名区分大小写，写成 DeepSeek-chat 会直接报 400；' +
              'deepseek-chat / deepseek-reasoner 已于 2026-07-24 被官方弃用',
          },
          column: { minWidth: 160 },
        },
        api_key: {
          title: 'API Key',
          type: 'password',
          form: {
            component: { placeholder: 'sk-xxxxxxxx', showPassword: true },
            helper:
              '★ 只写不读：保存后不会再回显明文；编辑时留空 = 保留原来的 Key。' +
              '★ 用自己的 Key（BYOK）：平台不提供公共额度，这里填谁的 Key 就消耗谁的额度，别人看不到也用不到',
          },
          column: {
            width: 110,
            align: 'center',
            formatter: ({ row }: any) => (row.has_api_key ? '已配置' : '未配置'),
          },
        },
        temperature: {
          title: '温度',
          type: 'number',
          form: {
            value: 0.2,
            component: { min: 0, max: 2, step: 0.1, precision: 1 },
            helper: '0~2。运维问答建议 0.1~0.3，越低越稳定',
          },
          column: { width: 80, align: 'center' },
        },
        max_tokens: {
          title: '最大输出',
          type: 'number',
          form: {
            value: 2048,
            component: { min: 64, max: 32768, step: 256 },
            helper: '64~32768，单次回答的最大长度',
          },
          column: { width: 100, align: 'center' },
        },
        enable_thinking: {
          title: '深度思考',
          type: 'switch',
          form: {
            value: false,
            helper:
              '仅对 DeepSeek 系列生效。开启后模型先输出思考过程（更严谨，但更慢、更耗 token）；' +
              '关闭时会显式跳过思考，运维问答更快更省 —— 建议保持关闭',
          },
          column: { width: 100, align: 'center' },
        },
        timeout: {
          title: '超时(秒)',
          type: 'number',
          form: {
            value: 60,
            component: { min: 5, max: 600, step: 5 },
            helper: '5~600。大模型响应慢，建议 60~120',
          },
          column: { width: 90, align: 'center' },
        },
        enabled: {
          title: '启用',
          type: 'switch',
          // ★ 暂时不开「按启用状态搜索」：平台已知问题 —— 布尔筛选不认小写
          //   true/false（?enabled=true 会返回业务码 4000）。修好后再把
          //   search: { show: true } 加回来。
          form: { value: true },
          column: { width: 80, align: 'center' },
        },
        is_default: {
          title: '默认',
          type: 'switch',
          // 同上，先不开布尔搜索
          form: {
            value: false,
            helper: '设为默认后，只影响你自己名下其他配置的默认标记（别人的默认不受影响）',
          },
          column: { width: 80, align: 'center' },
        },
        description: {
          title: '备注',
          type: 'input',
          form: { component: { placeholder: '可选，如：生产用 / 测试用' } },
          column: { minWidth: 140, showOverflowTooltip: true },
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
