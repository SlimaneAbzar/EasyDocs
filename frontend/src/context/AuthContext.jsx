import { createContext, useContext, useState } from "react";
import api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));

  const login = async (email, password) => {
    const params = new URLSearchParams();
    params.append("username", email);
    params.append("password", password);
    const res = await api.post("/auth/login", params);
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
  };

  const register = async (email, password) => {
    const res = await api.post("/auth/register", { email, password });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
