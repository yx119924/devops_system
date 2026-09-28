import type { Router } from 'vue-router';

/**
 * 判断某个 path 在当前账号下是否真的可达。
 *
 * 本项目使用「后端控制路由」：后端下发的菜单 == 前端注册的路由。
 * 因此账号没有某个菜单权限时，该路由**根本不存在**，直接 router.push(path)
 * 会掉进 `/:path(.*)*` 兜底路由 → 页面显示 404（而不是 403）。
 *
 * 所有「写死的跳转目标」在跳之前都应过一遍本函数。
 *
 * @param router 当前路由实例（useRouter()）
 * @param path   目标路径，如 '/messageCenter'
 * @returns      注册过且可解析 → true；未注册 / 命中 404、401 兜底 → false
 */
export function isRouteAvailable(router: Router, path: string): boolean {
	if (!path) return false;
	try {
		const resolved = router.resolve(path);
		if (!resolved || !resolved.matched || resolved.matched.length === 0) return false;
		// 命中兜底记录说明该路径并未注册
		return !resolved.matched.some((m: any) => m.name === 'notFound' || m.name === 'noPower');
	} catch (e) {
		return false;
	}
}
