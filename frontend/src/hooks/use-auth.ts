"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { apiClient, LoginRequest, RegisterRequest } from "@/lib/api-client";

export function useAuth() {
  const router = useRouter();
  const {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout: storeLogout,
    setUser,
    updateToken,
    setLoading,
  } = useAuthStore();

  const loginAction = useCallback(
    async (data: LoginRequest) => {
      setLoading(true);
      try {
        const response = await apiClient.login(data);
        login(response.user, response.access_token, response.refresh_token);
        router.push("/dashboard");
        return response;
      } catch (error) {
        setLoading(false);
        throw error;
      }
    },
    [login, router, setLoading]
  );

  const registerAction = useCallback(
    async (data: RegisterRequest) => {
      setLoading(true);
      try {
        const response = await apiClient.register(data);
        login(response.user, response.access_token, response.refresh_token);
        router.push("/dashboard");
        return response;
      } catch (error) {
        setLoading(false);
        throw error;
      }
    },
    [login, router, setLoading]
  );

  const logoutAction = useCallback(async () => {
    try {
      await apiClient.logout();
    } catch {
      // Ignore logout API errors
    } finally {
      storeLogout();
      router.push("/login");
    }
  }, [storeLogout, router]);

  const fetchProfile = useCallback(async () => {
    try {
      const profile = await apiClient.getProfile();
      setUser(profile);
      return profile;
    } catch {
      storeLogout();
      router.push("/login");
      return null;
    }
  }, [setUser, storeLogout, router]);

  const hasPermission = useCallback(
    (permission: string) => {
      return user?.permissions?.includes(permission) ?? false;
    },
    [user]
  );

  const hasRole = useCallback(
    (role: string) => {
      return user?.roles?.includes(role) ?? false;
    },
    [user]
  );

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login: loginAction,
    register: registerAction,
    logout: logoutAction,
    fetchProfile,
    hasPermission,
    hasRole,
  };
}
