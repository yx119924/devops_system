<template>
	<div class="grant-panel">
		<div class="panel-alert">
			<el-button size="small" type="primary" :loading="saving" @click="handleSave">保存</el-button>
			<span class="panel-tip">
				当前角色：<b>{{ roleName }}</b> —— 这里配置该角色能看到的 <b>Jenkins Job 目录</b>。
				目录候选是<b>实时读取各台 Jenkins</b> 得到的，授权某一层目录即可，其下层子目录默认可见。
				<template v-if="failedServers.length">
					<span class="warn">{{ failedServers.join('、') }} 读取目录失败</span>，该行请手工输入目录。
				</template>
			</span>
		</div>

		<el-table :data="rows" border size="small" v-loading="loading" empty-text="暂无可配置的 Jenkins 服务器">
			<el-table-column label="Jenkins 服务器" min-width="220">
				<template #default="{ row }">
					<div class="srv-name">{{ row.server_name }}</div>
					<div class="srv-url">{{ row.url }}</div>
				</template>
			</el-table-column>
			<el-table-column label="可见性" width="180">
				<template #default="{ row }">
					<el-select v-model="row.mode" size="small" style="width: 100%">
						<el-option label="不可见" value="none" />
						<el-option label="全部可见" value="all" />
						<el-option label="仅指定目录" value="paths" />
					</el-select>
				</template>
			</el-table-column>
			<el-table-column label="可见目录（可输入新目录后回车）" min-width="300">
				<template #default="{ row }">
					<el-select
						v-model="row.allowed_paths"
						multiple
						filterable
						allow-create
						default-first-option
						size="small"
						style="width: 100%"
						:disabled="row.mode !== 'paths'"
						placeholder="勾选，或直接输入目录后回车"
					>
						<el-option-group v-if="topOpts(row).length" label="顶层目录 / Job（其下层默认可见）">
							<el-option v-for="o in topOpts(row)" :key="o.value" :label="o.label" :value="o.value" />
						</el-option-group>
						<el-option-group v-if="subOpts(row).length" label="子目录（只想放开其中一部分时用）">
							<el-option v-for="o in subOpts(row)" :key="o.value" :label="o.label" :value="o.value" />
						</el-option-group>
					</el-select>
				</template>
			</el-table-column>
			<el-table-column label="当前生效" width="220">
				<template #default="{ row }">
					<span class="eff">{{ effectText(row) }}</span>
				</template>
			</el-table-column>
		</el-table>

		<div class="panel-foot">
			「不可见」= 该角色在此 Jenkins 上一条 Job 都看不到（默认拒绝）。保存后立即生效，用户重新打开「构建发布」页即可。
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { RoleDrawerStores } from '../stores/RoleDrawerStores';
import { GetRoleJenkinsGrants, SetRoleJenkinsGrants } from './grantApi';

const RoleDrawer = RoleDrawerStores();

const loading = ref(false);
const saving = ref(false);
const roleName = ref('');
const rows = ref<any[]>([]);

// 哪几台服务器没读到目录结构（仅用于前端提示；后端不会伪造候选列表）
const failedServers = computed(() =>
	rows.value.filter((r: any) => r.folders_error).map((r: any) => r.server_name)
);

// ★ 候选目录由后端**逐台实时读取**（不同 Jenkins 的目录结构可能不同），不再写死
//   dev/test/pre/prod。这里再把「已授权、但候选里没有的」补回去 —— 否则一旦
//   实时读取失败或该目录已在 Jenkins 上改名/删除，管理员点一下保存就会把它静默丢掉。
const optList = (row: any) => {
	const src = Array.isArray(row.folder_options) ? row.folder_options : [];
	const out = src.map((o: any) => ({
		value: o.value,
		label: o.label,
		depth: Number(o.depth) || 0,
	}));
	const known = new Set(out.map((o: any) => o.value));
	for (const p of row.allowed_paths || []) {
		if (p && !known.has(p)) out.push({ value: p, label: String(p).replace(/\/$/, ''), depth: 0 });
	}
	return out;
};
const topOpts = (row: any) => optList(row).filter((o: any) => !o.depth);
const subOpts = (row: any) => optList(row).filter((o: any) => o.depth > 0);

