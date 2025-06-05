import axios from 'axios'

const state = {
  token: localStorage.getItem('token') || '',
  userInfo: null
}

const mutations = {
  SET_TOKEN(state, token) {
    state.token = token
    localStorage.setItem('token', token)
  },
  SET_USER_INFO(state, userInfo) {
    state.userInfo = userInfo
  },
  CLEAR_USER_STATE(state) {
    state.token = ''
    state.userInfo = null
    localStorage.removeItem('token')
  }
}

const actions = {
  async login({ commit }, loginData) {
    const response = await axios.post('http://localhost:8000/api/system/login/', loginData)
    const { token, user } = response.data
    commit('SET_TOKEN', token)
    commit('SET_USER_INFO', user)
    return response
  },

  logout({ commit }) {
    commit('CLEAR_USER_STATE')
  }
}

const getters = {
  isAuthenticated: state => !!state.token,
  userInfo: state => state.userInfo
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
}