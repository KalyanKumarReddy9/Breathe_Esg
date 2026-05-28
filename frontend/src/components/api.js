import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 30000, // 30 seconds timeout to prevent infinite hanging
});

api.interceptors.request.use(request => {
  console.log('[Frontend DEBUG] Starting Request:', request.method.toUpperCase(), request.url);
  console.log('[Frontend DEBUG] Full Request URL:', request.baseURL + request.url);
  return request;
});

api.interceptors.response.use(response => {
  console.log('[Frontend DEBUG] Response Success:', response.status, response.config.url);
  return response;
}, error => {
  console.error('[Frontend DEBUG] API Error:', error.message);
  if (error.response) {
    console.error('[Frontend DEBUG] Error Data:', error.response.data);
    console.error('[Frontend DEBUG] Error Status:', error.response.status);
  }
  return Promise.reject(error);
});

export default api;
