import { create } from 'zustand';

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  name?: string;
  organization_id: string;
  roles?: string[];
  permissions?: string[];
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
}

// Seed admin credentials to ensure instant loading during investor demos.
const DEFAULT_USER: User = {
  id: "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  email: "admin@prometheus.ai",
  first_name: "Chirag",
  last_name: "Hariprasad",
  name: "Chirag Hariprasad",
  organization_id: "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  roles: ["admin"],
  permissions: ["*"]
};

export const useAuthStore = create<AuthState>((set) => {
  const cachedToken = localStorage.getItem('twincx_token');
  const cachedUserStr = localStorage.getItem('twincx_user');
  let cachedUser: User | null = null;
  
  try {
    cachedUser = cachedUserStr ? JSON.parse(cachedUserStr) : DEFAULT_USER;
  } catch {
    cachedUser = DEFAULT_USER;
  }

  // Fallback token is "demo-token" so Axios starts sending requests immediately.
  const initialToken = cachedToken || "demo-token";

  return {
    token: initialToken,
    user: cachedUser,
    isAuthenticated: true, // Auto-authenticate for seamless demo delivery
    setAuth: (token, user) => {
      localStorage.setItem('twincx_token', token);
      localStorage.setItem('twincx_user', JSON.stringify(user));
      set({ token, user, isAuthenticated: true });
    },
    clearAuth: () => {
      localStorage.removeItem('twincx_token');
      localStorage.removeItem('twincx_user');
      set({ token: null, user: null, isAuthenticated: false });
    },
  };
});
