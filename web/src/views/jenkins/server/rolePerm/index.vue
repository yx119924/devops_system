<template>
	<el-dialog v-model="visible" :title="title" width="860px" top="7vh" destroy-on-close @closed="onClosed">
		<div class="rp-tip">
			Jenkins 的 Job 按<b>顶层目录</b>组织，下层还有子目录。
			<template v-if="topOptions.length">
				已实时读取到 <b>{{ topOptions.length }}</b> 个顶层目录 / Job。
			</template>
			<template v-else-if="foldersError">
				<span class="rp-warn">实时读取目录失败：{{ foldersError }}</span>
				—— 请在下拉框里<b>手工输入</b>目录后回车。
			</template>
			<b>授权到某一层目录即可，其下层默认可见</b>。未在下面的角色一律<b>看不到任何 Job</b>（默认拒绝）。
		</div>

		<el-table :data="rows" border size="small" v-loading="loading" empty-text="没有可配置的角色">
			<el-table-column label="角色" width="150">
				<template #default="{ row }">
					<span class="rp-role">{{ row.role_name }}</span>
					<span class="rp-key">{{ row.role_key }}</span>
				</template>
			</el-table-column>
			<el-table-column label="可见范围" width="200">
				<template #default="{ row }">
					<el-select v-model="row.mode" style="width: 170px" @change="onModeChange(row)">
						<el-option label="不可见（默认）" value="none" />
						<el-option label="全部可见" value="all" />
						<el-option label="仅指定目录" value="paths" />
					</el-select>
				</template>
			</el-table-column>
			<el-table-column label="可见目录">
				<template #default="{ row }">
					<el-select
						v-if="row.mode === 'paths'"
						v-model="row.paths"
						multiple
						filterable
						allow-create
						default-first-option
						placeholder="勾选，或直接输入目录后回车"
						style="width: 100%"
					>
						<el-option-group
							v-if="topOptionsFor(row).length"
							label="顶层目录 / Job（其下层默认可见）"
						>
							<el-option v-for="o in topOptionsFor(row)" :key="o.value" :label="o.label" :value="o.value" />
						</el-option-group>
						<el-option-group
							v-if="subOptionsFor(row).length"
							label="子目录（只想放开其中一部分时用）"
						>
							<el-option v-for="o in subOptionsFor(row)" :key="o.value" :label="o.label" :value="o.value" />
						</el-option-group>
					</el-select>
					<span v-else-if="row.mode === 'all'" class="rp-all">该角色可见全部 Job</span>
					<span v-else class="rp-none">该角色不可见任何 Job</span>
				</template>
			</el-table-column>
		</el-table>

		<template #footer>
			<el-button @click="visible = false">取消</el-button>
			<el-button type="primary" :loading="saving" @click="save">保存</el-button>
		</template>
	</el-dialog>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { GetRolePerms, SetRolePerms } from '../api';

export default defineComponent({
	name: 'jenkinsRolePermDialog',
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
			props.server ? `发布目录授权 — ${props.server.name}` : '发布目录授权'
		);

		const loading = ref(false);
		const saving = ref(false);
		// ★ 候选目录来自后端**实时读取**的 Jenkins 目录树，不再写死 dev/test/pre/prod。
		//   后端拉取失败时返回空数组 + foldersError（不会伪造列表），
		//   此时下拉仍可用 allow-create 手工输入。
		const folderOptions = ref<any[]>([]);
		const foldersError = ref('');
		// 每行：{ role, role_name, role_key, mode: 'none'|'all'|'paths', paths: [] }
		const rows = ref<any[]>([]);

		// 顶层项（含根级 Job）：授权后下层默认可见 —— 绝大多数场景只用这一组。
		// 提示语要显示数量，所以这里需要一个全局的；下拉里用的是逐行的 topOptionsFor(row)。
		const topOptions = computed(() => folderOptions.value.filter((o: any) => !o.depth));

		// 逐行取候选：把「已授权、但当前候选里没有的目录」补回去。
		// 否则一旦 Jenkins 上该目录被改名/删除、或实时读取失败，管理员点一下保存
		// 就会把这些目录静默删掉（等于悄悄扩大/收窄了权限）。
		const mergeGranted = (row: any) => {
			const out = folderOptions.value.slice();
			const known = new Set(out.map((o: any) => o.value));
			for (const p of row.paths || []) {
				if (p && !known.has(p)) {
					out.push({ value: p, label: String(p).replace(/\/$/, ''), depth: 0, kind: 'folder' });
				}
			}
			return out;
		};
		const topOptionsFor = (row: any) => mergeGranted(row).filter((o: any) => !o.depth);
		const subOptionsFor = (row: any) => mergeGranted(row).filter((o: any) => o.depth > 0);

		const load = async () => {
			if (!props.server?.id) return;
			loading.value = true;
			try {
				const res: any = await GetRolePerms(props.server.id);
				if (res.code === 2000) {
					const list = res.data?.roles || [];
					folderOptions.value = res.data?.folder_options || [];
					foldersError.value = res.data?.folders_error || '';
					rows.value = list.map((r: any) => ({
						role: r.role,
						role_name: r.role_name,
						role_key: r.role_key,
						mode: !r.configured ? 'none' : (r.allow_all ? 'all' : 'paths'),
						paths: r.allowed_paths || [],
					}));
				} else {
					ElMessage.error(res.msg || '获取授权配置失败');
				}
			} finally {
				loading.value = false;
			}
		};

		const onModeChange = (row: any) => {
			if (row.mode === 'paths' && !row.paths.length) {
				row.paths = [];
			}
		};

		const save = async () => {
			if (!props.server?.id) return;
			const perms: any[] = [];
			for (const r of rows.value) {
				if (r.mode === 'none') continue;         // 不提交 = 收回授权
				if (r.mode === 'all') {
					perms.push({ role: r.role, allow_all: true });
					continue;
				}
				// 仅指定目录但一个都没选：提交空数组在后端语义上是"全部可见"，
				// 与用户意图相反，这里直接拦下。
				if (!r.paths.length) {
					ElMessage.warning(`角色「${r.role_name}」选择了"仅指定目录"但未选目录`);
					return;
				}
				perms.push({ role: r.role, allow_all: false, allowed_paths: r.paths });
			}
			saving.value = true;
			try {
				const res: any = await SetRolePerms(props.server.id, perms);
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
			folderOptions.value = [];
			foldersError.value = '';
		};

		watch(
			() => props.modelValue,
			(v) => { if (v) load(); }
		);

		return {
			visible, title, loading, saving, folderOptions, foldersError, rows,
			topOptions, topOptionsFor, subOptionsFor,
			onModeChange, save, onClosed,
		};
	},
});
</script>

<style scoped>
.rp-tip {
	font-size: 13px;
	color: #606266;
	line-height: 1.7;
	margin-bottom: 12px;
	padding: 10px 12px;
	background: #f5f8ff;
	border-radius: 6px;
}
.rp-role {
	color: #303133;
}
.rp-key {
	margin-left: 6px;
	color: #c0c4cc;
	font-size: 12px;
}
.rp-all {
	color: #67c23a;
	font-size: 13px;
}
.rp-none {
	color: #c0c4cc;
	font-size: 13px;
}
.rp-warn {
	color: #e6a23c;
	font-weight: 600;
}
</style>
