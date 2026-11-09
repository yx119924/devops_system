import { request } from '/@/utils/service';

export const apiPrefix = '/inspection/';

/**
 * ★ 必须显式传 timeout：`/@/utils/service.ts` 的 `createRequestFunction` 里
 *   `configDefault.timeout = 5000` 会覆盖 axios 实例的 20000，
 *   而生成一份日报要查库 + 拉 Prometheus targets，冷启动时 5s 不够。
 */
const QUERY_TIMEOUT = 30000;
const EXPORT_TIMEOUT = 60000;

export function GetDaily(params: any) {
	return request({ url: apiPrefix + 'daily/', method: 'get', params, timeout: QUERY_TIMEOUT });
}

export function GetWeekly(params: any) {
	return request({ url: apiPrefix + 'weekly/', method: 'get', params, timeout: EXPORT_TIMEOUT });
}

/**
 * 下载报告。
 * 后端返回的是二进制流，但出错时返回的是 JSON —— 用 responseType:'blob'
 * 时 JSON 也会被包成 Blob，必须读出来判断，否则用户只会看到一个 0 字节文件。
 */
export async function downloadReport(kind: 'word' | 'excel', date: string): Promise<string> {
	const res: any = await request({
		url: apiPrefix + `export/${kind}/`,
		method: 'get',
		params: { date },
		responseType: 'blob',
		timeout: EXPORT_TIMEOUT,
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

	let filename = kind === 'word' ? `巡检日报_${date}.docx` : `巡检日报附表_${date}.xlsx`;
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