const effectText = (row: any) => {
	if (row.mode === 'all') return '全部 Job';
	if (row.mode === 'none') return '无（看不到任何 Job）';
	const paths = row.allowed_paths || [];
	if (!paths.length) return '无（未选目录）';
	return paths.join('、');
};

const load = async (roleId: any) => {
	if (!roleId) {
		rows.value = [];
		roleName.value = '';
		return;
	}
	loading.value = true;
	try {
		const res: any = await GetRoleJenkinsGrants(roleId);
		if (res.code !== 2000) {
			ElMessage.error(res.msg || '读取 Jenkins 目录授权失败');
			rows.value = [];
			return;
		}
		roleName.value = res.data?.role_name || '';
		rows.value = (res.data?.servers || []).map((s: any) => ({
			server: s.server,
			server_name: s.server_name,
			url: s.url,
			mode: s.allow_all ? 'all' : (s.allowed_paths || []).length ? 'paths' : 'none',
			allowed_paths: [...(s.allowed_paths || [])],
			// 该台 Jenkins 的实时候选目录（后端逐台下发，各台可能不同）
			folder_options: Array.isArray(s.folder_options) ? s.folder_options : [],
			folders_error: s.folders_error || '',
		}));
	} catch (e: any) {
		ElMessage.error(e?.message || '读取 Jenkins 目录授权失败');
		rows.value = [];
	} finally {
		loading.value = false;
	}
};

const handleSave = async () => {
	// 「仅指定目录」但一个都没选 —— 后端语义会把空数组当成"全部可见"，
	// 必须在前端拦住，否则是静默的超范围授权。
	for (const row of rows.value) {
		if (row.mode === 'paths' && !(row.allowed_paths || []).length) {
			ElMessage.warning(`「${row.server_name}」选择了"仅指定目录"但没填目录，请先选择目录或改为其他可见性`);
			return;
		}
	}
	saving.value = true;
	try {
		const perms = rows.value.map((row: any) => {
			if (row.mode === 'all') return { server: row.server, allow_all: true };
			if (row.mode === 'none') return { server: row.server, allowed_paths: [] };
			return { server: row.server, allowed_paths: row.allowed_paths };
		});
		const res: any = await SetRoleJenkinsGrants(RoleDrawer.$state.roleId, perms);
		ElMessage({ message: res.msg || '已保存', type: res.code === 2000 ? 'success' : 'error' });
		if (res.code === 2000) await load(RoleDrawer.$state.roleId);
	} catch (e: any) {
		ElMessage.error(e?.message || '保存失败');
	} finally {
		saving.value = false;
	}
};

// 角色切换（抽屉里换角色）时重新加载
watch(
	() => RoleDrawer.$state.roleId,
	(v) => load(v),
	{ immediate: true }
);
</script>

<style lang="scss" scoped>
.grant-panel {
	.panel-alert {
		line-height: 22px;
		padding: 8px 16px;
		margin-bottom: 16px;
		border-radius: 4px;
		background-color: var(--el-color-primary-light-9);
		color: var(--el-text-color-primary);

		.panel-tip {
			margin-left: 12px;
			font-size: 13px;
		}
		.warn {
			color: var(--el-color-warning);
			font-weight: 600;
		}
		code {
			padding: 0 4px;
			border-radius: 3px;
			background: var(--el-fill-color);
		}
	}
	.srv-name {
		font-weight: 600;
	}
	.srv-url {
		font-size: 12px;
		color: var(--el-text-color-secondary);
		word-break: break-all;
	}
	.eff {
		font-size: 12px;
		color: var(--el-color-success);
	}
	.panel-foot {
		margin-top: 12px;
		font-size: 12px;
		line-height: 20px;
		color: var(--el-text-color-secondary);
	}
}
</style>
