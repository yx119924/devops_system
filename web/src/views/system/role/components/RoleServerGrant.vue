<template>
	<div class="grant-panel">
		<div class="panel-alert">
			<el-button size="small" type="primary" :loading="saving" @click="handleSave">保存</el-button>
			<span class="panel-tip">
				当前角色：<b>{{ roleName }}</b> —— 这里配置该角色能访问的 <b>服务器</b>。
				「可操作」= 能下发命令 / 开终端 / 传凭据操作；「只读」= 只看得到资产台账，连不上也下发不了。
				运维与管理员角色默认可见<b>全部</b>服务器，不需要在此配置。
			</span>
		</div>

		<div class="panel-toolbar">
			<el-input v-model="keyword" placeholder="搜索主机名 / IP" clearable size="small" style="width: 240px" />
			<el-checkbox v-model="onlyGranted" size="small">只看已授权</el-checkbox>
			<span class="counter">已授权 {{ grantedCount }} / {{ rows.length }} 台</span>
		</div>

		<el-table :data="visibleRows" border size="small" v-loading="loading" max-height="52vh" empty-text="没有匹配的服务器">
			<el-table-column label="主机名" min-width="180">
				<template #default="{ row }">
					<span class="srv-name">{{ row.hostname }}</span>
				</template>
			</el-table-column>
			<el-table-column label="IP" width="150" prop="ip" />
			<el-table-column label="状态" width="90">
				<template #default="{ row }">
					<el-tag :type="row.status === 'online' ? 'success' : 'info'" size="small">{{ row.status === 'online' ? '在线' : '停用' }}</el-tag>
				</template>
			</el-table-column>
			<el-table-column label="授权级别" width="150">
				<template #default="{ row }">
					<el-select v-model="row.level" size="small" style="width: 100%">
						<el-option label="无授权" value="" />
						<el-option label="只读" value="read" />
						<el-option label="可操作" value="write" />
					</el-select>
				</template>
			</el-table-column>
		</el-table>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { RoleDrawerStores } from '../stores/RoleDrawerStores';
import { GetRoleServerGrants, SetRoleServerGrants } from './grantApi';

const RoleDrawer = RoleDrawerStores();

const loading = ref(false);
const saving = ref(false);
const roleName = ref('');
const rows = ref<any[]>([]);
const keyword = ref('');
const onlyGranted = ref(false);

const visibleRows = computed(() => {
	const kw = keyword.value.trim().toLowerCase();
	return rows.value.filter((r) => {
		if (onlyGranted.value && !r.level) return false;
		if (!kw) return true;
		return String(r.hostname || '').toLowerCase().includes(kw) || String(r.ip || '').includes(kw);
	});
});

const grantedCount = computed(() => rows.value.filter((r) => !!r.level).length);

const load = async (roleId: any) => {
	if (!roleId) {
		rows.value = [];
		roleName.value = '';
		return;
	}
	loading.value = true;
	try {
		const res: any = await GetRoleServerGrants(roleId);
		if (res.code !== 2000) {
			ElMessage.error(res.msg || '读取资产授权失败');
			rows.value = [];
			return;
		}
		roleName.value = res.data?.role_name || '';
		rows.value = (res.data?.servers || []).map((s: any) => ({
			server: s.server,
			hostname: s.hostname,
			ip: s.ip,
			status: s.status,
			level: s.level || '',
		}));
	} catch (e: any) {
		ElMessage.error(e?.message || '读取资产授权失败');
		rows.value = [];
	} finally {
		loading.value = false;
	}
};

const handleSave = async () => {
	saving.value = true;
	try {
		const grants = rows.value.map((r: any) => ({ server: r.server, level: r.level || '' }));
		const res: any = await SetRoleServerGrants(RoleDrawer.$state.roleId, grants);
		ElMessage({ message: res.msg || '已保存', type: res.code === 2000 ? 'success' : 'error' });
		if (res.code === 2000) await load(RoleDrawer.$state.roleId);
	} catch (e: any) {
		ElMessage.error(e?.message || '保存失败');
	} finally {
		saving.value = false;
	}
};

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
	}
	.panel-toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 10px;

		.counter {
			font-size: 12px;
			color: var(--el-text-color-secondary);
		}
	}
	.srv-name {
		font-weight: 600;
	}
}
</style>
