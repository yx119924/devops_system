import { reactive } from 'vue';

/**
 * 流水线编排 / 发起执行 / 执行详情 三个弹层的共享状态。
 *
 * ★ 为什么用一个小 store 而不是把弹层塞进 crud.tsx：
 *   fast-crud 的 `rowHandle.buttons[].click` 只能拿到 ctx（没有组件实例），
 *   而弹层需要挂在页面组件上（要能 v-model、要能拿到 emit）。
 *   与 `log/collect/panelStore.ts` 同一套路子。
 */
export const designerStore = reactive({
	visible: false,
	pipeline: null as any,
});

export const runStartStore = reactive({
	visible: false,
	pipeline: null as any,
});

/** 执行详情（推进/中止/重跑）弹层；两个页面共用 */
export const runPanelStore = reactive({
	visible: false,
	runId: null as number | null,
});

export function openDesigner(row: any) {
	designerStore.pipeline = row;
	designerStore.visible = true;
}

export function openRunStart(row: any) {
	runStartStore.pipeline = row;
	runStartStore.visible = true;
}

export function openRunPanel(runId: number) {
	runPanelStore.runId = runId;
	runPanelStore.visible = true;
}
