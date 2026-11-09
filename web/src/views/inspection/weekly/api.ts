import { request } from '/@/utils/service';

export const apiPrefix = '/inspection/';

/**
 * ★ 周报要跑 7 天的逐日聚合，比日报慢一个量级 —— 超时必须给足。
 *   `utils/service.ts` 的 createRequestFunction 默认 5s，不显式传就必然超时。
 */
const WEEKLY_TIMEOUT = 60000;

export function GetWeekly(params: any) {
	return request({ url: apiPrefix + 'weekly/', method: 'get', params, timeout: WEEKLY_TIMEOUT });
}

/**
 * 下载周报（Word / Excel）。
 * 后端返回二进制流，出错时返回 JSON —— responseType:'blob' 下 JSON 也被包成 Blob，
 * 必须读出来判断，否则用户只会拿到一个 0 字节文件。
 */
export async function downloadWeekly(kind: 'word' | 'excel', week: string): Promise<string> {
	const res: any = await request({
		url: apiPrefix + `export/weekly/${kind}/`,
		method: 'get',
		params: { week },
		responseType: 'blob',
		timeout: WEEKLY_TIMEOUT,
	});

	const raw = res?.data instanceof Blob ? res.data : new Blob([res?.data]);
	if (raw.type && raw.type.indexOf('application/json') >= 0) {
		const text = await raw.text();
		let msg = '导出失败';
		try {
			msg = JSON.parse(text)?.msg || msg;
		} catch (e) {
			/* 保持默认提示 */
		}
		throw new Error(msg);
	}

	let filename = kind === 'word' ? `巡检周报_${week}.docx` : `巡检周报附表_${week}.xlsx`;
	const cd = res?.headers?.['content-disposition'];
	if (cd) {
		const m = cd.match(/filename=([^;]+)/i);
		if (m) {
			try {
				filename = decodeURIComponent(m[1].trim().replace(/^"|"$/g, ''));
			} catch (e) {
				/* 解析不到就用默认名 */
			}
		}
	}

	const url = URL.createObjectURL(raw);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	a.style.display = 'none';
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
	return filename;
}
