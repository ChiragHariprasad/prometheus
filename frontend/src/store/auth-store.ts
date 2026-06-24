import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  permissions: string[];
  organization_id: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (user: User, token: string, refreshToken: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
  updateToken: (token: string, refreshToken: string) => void;
  setLoading: (loading: boolean) => void;
}

const DEV_USER: User = {
  id: "00000000-0000-0000-0000-000000000001",
  organization_id: "eb35c0b4-f66b-442b-b35a-30246d8df683",
  email: "dev@prometheus.local",
  name: "Dev User",
  roles: ["admin"],
  permissions: ["admin:*"],
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: DEV_USER,
      token: "dev-mode-token",
      refreshToken: "dev-mode-refresh-token",
      isAuthenticated: true,
      isLoading: false,
      login: (user, token, refreshToken) =>
        set({
          user,
          token,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
        }),
      logout: () =>
        set({
          user: DEV_USER,
          token: "dev-mode-token",
          refreshToken: "dev-mode-refresh-token",
          isAuthenticated: true,
          isLoading: false,
        }),
      setUser: (user) => set({ user }),
      updateToken: (token, refreshToken) => set({ token, refreshToken }),
      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: "prometheus-auth",
      partialize: (state) => ({
        // We do not persist token/user in dev-mode to ensure it resets to DEV_USER if changed
      }),
    }
  )
);

