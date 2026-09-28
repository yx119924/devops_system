<template>
	<el-dialog
		:model-value="modelValue"
		title="Web SSH 终端"
		width="82%"
		top="5vh"
		:close-on-click-modal="false"
		:destroy-on-close="true"
		@update:model-value="(v: boolean) => emit('update:modelValue', v)"
		@opened="onOpened"
		@closed="onClosed"
	>
		<div class="ssh-toolbar">
			<span class="ssh-server" v-if="server">{{ server.hostname }}（{{ server.ip }}:{{ server.ssh_port || 22 }}）</span>
			<el-select
				v-if="credentials.length > 1"
				v-model="credentialId"
				placeholder="选择凭据"
				clearable
				filterable
				style="width: 280px"
			>
				<el-option v-for="c in credentials" :key="c.id" :label="`${c.name}（${c.username}）`" :value="c.id" />
			</el-select>
			<span v-else-if="credentials.length === 1" class="ssh-cred">凭据：{{ credentials[0].name }}（{{ credentials[0].username }}）</span>
			<el-button type="primary" :disabled="!credentialId || connecting" :loading="connecting" @click="connect">连接</el-button>
			<el-button @click="disconnect">断开</el-button>
			<span class="ssh-hint">{{ hint }}</span>
		</div>
		<div ref="terminalRef" class="ssh-terminal"></div>
	</el-dialog>
</template>

<script lang="ts">
import { computed, defineComponent, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Session } from '/@/utils/storage';
import { getWsBaseURL } from '/@/utils/baseUrl';
import { request } from '/@/utils/service';

export default defineComponent({
	name: 'webSsh',
	props: {
		modelValue: { type: Boolean, default: false },
		server: { type: Object, default: null },
	},
	emits: ['update:modelValue'],
	setup(props, { emit }) {
		const terminalRef = ref();
		const credentialId = ref<any>(null);
		const credentials = ref<any[]>([]);
		const connecting = ref(false);
		let term: Terminal | null = null;
		let fitAddon: FitAddon | null = null;
		let ws: WebSocket | null = null;

		const hint = computed(() => {
			if (credentials.value.length === 0) return '该服务器没有可用凭据，请联系运维在「凭据管理」中配置';
			return '连接后可直接操作服务器';
		});

		/**
		 * 拉取"这台服务器上我能用的凭据"。
		 *
		 * 走 `/api/cmdb/server/{id}/ssh_credentials/` 而不是凭据模块的
		 * `/api/bastion/credential/`：
		 * - 后者属「凭据管理」模块，开发/测试这类角色没有该按钮权限，请求直接 4000
		 *   （曾经的表现就是下拉永远是"无数据"，弹窗里根本无法连接）；
		 * - 而且 `CustomPermission` 是**前缀**匹配，任何
		 *   `/api/bastion/credential/xxx/` 都会落到同一条按钮权限上，绕不开；
		 * - 该接口只吐 id/name/username/auth_type，密码与私钥是 write_only，不会外泄，
		 *   且服务端已按资产授权校验"这台机器你看不看得到"。
		 */
		const loadCredentials = async () => {
			credentials.value = [];
			credentialId.value = null;
			if (!props.server) return;
			try {
				const res: any = await request({
					url: `/api/cmdb/server/${props.server.id}/ssh_credentials/`,
					method: 'get',
				});
				if (res.code !== 2000) {
					ElMessage.error(res.msg || '获取可用凭据失败');
					return;
				}
				const list = Array.isArray(res.data) ? res.data : [];
				credentials.value = list;
				// 只剩一条时直接选中，省掉一次无意义的选择（这是绝大多数机器的情形）
				if (list.length === 1) credentialId.value = list[0].id;
			} catch (e: any) {
				ElMessage.error(e?.message || '获取可用凭据失败');
			}
		};

		const initTerminal = () => {
			if (term) return;
			term = new Terminal({
				fontSize: 14,
				cursorBlink: true,
				convertEol: true,
				theme: { background: '#1e1e1e' },
			});
			fitAddon = new FitAddon();
			term.loadAddon(fitAddon);
			term.open(terminalRef.value);
			fitAddon.fit();
			term.onData((data) => {
				if (ws && ws.readyState === WebSocket.OPEN) {
					ws.send(JSON.stringify({ type: 'input', data }));
				}
			});
			window.addEventListener('resize', onResize);
		};

		const onResize = () => {
			if (fitAddon && term) {
				fitAddon.fit();
				if (ws && ws.readyState === WebSocket.OPEN) {
					ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
				}
			}
		};

		const onOpened = () => {
			loadCredentials();
			initTerminal();
		};

		const connect = () => {
			if (!credentialId.value || !props.server) return;
			initTerminal();
			disconnect();
			connecting.value = true;
			const token = Session.get('token');
			const url = `${getWsBaseURL()}ws/ssh/${token}/${props.server.id}/${credentialId.value}/`;
			ws = new WebSocket(url);
			ws.onopen = () => {
				connecting.value = false;
				term?.reset();
				term?.writeln('\x1b[32m连接成功，正在登录 ' + props.server.hostname + '...\x1b[0m');
			};
			ws.onmessage = (event) => {
				try {
					const msg = JSON.parse(event.data);
					if (msg.type === 'stdout') {
						term?.write(msg.data);
					} else if (msg.type === 'error') {
						term?.writeln('\r\n\x1b[31m连接失败：' + msg.message + '\x1b[0m');
					}
				} catch (e) {}
			};
			ws.onclose = () => {
				connecting.value = false;
				term?.writeln('\r\n\x1b[33m连接已断开\x1b[0m');
			};
			ws.onerror = () => {
				connecting.value = false;
				term?.writeln('\r\n\x1b[31m连接出错，请检查服务器网络/凭据\x1b[0m');
			};
		};

		const disconnect = () => {
			connecting.value = false;
			if (ws) {
				ws.close();
				ws = null;
			}
		};

		const onClosed = () => {
			disconnect();
			window.removeEventListener('resize', onResize);
			if (term) {
				term.dispose();
				term = null;
				fitAddon = null;
			}
		};

		return { terminalRef, credentialId, credentials, connecting, hint, onOpened, onClosed, connect, disconnect, emit };
	},
});
</script>

<style scoped>
.ssh-toolbar {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 12px;
}
.ssh-server {
	font-weight: 600;
	color: #303133;
}
.ssh-cred {
	font-size: 13px;
	color: #606266;
}
.ssh-hint {
	font-size: 12px;
	color: #909399;
}
.ssh-terminal {
	width: 100%;
	height: 62vh;
	background: #1e1e1e;
	border-radius: 4px;
	padding: 8px;
	box-sizing: border-box;
}
</style>
