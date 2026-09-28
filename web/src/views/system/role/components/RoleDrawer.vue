<template>
	<el-drawer
		v-model="RoleDrawer.drawerVisible"
		:title="$t('message.pages.role.dialog.assignPermissions')"
		direction="rtl"
		size="80%"
		:close-on-click-modal="false"
		:before-close="RoleDrawer.handleDrawerClose"
		:destroy-on-close="true"
	>
		<template #header>
			<div>
				{{ $t('message.pages.role.dialog.currentRole') }}
				<el-tag style="margin-right: 20px">{{ RoleDrawer.roleName }}</el-tag>
				{{ $t('message.pages.role.dialog.authorizedUsers') }}
				<el-button size="small" :icon="UserFilled" @click="handleUsers">{{ RoleDrawer.users.length }}</el-button>
			</div>
		</template>
		<splitpanes class="default-theme" style="height: 100%">
			<pane min-size="20" size="22">
				<div class="pane-box">
					<MenuTreeCom />
				</div>
			</pane>
			<pane min-size="20">
				<div class="pane-box">
					<el-tabs v-model="activeName" class="demo-tabs">
						<el-tab-pane :label="$t('message.pages.role.dialog.interfacePermission')" name="first"><MenuBtnCom /></el-tab-pane>
						<el-tab-pane :label="$t('message.pages.role.dialog.columnPermission')" name="second"><MenuFieldCom /></el-tab-pane>
						<!-- 扩展面板：Jenkins Job 目录授权 / 服务器资产授权。
						     放在角色管理里配置，是为了让"某人能看哪些 Job、哪些机器"和
						     这份角色的其他权限在一处维护，不用去业务页面逐台点。 -->
						<el-tab-pane label="Jenkins 目录授权" name="jenkins"><JenkinsGrantCom /></el-tab-pane>
						<el-tab-pane label="服务器资产授权" name="server"><ServerGrantCom /></el-tab-pane>
					</el-tabs>
				</div>
			</pane>
		</splitpanes>
	</el-drawer>

	<el-dialog v-model="dialogVisible" :title="$t('message.pages.role.dialog.assignUsers')" width="700px" :close-on-click-modal="false">
		<RoleUsersCom />
	</el-dialog>
</template>

<script setup lang="ts">
import { Splitpanes, Pane } from 'splitpanes';
import 'splitpanes/dist/splitpanes.css';
import { UserFilled } from '@element-plus/icons-vue';
import { RoleDrawerStores } from '../stores/RoleDrawerStores';
import { defineAsyncComponent, ref, watch } from 'vue';
import { RoleUsersStores } from '../stores/RoleUsersStores';

const MenuTreeCom = defineAsyncComponent(() => import('./RoleMenuTree.vue'));
const MenuBtnCom = defineAsyncComponent(() => import('./RoleMenuBtn.vue'));
const MenuFieldCom = defineAsyncComponent(() => import('./RoleMenuField.vue'));
const RoleUsersCom = defineAsyncComponent(() => import('./RoleUsers.vue'));
const JenkinsGrantCom = defineAsyncComponent(() => import('./RoleJenkinsGrant.vue'));
const ServerGrantCom = defineAsyncComponent(() => import('./RoleServerGrant.vue'));
const RoleDrawer = RoleDrawerStores(); // 抽屉参数
const RoleUsers = RoleUsersStores(); // 角色-用户
const activeName = ref('first');

const dialogVisible = ref(false);

const handleUsers = () => {
	dialogVisible.value = true;
	RoleUsers.get_all_users(); // 获取所有用户
	RoleUsers.set_right_users(RoleDrawer.$state.users); // 设置已选中用户
};

// 每次打开抽屉都回到第一个 tab，避免上次停在 Jenkins/资产授权页时
// 被误以为是角色默认的权限页
watch(
	() => RoleDrawer.drawerVisible,
	(v) => {
		if (v) activeName.value = 'first';
	}
);
</script>

<style lang="scss" scoped>
.pane-box {
	width: 100vw; /* 视口宽度 */
	height: 100vh; /* 视口高度 */
	max-width: 100%; /* 确保不超过父元素的宽度 */
	max-height: 100%; /* 确保不超过父元素的高度 */
	overflow: auto; /* 当内容超出容器尺寸时显示滚动条 */
	padding: 10px;
	background-color: #fff;
}
</style>
