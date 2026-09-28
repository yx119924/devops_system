<template>
	<div class="error layout-view-bg-white" :style="{ height: `calc(100vh - ${initTagViewHeight}` }">
		<div class="error-flex">
			<div class="left">
				<div class="left-item">
					<div class="left-item-animation left-item-num">401</div>
					<div class="left-item-animation left-item-title">{{ $t('message.noAccess.accessTitle') }}</div>
					<div class="left-item-animation left-item-msg">{{ $t('message.noAccess.accessMsg') }}</div>
					<div class="left-item-animation left-item-btn">
						<el-button type="primary" round @click="onSetAuth">{{ $t('message.noAccess.accessBtn') }}</el-button>
					</div>
				</div>
			</div>
			<div class="right">
				<!-- 上游模板残留：原插图指向一个第三方 CDN 外链（详见 CHANGELOG），
				     内网不可达会裂图、且带图床水印参数。改用平台自带的 login-main.svg。 -->
				<img :src="errorImg" alt="401" />
			</div>
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { useTagsViewRoutes } from '/@/stores/tagsViewRoutes';
import { Session } from '/@/utils/storage';
import errorImg from '/@/assets/login-main.svg';

export default defineComponent({
	name: '401',
	setup() {
		const storesThemeConfig = useThemeConfig();
		const storesTagsViewRoutes = useTagsViewRoutes();
		const { themeConfig } = storeToRefs(storesThemeConfig);
		const { isTagsViewCurrenFull } = storeToRefs(storesTagsViewRoutes);
		const onSetAuth = () => {
			// https://gitee.com/lyt-top/vue-next-admin/issues/I5C3JS
			// 清除缓存/token等
			Session.clear();
			// 使用 reload 时，不需要调用 resetRoute() 重置路由
			window.location.reload();
		};
		// 设置主内容的高度
		const initTagViewHeight = computed(() => {
			let { isTagsview } = themeConfig.value;
			if (isTagsViewCurrenFull.value) {
				return `30px`;
			} else {
				if (isTagsview) return `114px`;
				else return `80px`;
			}
		});
		return {
			onSetAuth,
			initTagViewHeight,
			errorImg,
		};
	},
});
</script>

<style scoped lang="scss">
.error {
	height: 100%;
	background-color: var(--el-color-white);
	display: flex;
	.error-flex {
		margin: auto;
		display: flex;
		height: 350px;
		width: 900px;
		.left {
			flex: 1;
			height: 100%;
			align-items: center;
			display: flex;
			.left-item {
				.left-item-animation {
					opacity: 0;
					animation-name: error-num;
					animation-duration: 0.5s;
					animation-fill-mode: forwards;
				}
				.left-item-num {
					color: var(--el-color-info);
					font-size: 55px;
				}
				.left-item-title {
					font-size: 20px;
					color: var(--el-text-color-primary);
					margin: 15px 0 5px 0;
					animation-delay: 0.1s;
				}
				.left-item-msg {
					color: var(--el-text-color-secondary);
					font-size: 12px;
					margin-bottom: 30px;
					animation-delay: 0.2s;
				}
				.left-item-btn {
					animation-delay: 0.2s;
				}
			}
		}
		.right {
			flex: 1;
			opacity: 0;
			animation-name: error-img;
			animation-duration: 2s;
			animation-fill-mode: forwards;
			img {
				width: 100%;
				height: 100%;
			}
		}
	}
}
</style>
