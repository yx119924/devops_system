import { request } from "/@/utils/service";

export function getCaptcha() {
    return request({
        url: '/captcha/',
        method: 'get',
    });
}
export function login(params: object) {
    return request({
        url: '/login/',
        method: 'post',
        data: params
    });
}

export function loginChangePwd(data: object) {
    return request({
        url: '/system/user/login_change_password/',
        method: 'post',
        data: data
    });
}

export function getUserInfo() {
    return request({
        url: '/system/user/user_info/',
        method: 'get',
    });
}

export function getBackends() {
    return request({
        url: '/dvadmin3_social_oauth2/backend/get_login_backend/',
        method: 'get',
    });
}