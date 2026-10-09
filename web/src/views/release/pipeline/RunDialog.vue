<template>
	<el-dialog
		v-model="show"
		:title="`发起执行 · ${pipeline?.name || ''}`"
		width="640px"
		:close-on-click-modal="false"
		@open="onOpen"
	>
		<el-alert
			type="warning"
			:closable="false"
			show-icon
			title="这会真的执行：会 SSH 到目标机、可能触发 Jenkins 构建、可能重启服务"
			description="执行由「执行记录」页面驱动推进；关掉浏览器会停在当前节点。请确认参数与环境无误。"
			class="mb12"
		/>

		<el-form v-if="defs.length" label-width="140px">
			<el-form-item v-for="p in defs" :key="p.key" :label="p.label || p.key" :required="p.required">
				<el-input v-model="values[p.key]" :placeholder="p.default || ''" clearable />
				<div class="hint">
					占位符 <code>{{ placeholder(p.key) }}</code>
					<span v-if="p.default">；默认值 {{ p.default }}</span>
				</div>
			</el-form-item>
		</el-form>
		<el-alert v-else type="info" :closable="false" show-icon title="该流水线没有定义运行时参数，直接发起即可" />

		<template #footer>
			<el-button @click="show = false">取消</el-button>
			<el-button type="primary" :loading="starting" @click="start">确认发起</el-button>
		</template>
	</el-dialog>
</template>

<script lang="ts">
import { defineComponent, ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import * as api from './api';

export default defineComponent({
	name: 'ReleaseRunDialog',
	props: {
		modelValue: { type: Boolean, default: false },
		pipeline: { type: Object, default: null },
	},
	emits: ['update:modelValue', 'started'],
	setup(props, { emit }) {
		const show = computed({
			get: () => props.modelValue,
			set: (v: boolean) => emit('update:modelValue', v),
		});

		const starting = ref(false);
		const values = ref<Record<string, string>>({});
		const defs = computed<any[]>(() => props.pipeline?.params || []);

		/**
		 * 占位符文本在脚本里拼，不在模板里拼。
		 * ★ 模板里写 `{{ '{{' + key + '}}' }}` 会被 Vue 编译器在**字符串内部的 `}}`**
		 *   处截断，直接编译报错 —— 这类"和模板语法撞车"的字符串一律挪到 script。
		 */
		const placeholder = (key: string) => `{{${key}}}`;

		function onOpen() {
			const init: Record<string, string> = {};
			defs.value.forEach((p: any) => {
				init[p.key] = p.default ?? '';
			});
			values.value = init;
		}

		async function start() {
			const missing = defs.value.filter((p: any) => p.required && !String(values.value[p.key] ?? '').trim());
			if (missing.length) {
				ElMessage.error('必填参数未填：' + missing.map((p: any) => p.label || p.key).join('、'));
				return;
			}
			starting.value = true;
			try {
				const resp: any = await api.RunPipeline(props.pipeline.id, values.value);
				const data = resp?.data?.data || resp?.data || {};
				ElMessage.success('已发起执行');
				show.value = false;
				emit('started', data.id);
			} finally {
				starting.value = false;
			}
		}

		return { show, starting, values, defs, placeholder, onOpen, start };
	},
});
</script>

<style scoped>
.mb12 {
	margin-bottom: 12px;
}
.hint {
	color: #909399;
	font-size: 12px;
	line-height: 1.6;
}
.hint code {
	background: #f5f7fa;
	padding: 1px 5px;
	border-radius: 3px;
	font-family: Consolas, 'Courier New', monospace;
}
</style>
