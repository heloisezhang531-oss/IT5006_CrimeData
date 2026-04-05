import axios from 'axios'

const api = axios.create({ baseURL: '/' })

export const fetchCurrentMonthCommunity = async () => (await api.get('/api/crime/current-month-community')).data
export const fetchPredictedRisk = async () => (await api.get('/api/crime/predicted-next-month-risk')).data
export const fetchTenYearTrend = async () => (await api.get('/api/crime/ten-year-trend')).data
export const fetchTop10PrimaryType = async () => (await api.get('/api/crime/current-month-top10-primary-type')).data
export const fetchRawData = async (limit = 200) => (await api.get(`/api/crime/raw-data?limit=${limit}`)).data

export const fetchModelMetrics = async () => (await api.get('/api/model/metrics')).data
export const fetchFeatureImportance = async () => (await api.get('/api/model/feature-importance')).data
