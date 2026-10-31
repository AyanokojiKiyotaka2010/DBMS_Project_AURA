import { createContext, useContext, useState, useEffect, useCallback } from "react";
import axios from "axios";
import { setAuthToken } from "../lib/campus";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  const checkAuth = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(response.data);
    } catch (e) {
      if (e?.response?.status === 401) setAuthToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [API]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const response = await axios.post(
      `${API}/auth/login`,
      { email, password },
      { withCredentials: true }
    );
    setAuthToken(response.data.token);
    setUser(response.data.user || response.data);
    return response.data;
  };

  const register = async (name, email, password, department_id, role, year_id, division_id, roll_no) => {
    const response = await axios.post(
      `${API}/auth/register`,
      { name, email, password, department_id, role, year_id, division_id, roll_no },
      { withCredentials: true }
    );
    if (response.data.verification_required) return response.data; // must confirm the e-mail code first
    setAuthToken(response.data.token);
    setUser(response.data.user || response.data);
    return response.data;
  };

  // e-mail verification + password reset (all return the server's JSON)
  const verifyEmail = async (email, code) => {
    const response = await axios.post(`${API}/auth/verify-email`, { email, code }, { withCredentials: true });
    setAuthToken(response.data.token);
    setUser(response.data.user);
    return response.data;
  };
  const resendCode = async (email) => (await axios.post(`${API}/auth/resend-code`, { email })).data;
  const forgotPassword = async (email) => (await axios.post(`${API}/auth/forgot-password`, { email })).data;
  const resetPassword = async (email, code, new_password) =>
    (await axios.post(`${API}/auth/reset-password`, { email, code, new_password })).data;

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (e) {
      // ignore
    }
    setAuthToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, verifyEmail, resendCode, forgotPassword, resetPassword, logout, checkAuth, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
