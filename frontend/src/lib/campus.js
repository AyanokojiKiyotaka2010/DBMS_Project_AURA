import axios from "axios";
import { useCallback, useEffect, useState } from "react";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
axios.defaults.withCredentials = true;

// Token auth: the login cookie is blocked by many browsers when the site and the API are on different
// domains (Vercel vs Render), so the JWT is also kept here and sent as "Authorization: Bearer".
const TOKEN_KEY = "aura_token";
export const getAuthToken = () => {
  try { return localStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; }
};
export function setAuthToken(token) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch {}
  if (token) axios.defaults.headers.common.Authorization = `Bearer ${token}`;
  else delete axios.defaults.headers.common.Authorization;
}
setAuthToken(getAuthToken());


export const CAN_POST_ANNOUNCEMENT = (r) =>
  ["CR", "DCR", "Administrator", "Professor"].includes(r);
export const IS_ADMIN = (r) => r === "Administrator";
export const CAN_VIEW_DIGEST = (r) =>
  ["CR", "DCR", "Administrator"].includes(r);

export const CAN_RUN_REPORTS = (r) =>
  ["Administrator", "Professor", "CR", "DCR"].includes(r);
export const CAN_MANAGE_CLUBS = (r) =>
  ["Administrator", "Convener", "Professor"].includes(r);
export const CAN_CLASS_TOOLS = (r) =>
  ["Administrator", "Professor", "CR", "DCR"].includes(r);

/** Departments / years / divisions are admin-managed data, not constants. */
export function useStructure() {
  const [s, setS] = useState({ departments: [], years: [], divisions: [], loaded: false });
  const reload = useCallback(
    () =>
      axios
        .get(`${API}/meta/structure`)
        .then((r) => setS({ ...r.data, loaded: true }))
        .catch(() => setS((p) => ({ ...p, loaded: true }))),
    []
  );
  useEffect(() => { reload(); }, [reload]);
  return { ...s, reload, setStructure: (d) => setS({ ...d, loaded: true }) };
}
