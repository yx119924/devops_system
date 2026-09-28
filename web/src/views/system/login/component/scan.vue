<template>
	<div class="login-scan-container">
		<div ref="qrcodeRef"></div>
		<div class="font12 mt20 login-msg">{{ $t('message.pages.login.scan.text') }}</div>
	</div>
</template>

<script lang="ts">
import { ref, defineComponent, onMounted } from 'vue';
import QRCode from 'qrcodejs2-fixes';

export default defineComponent({
	name: 'loginScan',
	setup() {
		const qrcodeRef = ref<HTMLElement | null>(null);
		// 初始化生成二维码
		const initQrcode = () => {
			(qrcodeRef.value as HTMLElement).innerHTML = '';
			new QRCode(qrcodeRef.value, {
				// 上游模板残留：原文指向上游作者的 QQ 群（详见 CHANGELOG），会把用户引到无关第三方群。
				// 改为平台自身地址。
				// 备注：本组件当前未被任何页面引用（login/index.vue 里的 <Scan> 已注释），
				// 但 router/backEnd.ts 的 import.meta.glob('../views/**/*.{vue,tsx}')
				// 仍会把它打进产物，故一并清理。
				text: `${window.location.origin}`,
				width: 260,
				height: 260,
				colorDark: '#000000',
				colorLight: '#ffffff',
			});
		};
		// 页面加载时
		onMounted(() => {
			initQrcode();
		});
		return { qrcodeRef };
	},
});
</script>

<style scoped lang="scss">
.login-scan-animation {
	opacity: 0;
	animation-name: error-num;
	animation-duration: 0.5s;
	animation-fill-mode: forwards;
}
.login-scan-container {
	padding: 20px;
	display: flex;
	flex-direction: column;
	text-align: center;
	@extend .login-scan-animation;
	animation-delay: 0.1s;
	:deep(img) {
		margin: auto;
	}
	.login-msg {
		color: var(--el-text-color-placeholder);
		@extend .login-scan-animation;
		animation-delay: 0.2s;
	}
}
</style>
