<template>
	<el-dialog v-model="visible" :title="title" width="720px" top="7vh" destroy-on-close @closed="onClosed">
		<div class="sg-tip">
			服务器 <b>{{ server?.hostname }}</b><span class="ip">（{{ server?.ip }}）</span>
			默认只对<b>运维 / 管理员</b>可见。下面列出的是额外授权给<b>其他角色或指定用户</b>的访问权限：
			需要"能下发命令 / 开终端"就选<b>可操作</b>，只需要"能看见资产台账"就选<b>只读</b>。
		</div>

		<el-table :data="rows" border size="small" v-loading="loading" empty-text="暂无授权（当前仅运维 / 管理员可见）">
			<el-table-column label="授权对象类型" width="140" align="center">
				<template #default="{ row }">
					<el-select v-model="row.type" style="width: 110px" @change="onTypeChange(row)">
						<el-option label="角色" value="role" />
						<el-option label="用户" value="user" />
					</el-select>
				</template>
			</el-table-column>
			<el-table-column label="授权对象" min-width="220">
				<template #default="{ row }">
					<el-select
						v-model="row.target"
						filterable
						placeholder="请选择"
						style="width: 100%"
						:loading="optionsLoading"
					>
						<el-option
							v-for="o in candidates(row.type)"
							:key="o.value"
							:label="o.label"
							:value="o.value"
						/>
					</el-select>
				</template>
			</el-table-column>
			<el-table-column label="授权级别" width="150" align="center">
				<template #default="{ row }">
					<el-select v-model="row.level" style="width: 120px">
						<el-option label="只读" value="read" />
						<el-option label="可操作" value="write" />
					</el-select>
				</template>
			</el-table-column>
			<el-table-column label="操作" width="80" align="center">
				<template #default="{ $index }">
					<el-button type="danger" link @click="rows.splice($index, 1)">删除</el-button>
				</template>
			</el-table-column>
		</el-table>

		<div class="sg-actions">
			<el-button link type="primary" @click="addRow">+ 添加一行</el-button>
			<span class="sg-note">保存会<b>整体覆盖</b>该服务器的授权，未在表中的对象将被收回。</span>
		</div>

		<template #footer>
			<el-button @click="visible = false">取消</el-button>
			<el-button type="primary" :loading="saving" @click="save">保存</el-button>
		</template>
	</el-dialog>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { GetGrantOptions, GetGrants, SetGrants } from '../api';

export default defineComponent({
	name: 'serverGrantDialog',
	props: {
		modelValue: { type: Boolean, default: false },
		server: { type: Object, default: null },
	},
	emits: ['update:modelValue', 'saved'],
	setup(props, { emit }) {
		const visible = computed({
			get: () => props.modelValue,
			set: (v: boolean) => emit('update:modelValue', v),
		});

		const title = computed(() =>
			props.server ? `资产授权 — ${props.server.hostname}` : '资产授权'
		);

		const loading = ref(false);
		const saving = ref(false);
		const optionsLoading = ref(false);
		const roles = ref<any[]>([]);
		const users = ref<any[]>([]);
		// 每行：{ type: 'role'|'user', target: id, level: 'read'|'write' }
		const rows = ref<any[]>([]);

		const candidates = (type: string) => {
			if (type === 'user') {
				return users.value.map((u) => ({
					value: u.id,
					label: u.name ? `${u.name}（${u.username}）` : u.username,
				}));
			}
			return roles.value.map((r) => ({ value: r.id, label: r.name }));
		};

		const loadOptions = async () => {
			if (roles.value.length || users.value.length) return;
			optionsLoading.value = true;
			try {
				const res: any = await GetGrantOptions();
				if (res.code === 2000) {
					roles.value = res.data?.roles || [];
					users.value = res.data?.users || [];
				} else {
					ElMessage.error(res.msg || '获取授权对象列表失败');
				}
			} finally {
				optionsLoading.value = false;
			}
		};

		const loadGrants = async () => {
			if (!props.server?.id) return;
			loading.value = true;
			try {
				const res: any = await GetGrants(props.server.id);
				if (res.code === 2000) {
					const list = res.data?.results ?? res.data ?? [];
					rows.value = list.map((g: any) => ({
						type: g.role ? 'role' : 'user',
						target: g.role || g.user,
						level: g.level || 'read',
					}));
				}
			} finally {
				loading.value = false;
			}
		};

		const onTypeChange = (row: any) => {
			row.target = null; // 类型换了，原对象不再适用
		};

		const addRow = () => {
			rows.value.push({ type: 'role', target: null, level: 'read' });
		};

		const save = async () => {
			if (!props.server?.id) return;
			const payload: any[] = [];
			const seen = new Set<string>();
			for (let i = 0; i < rows.value.length; i++) {
				const r = rows.value[i];
				if (!r.target) {
					ElMessage.warning(`第 ${i + 1} 行还没选择授权对象`);
					return;
				}
				// 前端先做一次去重：同一对象同一行只留一条，避免后端报"重复"
				const key = `${r.type}:${r.target}`;
				if (seen.has(key)) {
					ElMessage.warning(`第 ${i + 1} 行的授权对象重复，请删除重复项`);
					return;
				}
				seen.add(key);
				payload.push({ [r.type]: r.target, level: r.level || 'read' });
			}
			saving.value = true;
			try {
				const res: any = await SetGrants(props.server.id, payload);
				if (res.code === 2000) {
					ElMessage.success(res.msg || '授权已保存');
					emit('saved');
					visible.value = false;
				} else {
					ElMessage.error(res.msg || '保存失败');
				}
			} finally {
				saving.value = false;
			}
		};

		const onClosed = () => {
			rows.value = [];
		};

		watch(
			() => props.modelValue,
			async (v) => {
				if (!v) return;
				await loadOptions();
				await loadGrants();
			}
		);

		return {
			visible, title, loading, saving, optionsLoading, roles, users, rows,
			candidates, onTypeChange, addRow, save, onClosed,
		};
	},
});
</script>

<style scoped>
.sg-tip {
	font-size: 13px;
	color: #606266;
	line-height: 1.7;
	margin-bottom: 12px;
	padding: 10px 12px;
	background: #f5f8ff;
	border-radius: 6px;
}
.sg-tip .ip {
	color: #909399;
}
.sg-actions {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-top: 10px;
}
.sg-note {
	font-size: 12px;
	color: #c0c4cc;
}
</style>
