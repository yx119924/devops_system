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
			<el-select v-model="credentialId" placeholder="选择凭据" clearable filterable style="width: 280px">
				<el-option v-for="c in credentials" :key="c.id" :label="`${c.name}（${c.username}）`" :value="c.id" />
			</el-select>
			<el-button type="primary" :disabled="!credentialId" @click="connect">连接</el-button>
			<el-button @click="disconnect">断开</el-button>
			<span class="ssh-hint">连接后可直接操作服务器</span>
		</div>
		<div ref="terminalRef" class="ssh-terminal"></div>
	</el-dialog>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';
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
		let term: Terminal | null = null;
		let fitAddon: FitAddon | null = null;
		let ws: WebSocket | null = null;

		const loadCredentials = async () => {
			try {
				const res: any = await request({ url: '/api/bastion/credential/', method: 'get', params: { limit: 1000 } });
				credentials.value = res.data || [];
			} catch (e) {}
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
			const token = Session.get('token');
			const url = `${getWsBaseURL()}ws/ssh/${token}/${props.server.id}/${credentialId.value}/`;
			ws = new WebSocket(url);
			ws.onopen = () => {
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
				term?.writeln('\r\n\x1b[33m连接已断开\x1b[0m');
			};
			ws.onerror = () => {
				term?.writeln('\r\n\x1b[31m连接出错，请检查服务器网络/凭据\x1b[0m');
			};
		};

		const disconnect = () => {
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

		return { terminalRef, credentialId, credentials, onOpened, onClosed, connect, disconnect, emit };
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
