import axios from 'axios';
import { get } from 'lodash-es';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { Action } from 'element-plus';
import { i18n } from '/@/i18n/index';

// @ts-ignore
import { errorLog, errorCreate } from './tools.ts';
// import { env } from "/src/utils/util.env";
// import { useUserStore } from "../store/modules/user";
import { Local, Session } from '/@/utils/storage';
import qs from 'qs';
import { getBaseURL } from './baseUrl';
import { successMessage } from './message.js';
/**
 * 统一错误提示：**弹窗只给业务文案，接口路径只进控制台**。
 *
 * 为什么要集中在这里：下面有 4 个业务码分支（400 / 401 / 4000 / 其他）都会
 * 弹提示，将来还可能继续加。原先每处都手拼 `${msg}: ${response.config.url}`，
 * 只要新增一处忘了剥，用户界面就会又冒出内部接口路径 —— 这条约束
 * 漏一处就等于没做。
 *
 * 为什么还要单独补一条 console：`errorCreate` 内部的 `console.error` 打印的
 * 就是传进去的 msg 本身；msg 里删掉 URL，控制台也就跟着没了。而排障时
 * 接口路径 + 原始响应体是第一手线索，所以在这里补打 ——
 * "用户看不到" 与 "开发查得到" 这两件事并不冲突。
 */
function notifyError(msg: string, url?: string, payload?: any) {
	// 控制台：保留完整线索（开发者可见、用户不可见）
	if (url) {
		console.warn(`[api] ${url}`, { msg, payload });
	}
	// 弹窗：只给业务文案
	errorCreate(msg);
}

/**
 * @description 创建请求实例
 */
function createService() {
	// 创建一个 axios 实例
	const service = axios.create({
		timeout: 20000,
		headers: {
			'Content-Type': 'application/json;charset=utf-8',
		},
		paramsSerializer: {
			serialize(params) {
				interface paramsObj {
					[key: string]: any;
				}
				let result: paramsObj = {};
				for (const [key, value] of Object.entries(params)) {
					if (value !== '') {
						result[key] = value;
					}
					if (typeof value === 'boolean') {
						result[key] = value ? 'True' : 'False';
					}
				}
				return qs.stringify(result);
			},
		},
	});
	// 请求拦截
	service.interceptors.request.use(
		(config) => config,
		(error) => {
			// 发送失败
			console.log(error);
			return Promise.reject(error);
		}
	);
	// 响应拦截
	service.interceptors.response.use(
		(response) => {
			if (response.config.responseType === 'blob') {
				return response;
			}
			// dataAxios 是 axios 返回数据中的 data
			const dataAxios = response.data;
			// 这个状态码是和后端约定的
			const { code } = dataAxios;
			// swagger判断
			if (dataAxios.swagger != undefined) {
				return dataAxios;
			}
			// 根据 code 进行判断
			if (code === undefined) {
				// 如果没有 code 代表这不是项目后端开发的接口
				errorCreate(`非标准返回：${dataAxios}， ${response.config.url}`, false);
				return dataAxios;
			} else {
				// 有 code 代表这是一个后端接口 可以进行进一步的判断
				switch (code) {
					case 400:
						// Local.clear();
						// Session.clear();
						notifyError(dataAxios.msg, response.config.url, dataAxios);
						// window.location.reload();
						break;
					case 401:
						// Local.clear();
						Session.clear();
						dataAxios.msg = i18n.global.t('message.common.authFailed');
						ElMessageBox.alert(dataAxios.msg, i18n.global.t('message.common.prompt'), {
							confirmButtonText: 'OK',
							callback: (action: Action) => {
								// window.location.reload();
							},
						});
						notifyError(dataAxios.msg, response.config.url, dataAxios);
						break;
					case 2000:
						// @ts-ignore
						if (response.config.unpack === false) {
							//如果不需要解包
							return dataAxios;
						}
						return dataAxios;
					case 4000:
						notifyError(dataAxios.msg, response.config.url, dataAxios);
						break;
					default:
						// 不是正确的 code
						notifyError(dataAxios.msg, response.config.url, dataAxios);
						break;
				}
				return Promise.reject(dataAxios);
			}
		},
		(error) => {
			const status = get(error, 'response.status');
			switch (status) {
				case 400:
					error.message = i18n.global.t('message.common.requestError');
					break;
				case 401:
					// Local.clear();
					Session.clear();
					error.message = i18n.global.t('message.common.authExpired');
					ElMessageBox.alert(error.message, i18n.global.t('message.common.prompt'), {
						confirmButtonText: 'OK',
						callback: (action: Action) => {
							window.location.reload();
						},
					});
					break;
				case 403:
					error.message = i18n.global.t('message.common.accessDenied');
					break;
				case 404:
					// ★ 弹窗文案里不出现接口路径：原写法用 requestAddressError 并把
					//   config.url 插进 {url}，用户会看到「请求地址出错: /api/...」。
					//   改成三语言都已存在、且不含路径的 endpointNotFound。
					//   这里不用像 notifyError 那样补打 console —— 本分支随后走
					//   errorLog(error)，而 console.error 打的是**整个 axios error
					//   对象**，它自带 config.url，控制台不会丢线索。
					error.message = i18n.global.t('message.common.endpointNotFound');
					break;
				case 408:
					error.message = i18n.global.t('message.common.requestTimeout');
					break;
				case 500:
					error.message = i18n.global.t('message.common.serverError');
					break;
				case 501:
					error.message = i18n.global.t('message.common.serviceNotImplemented');
					break;
				case 502:
					error.message = i18n.global.t('message.common.gatewayError');
					break;
				case 503:
					error.message = i18n.global.t('message.common.serviceUnavailable');
					break;
				case 504:
					error.message = i18n.global.t('message.common.gatewayTimeout');
					break;
				case 505:
					error.message = i18n.global.t('message.common.httpVersionNotSupported');
					break;
				default:
					break;
			}
			errorLog(error);
			if (status === 401) {
				// const userStore = useUserStore();
				// userStore.logout();
			}
			return Promise.reject(error);
		}
	);
	return service;
}

