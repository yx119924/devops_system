import {createRouter, createWebHashHistory} from 'vue-router';
import NProgress from 'nprogress';
import 'nprogress/nprogress.css';
import pinia from '/@/stores/index';
import {storeToRefs} from 'pinia';
import {useKeepALiveNames} from '/@/stores/keepAliveNames';
import {useRoutesList} from '/@/stores/routesList';
import {useThemeConfig} from '/@/stores/themeConfig';
import {Session} from '/@/utils/storage';
import {NextLoading} from '/@/utils/loading';
import {dynamicRoutes, notFoundAndNoPower, staticRoutes} from '/@/router/route';
import {initFrontEndControlRoutes} from '/@/router/frontEnd';
import {initBackEndControlRoutes, setRouters} from '/@/router/backEnd';
import {useFrontendMenuStore} from "/@/stores/frontendMenu";
import {useTagsViewRoutes} from "/@/stores/tagsViewRoutes";
import {toRaw} from "vue";
import {checkVersion} from "/@/utils/upgrade";

/**
 * 1、前端控制路由时：isRequestRoutes 为 false，需要写 roles，需要走 setFilterRoute 方法。
 * 2、后端控制路由时：isRequestRoutes 为 true，不需要写 roles，不需要走 setFilterRoute 方法），
 * 相关方法已拆解到对应的 `backEnd.ts` 与 `frontEnd.ts`（他们互不影响，不需要同时改 2 个文件）。
 * 特别说明：
 * 1、前端控制：路由菜单由前端去写（无菜单管理界面，有角色管理界面），角色管理中有 roles 属性，需返回到 userInfo 中。
 * 2、后端控制：路由菜单由后端返回（有菜单管理界面、有角色管理界面）
 */

// 读取 `/src/stores/themeConfig.ts` 是否开启后端控制路由配置
const storesThemeConfig = useThemeConfig(pinia);
const {themeConfig} = storeToRefs(storesThemeConfig);
const {isRequestRoutes} = themeConfig.value;
import {useUserInfo} from "/@/stores/userInfo";
const { userInfos } = storeToRefs(useUserInfo());

/**
 * 创建一个可以被 Vue 应用程序使用的路由实例
 * @method createRouter(options: RouterOptions): Router
 * @link 参考：https://next.router.vuejs.org/zh/api/#createrouter
 */
export const router = createRouter({
    history: createWebHashHistory(),
    /**
     * 说明：
     * 1、notFoundAndNoPower 默认添加 404、401 界面，防止一直提示 No match found for location with path 'xxx'
     * 2、backEnd.ts(后端控制路由)、frontEnd.ts(前端控制路由) 中也需要加 notFoundAndNoPower 404、401 界面。
     *    防止 404、401 不在 layout 布局中，不设置的话，404、401 界面将全屏显示
     */
    routes: [...notFoundAndNoPower, ...staticRoutes]
});

/**
 * 路由多级嵌套数组处理成一维数组
 * @param arr 传入路由菜单数据数组
 * @returns 返回处理后的一维路由菜单数组
 */
export function formatFlatteningRoutes(arr: any) {
    if (arr.length <= 0) return false;
    for (let i = 0; i < arr.length; i++) {
        if (arr[i].children) {
            arr = arr.slice(0, i + 1).concat(arr[i].children, arr.slice(i + 1));
        }
    }
    return arr;
}

/**
 * 一维数组处理成多级嵌套数组（只保留二级：也就是二级以上全部处理成只有二级，keep-alive 支持二级缓存）
 * @description isKeepAlive 处理 `name` 值，进行缓存。顶级关闭，全部不缓存
 * @link 参考：https://v3.cn.vuejs.org/api/built-in-components.html#keep-alive
 * @param arr 处理后的一维路由菜单数组
 * @returns 返回将一维数组重新处理成 `定义动态路由（dynamicRoutes）` 的格式
 */
export function formatTwoStageRoutes(arr: any) {
    if (arr.length <= 0) return false;
    const newArr: any = [];
    const cacheList: Array<string> = [];
    arr.forEach((v: any) => {
        if (v.path === '/') {
            newArr.push({component: v.component,name: v.name,path: v.path,redirect: v.redirect,meta: v.meta,children: []});
        } else {
            // 判断是否是动态路由（xx/:id/:name），用于 tagsView 等中使用
            // 修复：https://gitee.com/lyt-top/vue-next-admin/issues/I3YX6G
            if (v.path.indexOf('/:') > -1) {
                v.meta['isDynamic'] = true;
                v.meta['isDynamicPath'] = v.path;
            }
            newArr[0].children.push({...v});
            // 存 name 值，keep-alive 中 include 使用，实现路由的缓存
            // 路径：/@/layout/routerView/parent.vue
            if (newArr[0].meta.isKeepAlive && v.meta.isKeepAlive && v.component_name != "") {
                cacheList.push(v.name);
                const stores = useKeepALiveNames(pinia);
                stores.setCacheKeepAlive(cacheList);
            }
        }
    });
    return newArr;
}

