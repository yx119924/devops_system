<template>
	<div class="md-body" v-html="html"></div>
</template>

<script lang="ts">
/**
 * AI 回答的 Markdown 渲染器。
 *
 * ★ 为什么需要它：AI 回答天然是 Markdown（标题/加粗/表格/代码块），
 *   而原来用 `v-text` + `white-space: pre-wrap` 渲染 ⇒ `###` `**` `|` 全部原样露出。
 *   渲染的责任在前端，不该反过来要求模型别用 Markdown。
 *
 * ★ 安全：`html: false` 是核心防线 —— 模型输出里的原生 HTML 一律当纯文本转义。
 *   这条必须有：日志内容可能被注入 `<img onerror=...>`，AI 转述时会把 payload 带出来。
 *   markdown-it 默认还会拒绝 `javascript:` 协议的链接。
 *   双重保险：外链统一加 rel="noopener noreferrer"。
 */
import { computed, defineComponent } from 'vue';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
	html: false,
	linkify: true,
	// AI 输出习惯用单换行分行，不开 breaks 会把两行并成一段
	breaks: true,
	typographer: false,
});

const rawLinkOpen = md.renderer.rules.link_open;
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
	tokens[idx].attrSet('target', '_blank');
	tokens[idx].attrSet('rel', 'noopener noreferrer');
	if (rawLinkOpen) return rawLinkOpen(tokens, idx, options, env, self);
	return self.renderToken(tokens, idx, options);
};

export default defineComponent({
	name: 'MarkdownView',
	props: {
		source: { type: String, default: '' },
	},
	setup(props) {
		const html = computed(() => md.render(props.source || ''));
		return { html };
	},
});
</script>

<style scoped lang="less">
.md-body {
	font-size: 13.5px;
	line-height: 1.8;
	color: #303133;
	word-break: break-word;

	/* 首尾不要留白，否则气泡里上下会空一块 */
	:deep(> :first-child) {
		margin-top: 0;
	}
	:deep(> :last-child) {
		margin-bottom: 0;
	}

	/* 标题：整体收敛字号。AI 回答里标题密度高，按网页默认的 h2/h3 会喧宾夺主 */
	:deep(h1),
	:deep(h2),
	:deep(h3),
	:deep(h4),
	:deep(h5) {
		margin: 14px 0 6px;
		font-weight: 600;
		line-height: 1.5;
		color: #1f2d3d;
	}
	:deep(h1) {
		font-size: 16px;
	}
	:deep(h2) {
		font-size: 15px;
	}
	:deep(h3) {
		font-size: 14px;
	}
	:deep(h4),
	:deep(h5) {
		font-size: 13.5px;
	}

	:deep(p) {
		margin: 6px 0;
	}
	:deep(strong) {
		font-weight: 600;
		color: #1f2d3d;
	}
	:deep(em) {
		font-style: italic;
		color: #5a5e66;
	}
	:deep(del) {
		color: #909399;
	}

	/* 列表：左侧留够缩进，不然圆点和父级文字挤在一起 */
	:deep(ul),
	:deep(ol) {
		margin: 6px 0;
		padding-left: 22px;
	}
	:deep(li) {
		margin: 3px 0;
	}
	:deep(li > p) {
		margin: 0;
	}

	/* 表格：细边框 + 表头浅底。AI 常用表格做参数对比 */
	:deep(table) {
		border-collapse: collapse;
		margin: 8px 0;
		font-size: 12.5px;
		width: 100%;
		display: block;
		overflow-x: auto;
	}
	:deep(th),
	:deep(td) {
		border: 1px solid #e4e7ed;
		padding: 6px 10px;
		text-align: left;
		vertical-align: top;
	}
	:deep(th) {
		background: #f5f7fa;
		font-weight: 600;
		color: #1f2d3d;
		white-space: nowrap;
	}

	/* 行内代码：命令、参数名用得多，浅底 + 等宽 */
	:deep(code) {
		font-family: Menlo, Consolas, 'Courier New', monospace;
		font-size: 12.5px;
		background: #f4f4f5;
		color: #c7254e;
		padding: 1px 5px;
		border-radius: 3px;
	}
	/* 代码块：不要行内代码那套红字浅底，会糊成一片 */
	:deep(pre) {
		margin: 8px 0;
		padding: 10px 12px;
		background: #f7f8fa;
		border: 1px solid #ebeef5;
		border-radius: 4px;
		overflow-x: auto;
		line-height: 1.6;
	}
	:deep(pre code) {
		background: transparent;
		color: #303133;
		padding: 0;
		font-size: 12.5px;
		white-space: pre;
	}

	:deep(blockquote) {
		margin: 8px 0;
		padding: 4px 12px;
		border-left: 3px solid #dcdfe6;
		background: #fafafa;
		color: #5a5e66;
	}

	:deep(hr) {
		margin: 12px 0;
		border: 0;
		border-top: 1px solid #ebeef5;
	}

	:deep(a) {
		color: #409eff;
		text-decoration: none;
		&:hover {
			text-decoration: underline;
		}
	}

	:deep(img) {
		max-width: 100%;
	}
}
</style>