/**
 * @description 创建请求方法
 * @param {Object} service axios 实例
 */
function createRequestFunction(service: any) {
	return function (config: any) {
		const configDefault = {
			headers: {
				'Content-Type': 'application/json',
			},
			timeout: 5000,
			baseURL: getBaseURL(),
			data: {},
		};
		Object.assign(configDefault, config);
		// const token = userStore.getToken;
		const token = Session.get('token');
		if (token != null) {
			// @ts-ignore
			configDefault.headers.Authorization = 'JWT ' + token;
		}
		return service(configDefault);
	};
}

// 用于真实网络请求的实例和请求方法
export const service = createService();
export const request = createRequestFunction(service);

// 用于模拟网络请求的实例和请求方法
export const serviceForMock = createService();
export const requestForMock = createRequestFunction(serviceForMock);

/**
 * 下载文件
 * @param url
 * @param params
 * @param method
 * @param filename
 */
export const downloadFile = function ({ url, params, method, filename = i18n.global.t('message.common.defaultExportFilename') }: any) {
	// return request({ url: url, method: method, params: params })
	// 	.then((res: any) => successMessage(res.msg));
	request({
		url: url,
		method: method,
		params: params,
		responseType: 'blob'
		// headers: {Accept: 'application/vnd.openxmlformats-officedocument'}
	}).then((res: any) => {
		// console.log(res.headers['content-type']); // 根据content-type不同来判断是否异步下载
		// if (res.headers && res.headers['Content-type'] === 'application/json') return successMessage('导入任务已创建，请前往'下载中心'等待下载');
		if (res.headers['content-type'] === 'application/json') return successMessage('message.common.importTaskCreated');
		const xlsxName = window.decodeURI(res.headers['content-disposition'].split('=')[1])
		const fileName = xlsxName || `${filename}.xlsx`
		if (res) {
			const blob = new Blob([res.data], { type: 'charset=utf-8' })
			const elink = document.createElement('a')
			elink.download = fileName
			elink.style.display = 'none'
			elink.href = URL.createObjectURL(blob)
			document.body.appendChild(elink)
			elink.click()
			URL.revokeObjectURL(elink.href) // 释放URL 对象0
			document.body.removeChild(elink)
		}
	})
}
