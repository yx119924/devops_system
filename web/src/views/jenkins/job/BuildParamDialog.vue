<!--
  触发构建：参数填写弹窗

  把原来「手填 JSON」换成 Jenkins 原生那样的勾选/下拉/填写表单。

  候选值三级来源（后端已算好，见 backend/dvadmin/jenkins/views/jenkins.py 的 job_params）：
    json_api        Jenkins 静态 Choice 参数，直接给 choices
    config_static   参数脚本里写死的列表（生产环境的 DEPLOY_HOST 就是 8 项复选框多选）
    cascade_static  级联参数：随被引用参数变化，这里本地重算，不再发请求
    build_history   脚本里算不出来的（如实时查 GitLab 分支）→ 用最近构建实际用过的值

  任何一步失败都会退回原来的 JSON 输入框，保证不会因为读不到参数就发不了版。
-->
<template>
	<el-dialog
		:model-value="modelValue"
		:title="`触发构建 - ${job}`"
		width="680px"
		top="6vh"
		destroy-on-close
		@update:model-value="onVisibleChange"
		@open="onOpen"
	>
		<div v-loading="loading" element-loading-text="正在读取 Jenkins 参数定义...">
			<template v-if="!loading">
				<el-alert
					v-if="loadError"
					type="warning"
					:closable="false"
					show-icon
					:title="loadError"
					description="已自动切换为高级模式：可直接填写 JSON 参数，留空则做普通构建"
					class="mb12"
				/>

				<!-- 高级模式（也是加载失败时的兜底）：保留原来的 JSON 输入 -->
				<template v-if="advanced || !params.length">
					<el-input v-model="jsonText" type="textarea" :rows="5" placeholder='{"BRANCH":"dev"}（可留空）' />
					<p class="hint" v-if="!params.length && !loadError">该 Job 没有参数化构建配置，直接点「触发构建」即可</p>
				</template>

				<!-- 动态表单 -->
				<el-form v-else label-position="top" class="param-form">
					<el-form-item v-for="p in params" :key="p.name">
						<template #label>
							<span class="p-name">{{ p.name }}</span>
							<span v-if="p.cascade_on" class="p-tag cascade">随 {{ p.cascade_on.join('、') }} 变化</span>
							<span v-else-if="p.source === 'build_history'" class="p-tag recent">最近用过</span>
							<span v-else-if="p.degraded" class="p-tag warn">需手填</span>
							<span v-else-if="p.multiple" class="p-tag multi">可多选</span>
						</template>

						<!-- 复选框多选 -->
						<el-checkbox-group v-if="p.type === 'checkbox'" v-model="form[p.name]" class="cb-group">
							<el-checkbox v-for="c in choicesOf(p)" :key="c" :value="c">{{ c }}</el-checkbox>
						</el-checkbox-group>
						<div v-if="p.type === 'checkbox'" class="hint-row">
							<span>共 {{ choicesOf(p).length }} 项，已选 {{ (form[p.name] || []).length }} 项</span>
							<el-button link type="primary" size="small" @click="form[p.name] = choicesOf(p).slice()">全选</el-button>
							<el-button link type="primary" size="small" @click="form[p.name] = []">清空</el-button>
						</div>

						<!-- 单选按钮组 -->
						<el-radio-group v-else-if="p.type === 'radio'" v-model="form[p.name]">
							<el-radio v-for="c in choicesOf(p)" :key="c" :value="c">{{ c }}</el-radio>
						</el-radio-group>

						<!-- 下拉（支持多选 / 允许自由输入） -->
						<el-select
							v-else-if="p.type === 'choice'"
							v-model="form[p.name]"
							:multiple="!!p.multiple"
							:allow-create="!!p.allow_create"
							:filterable="choicesOf(p).length > 8 || !!p.allow_create"
							clearable
							default-first-option
							style="width: 100%"
							:placeholder="p.allow_create ? '选择最近用过的值，或直接输入新的' : '请选择'"
						>
							<el-option v-for="c in choicesOf(p)" :key="c" :label="c" :value="c" />
						</el-select>

						<!-- 开关 -->
						<el-switch v-else-if="p.type === 'boolean'" v-model="form[p.name]" />

						<!-- 文本 / 多行文本 / 密码 -->
						<el-input
							v-else
							v-model="form[p.name]"
							:type="inputType(p)"
							:rows="p.type === 'text' ? 2 : undefined"
							:show-password="p.type === 'password'"
							placeholder="请输入"
						/>

						<!-- 纯文本参数（TAG / 版本号）的历史值：点一下就填进去，也能自己改 -->
						<p
							v-if="(p.type === 'text' || p.type === 'string') && p.recent && p.recent.length"
							class="p-recent"
						>
							<span>最近用过：</span>
							<el-button
								v-for="r in p.recent.slice(0, 3)"
								:key="r"
								link
								type="primary"
								size="small"
								@click="form[p.name] = r"
							>{{ r }}</el-button>
						</p>

						<p v-if="p.description" class="p-desc" :title="p.description">{{ p.description }}</p>
					</el-form-item>
				</el-form>
			</template>
		</div>

		<template #footer>
			<div class="dlg-footer">
				<el-checkbox v-model="advanced" size="small" :disabled="!params.length">高级模式（直接填 JSON）</el-checkbox>
				<div>
					<el-button @click="onVisibleChange(false)">取消</el-button>
					<el-button type="primary" :loading="submitting" @click="onSubmit">触发构建</el-button>
				</div>
			</div>
		</template>
	</el-dialog>