const frameOutRoutes = staticRoutes.map(item => item.path)

const checkToken = ()=>{
    const urlParams = new URLSearchParams(window.location.search);
    const _oauth2_token = urlParams.get('_oauth2_token');
    if (_oauth2_token) {
        Session.set('token', _oauth2_token);
        const cleanUrl = window.location.href.split('?')[0];
        window.history.replaceState({}, '', cleanUrl);
        useUserInfo(pinia).setUserInfos();

    }
}
// 路由加载前
router.beforeEach(async (to, from, next) => {
    // 检查浏览器本地版本与线上版本是否一致，判断是否需要刷新页面进行更新
    // ★ checkVersion 打的是构建期才生成的 version-build（utils/upgrade.ts:34），
    //   一旦 404 / 超时 / 网络抖动，裸 await 会让整个守卫 reject ⇒ 导航中止、
    //   next() 永不执行 ⇒ 全局 loading 永久残留。版本检查只是锦上添花，
    //   失败必须放过，不能拖死导航。（2026-11-02 事故复盘）
    try {
        await checkVersion()
    } catch (e) {
        console.warn('[router] 版本检查失败，已忽略，不影响导航', e)
    }
    checkToken()
    NProgress.configure({showSpinner: false});
    if (to.meta.title) NProgress.start();
    const token = Session.get('token');
    if (to.path === '/login' && !token) {
        next();
        NProgress.done();
    } else {
        if (!token) {
            next(`/login?redirect=${to.path}&params=${JSON.stringify(to.query ? to.query : to.params)}`);
            Session.clear();
            NProgress.done();
        }else if (token && to.path === '/login' && userInfos.value.pwd_change_count===0 ) {
            next('/login');
            NProgress.done();
        } else if (token && to.path === '/login' && userInfos.value.pwd_change_count>0) {
            next('/home');
            NProgress.done();
        }else if(token &&  frameOutRoutes.includes(to.path) ){
            next()
        } else {
            const storesRoutesList = useRoutesList(pinia);
            const {routesList} = storeToRefs(storesRoutesList);
            if (routesList.value.length === 0) {
                // ★ 必须 try/catch：初始化会串行 await 用户信息 / 按钮权限 / 菜单等接口。
                //   token 过期时后端返回 HTTP 200 + body 里 code=401（见后端
                //   dvadmin/utils/exception.py:95，ErrorResponse 的 status 默认 None），
                //   拦截器 Session.clear() 后 Promise.reject ⇒ 这里 await 抛错 ⇒
                //   本守卫整体 reject ⇒ vue-router 只「中止导航」，不会替你调 next()。
                //   后果：afterEach 不跑、目标组件不挂载、.loading-next 永不移除
                //   ⇒ 白屏 + 9 个小方块无限转圈，只能手动 F5。（2026-11-02 实测）
                try {
                    if (isRequestRoutes) {
                        // 后端控制路由：路由数据初始化，防止刷新时丢失
                        await initBackEndControlRoutes();
                    } else {
                        // https://gitee.com/lyt-top/vue-next-admin/issues/I5F1HP
                        await initFrontEndControlRoutes();
                    }
                    // 解决刷新时，一直跳 404 页面问题，关联问题 No match found for location with path 'xxx'
                    // to.query 防止页面刷新时，普通路由带参数时，参数丢失。动态路由（xxx/:id/:name"）isDynamic 无需处理
                    next({ path: to.path, query: to.query });
                } catch (e) {
                    // 兜底三件事：清掉已失效的登录态、收掉全局 loading 与进度条、回登录页。
                    // 少任何一件，用户看到的就是「一直转圈」或「停在白屏」。
                    console.warn('[router] 路由初始化失败，已清理登录态并回登录页', e)
                    Session.clear()
                    NextLoading.done()
                    NProgress.done()
                    next(`/login?redirect=${to.path}`)
                }
            } else {
                next();
            }
        }
    }
});

// 路由加载后
router.afterEach(() => {
    NProgress.done();
});

// ★ 导航期异常兜底：守卫抛错、动态 chunk 加载失败（发版后旧 index.html 引用旧 hash
//   就会这样 —— login 本身就是懒加载 chunk，加载失败时导航会静默中止）都会走到这里。
//   没有这一层，用户看到的同样是「白屏 + 永久转圈」，而且没有任何提示。
router.onError((error) => {
    console.error('[router] 导航异常，已收掉全局 loading', error)
    NextLoading.done()
    NProgress.done()
});

// 导出路由
export default router;
