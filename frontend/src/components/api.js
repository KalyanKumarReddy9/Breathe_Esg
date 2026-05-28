import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 30000, // 30 seconds timeout to prevent infinite hanging
});

export default api;
