import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// withCredentials: true so httpOnly auth cookies (access_token / session_token)
// are sent on every request.
export const API = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  withCredentials: true,
});
export const assetUrl = (name) => (name ? `${BACKEND_URL}/api/storage/${name}` : null);
