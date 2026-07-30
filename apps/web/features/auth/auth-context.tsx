"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api, setAccessToken } from "@/lib/api";
import type { Role, User } from "@/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (action: "write" | "admin") => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

const ROLE_RANK: Record<Role, number> = { VIEWER: 0, BUYER: 1, ADMIN: 2 };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    try {
      const me = await api.get<User>("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    (async () => {
      // Try to restore a session using the refresh cookie.
      const ok = await api.refresh();
      if (ok) await loadMe();
      setLoading(false);
    })();
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string }>("/auth/login", { email, password });
    setAccessToken(res.access_token);
    await loadMe();
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }

  function can(action: "write" | "admin") {
    if (!user) return false;
    if (action === "admin") return user.role === "ADMIN";
    return ROLE_RANK[user.role] >= ROLE_RANK.BUYER;
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
