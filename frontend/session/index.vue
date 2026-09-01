<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding" />
		<el-dialog
			v-model="replayVisible"
			title="会话回放"
			width="78%"
			top="6vh"
			:close-on-click-modal="false"
			:destroy-on-close="true"
			@opened="onReplayOpened"
			@closed="onReplayClosed"
		>
			<div ref="playerRef" class="replay-container"></div>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as AsciinemaPlayer from 'asciinema-player';
import 'asciinema-player/dist/bundle/asciinema-player.css';

export default defineComponent({
	name: "bastionSession",
	setup() {
		const instance = getCurrentInstance();
		const replayVisible = ref(false);
		const replaySrc = ref('');
		const playerRef = ref();
		let player: any = null;

		const context: any = {
			componentName: instance?.type.name,
			openReplay: (row: any) => {
				// recording 存的是 media/sessions/{id}.cast
				replaySrc.value = '/' + row.recording.replace(/^\/+/, '');
				replayVisible.value = true;
			},
		};

		const { crudBinding, crudRef, crudExpose } = useFs({ createCrudOptions, context });

		const onReplayOpened = () => {
			if (playerRef.value && replaySrc.value) {
				player = AsciinemaPlayer.create(replaySrc.value, playerRef.value, {
					fit: 'width',
					terminalFontSize: '13px',
					autoPlay: true,
				});
			}
		};

		const onReplayClosed = () => {
			if (player) {
				player.dispose();
				player = null;
			}
		};

		onMounted(() => {
			crudExpose.doRefresh();
		});

		return { crudBinding, crudRef, replayVisible, playerRef, onReplayOpened, onReplayClosed };
	}
});
</script>

<style scoped>
:deep(.fs-crud) {
  position: relative;
}
:deep(.fs-crud-actionbar) {
  position: absolute;
  top: 10px;
  right: 20px;
  z-index: 10;
  margin: 0;
  display: flex;
  justify-content: flex-end;
}
:deep(.fs-actionbar-buttons) {
  gap: 6px;
  flex-wrap: nowrap;
}
:deep(.fs-crud-search),
:deep(.fs-search-column) {
  padding-right: 200px;
}
.replay-container {
  width: 100%;
  background: #121314;
  border-radius: 6px;
  min-height: 420px;
}
</style>