</template>

<script lang="ts">
import { defineComponent, ref, reactive, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { GetJobParams } from './api';

export default defineComponent({
	name: 'JenkinsBuildParamDialog',
	props: {
		modelValue: { type: Boolean, default: false },
		serverId: { type: Number, default: null },
		job: { type: String, default: '' },
		submitting: { type: Boolean, default: false },
		// 父组件已经探测过一次参数了（可能失败），直接把结果带进来：
		// 非空时本组件不再重复请求，立刻进高级模式（JSON 兜底），
		// 免得用户在同一个超时上白等两次。
		preloadError: { type: String, default: '' },
	},
	emits: ['update:modelValue', 'confirm'],
	setup(props, { emit }) {
		const loading = ref(false);
		const loadError = ref('');
		const params = ref<any[]>([]);
		const form = reactive<Record<string, any>>({});
		const advanced = ref(false);
		const jsonText = ref('');

		const storeKey = () => `jenkins_build_params::${props.serverId}::${props.job}`;

		/** el-dialog 的显隐回写。写成方法而不是模板里的内联箭头函数，
		 *  免得在模板表达式里出现 TS 类型标注（不同编译链对它的处理不一致）。 */
		const onVisibleChange = (v: boolean) => emit('update:modelValue', v);

		/** 纯文本参数的输入框形态：多行 / 密码（密码要 type=password，EP 的
		 *  show-password 只在 type 为 password 时才渲染那只"眼睛"）/ 单行。 */
		const inputType = (p: any) => {
			if (p.type === 'text') return 'textarea';
			if (p.type === 'password') return 'password';
			return 'text';
		};

		/** 某参数当前的候选值；级联参数按被引用参数的当前值本地重算 */
		const choicesOf = (p: any) => {
			if (!p.cascade_on || !p.cascade_rules?.length) return p.choices || [];
			for (const rule of p.cascade_rules) {
				const hit = Object.keys(rule.when).every((k) => {
					const cur = ([] as any[]).concat(form[k] ?? []);
					return (rule.when[k] || []).some((v: string) => cur.includes(v));
				});
				if (hit) return rule.choices || [];
			}
			return p.cascade_else?.length ? p.cascade_else : p.choices || [];
		};

		/** 用 Jenkins 的默认值预填表单 */
		const applyDefaults = () => {
			params.value.forEach((p: any) => {
				const list = choicesOf(p);
				const def = p.default == null ? '' : String(p.default);
				if (p.type === 'checkbox' || p.multiple) {
					const parts = def.split(',').map((s) => s.trim()).filter(Boolean);
					form[p.name] = list.length ? parts.filter((x) => list.includes(x)) : parts;
				} else if (p.type === 'boolean') {
					form[p.name] = def.toLowerCase() === 'true';
				} else if (p.type === 'choice' || p.type === 'radio') {
					const usable = def && (!list.length || list.includes(def));
					form[p.name] = usable ? def : list[0] || def || '';
				} else {
					form[p.name] = def;
				}
			});
		};

		/** 记住同一次会话里填过的值，反复发版不用重复填 */
		const restoreSaved = () => {
			try {
				const raw = sessionStorage.getItem(storeKey());
				if (!raw) return;
				const obj = JSON.parse(raw);
				params.value.forEach((p: any) => {
					const v = obj[p.name];
					if (v === undefined) return;
					const list = choicesOf(p);
					if (p.type === 'checkbox' || p.multiple) {
						const arr = ([] as any[]).concat(v);
						form[p.name] = list.length && !p.allow_create ? arr.filter((x) => list.includes(x)) : arr;
					} else if (p.allow_create || !list.length || list.includes(v)) {
						form[p.name] = v;
					}
				});
			} catch {
				/* sessionStorage 不可用就忽略 */
			}
		};

		const saveForm = () => {
			try {
				sessionStorage.setItem(storeKey(), JSON.stringify(form));
			} catch {
				/* 忽略 */
			}
		};

		const onOpen = async () => {
			advanced.value = false;
			loadError.value = '';
			jsonText.value = '';
			params.value = [];
			Object.keys(form).forEach((k) => delete form[k]);
			if (!props.serverId || !props.job) return;

			// 父组件探测参数时已经失败过 → 直接兜底，不再发第二次请求
			if (props.preloadError) {
				loadError.value = props.preloadError;
				advanced.value = true;
				return;
			}

			loading.value = true;
			try {
				const res: any = await GetJobParams(props.serverId, props.job);
				if (res.code !== 2000) {
					loadError.value = res.msg || '读取参数定义失败';
					advanced.value = true;
					return;
				}
				params.value = res.data?.params || [];
				applyDefaults();
				restoreSaved();
			} catch (e: any) {
				const msg = String(e?.message || '');
				loadError.value = msg.includes('timeout') ? '读取参数定义超时（Jenkins 响应较慢）' : msg || '读取参数定义失败';
				advanced.value = true;
			} finally {
				loading.value = false;
			}
		};

		// 被引用参数变了 → 级联参数里失效的选项自动收敛
		watch(
			form,
			() => {
				params.value.forEach((p: any) => {
					if (!p.cascade_on) return;
					const list = choicesOf(p);
					const arr = ([] as any[]).concat(form[p.name] ?? []);
					if (!arr.some((v) => v && !list.includes(v))) return;
					form[p.name] = p.multiple ? arr.filter((v: string) => list.includes(v)) : list[0] || '';
				});
			},
			{ deep: true }
		);

		const onSubmit = () => {
			const payload: Record<string, any> = {};
			if (advanced.value || !params.value.length) {
				const raw = jsonText.value.trim();
				if (raw) {
					try {
						Object.assign(payload, JSON.parse(raw));
					} catch {
						ElMessage.error('参数不是合法 JSON，请检查后重试');
						return;
					}
				}
			} else {
				const missing: string[] = [];
				params.value.forEach((p: any) => {
					let v = form[p.name];
					if (p.type === 'checkbox' || p.multiple) {
						// 多选按逗号拼接——Active Choices 的默认分隔符，Jenkins 侧就是这么收的
						v = ([] as any[]).concat(v ?? []).filter(Boolean).join(',');
					} else if (p.type === 'boolean') {
						v = !!v;
					} else if (p.type === 'choice' || p.type === 'radio') {
						if (!v) missing.push(p.name);
					} else if (!String(v ?? '').trim() && /必填|需要填写/.test(p.description || '')) {
						// Jenkins 的 TextParameter 允许空值，只有描述里明确要求填的才拦
						missing.push(p.name);
					}
					payload[p.name] = v;
				});
				if (missing.length) {
					ElMessage.warning(`请先填写：${missing.join('、')}`);
					return;
				}
			}
			saveForm();
			emit('confirm', payload);
		};

		return {
			loading, loadError, params, form, advanced, jsonText,
			choicesOf, inputType, onOpen, onSubmit, onVisibleChange,
		};
	},
});
</script>

<style scoped>
.mb12 {
	margin-bottom: 12px;
}
.param-form :deep(.el-form-item) {
	margin-bottom: 18px;
}
.p-name {
	font-weight: 500;
}
.p-tag {
	margin-left: 8px;
	padding: 1px 6px;
	border-radius: 4px;
	font-size: 11px;
	font-weight: 400;
	line-height: 18px;
}
.p-tag.cascade {
	background: #e6f1fb;
	color: #185fa5;
}
.p-tag.recent {
	background: #faeeda;
	color: #854f0b;
}
.p-tag.warn {
	background: #fcebeb;
	color: #a32d2d;
}
.p-tag.multi {
	background: #e1f5ee;
	color: #0f6e56;
}
.cb-group {
	display: flex;
	flex-wrap: wrap;
	gap: 4px 16px;
}
.hint-row {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: 4px;
	font-size: 12px;
	color: #909399;
}
.p-desc {
	margin: 4px 0 0;
	font-size: 12px;
	line-height: 1.6;
	color: #909399;
	white-space: pre-line;
	max-height: 72px;
	overflow: auto;
}
.p-recent {
	margin: 4px 0 0;
	font-size: 12px;
	line-height: 1.8;
	color: #909399;
}
.p-recent :deep(.el-button) {
	height: auto;
	padding: 0 2px;
	font-size: 12px;
	font-family: inherit;
}
.hint {
	margin: 6px 0 0;
	font-size: 12px;
	color: #909399;
}
.dlg-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}
</style>
