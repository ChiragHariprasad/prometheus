"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { Bot, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showMfa, setShowMfa] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    email: "",
    password: "",
    mfa_code: "",
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login({
        email: form.email,
        password: form.password,
        mfa_code: form.mfa_code || undefined,
      });
    } catch (err: unknown) {
      const apiError = err as { response?: { status?: number; data?: { detail?: string } } };
      if (apiError?.response?.status === 428) {
        setShowMfa(true);
      } else {
        setError(
          apiError?.response?.data?.detail || "Invalid credentials"
        );
      }
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-gradient-to-br from-prometheus-900 via-prometheus-800 to-prometheus-950 p-12 text-white">
        <div className="flex items-center gap-3">
          <Bot className="h-8 w-8" />
          <span className="text-2xl font-bold">PROMETHEUS</span>
        </div>
        <div className="space-y-6">
          <h1 className="text-4xl font-bold leading-tight">
            Intelligent Customer Twins
            <br />
            <span className="text-prometheus-300">
              for Personalized Marketing
            </span>
          </h1>
          <p className="text-lg text-prometheus-200 max-w-md">
            AI-powered platform that creates digital twins of your customers
            to predict behavior, personalize engagement, and maximize revenue.
          </p>
          <div className="grid grid-cols-3 gap-4 pt-6">
            <div className="rounded-lg bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-2xl font-bold">10M+</p>
              <p className="text-sm text-prometheus-200">Events Processed</p>
            </div>
            <div className="rounded-lg bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-2xl font-bold">99.9%</p>
              <p className="text-sm text-prometheus-200">Prediction Accuracy</p>
            </div>
            <div className="rounded-lg bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-2xl font-bold">3.2x</p>
              <p className="text-sm text-prometheus-200">Revenue Uplift</p>
            </div>
          </div>
        </div>
        <p className="text-sm text-prometheus-300">
          &copy; 2026 PROMETHEUS. All rights reserved.
        </p>
      </div>

      <div className="flex items-center justify-center p-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4 lg:hidden">
              <Bot className="h-10 w-10 text-prometheus-500" />
            </div>
            <CardTitle className="text-2xl">Welcome back</CardTitle>
            <CardDescription>
              Sign in to your PROMETHEUS account
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              {error && (
                <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={form.email}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      email: e.target.value,
                    }))
                  }
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={form.password}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        password: e.target.value,
                      }))
                    }
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {showMfa && (
                <div className="space-y-2">
                  <Label htmlFor="mfa">MFA Code</Label>
                  <Input
                    id="mfa"
                    placeholder="Enter 6-digit code"
                    maxLength={6}
                    value={form.mfa_code}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        mfa_code: e.target.value,
                      }))
                    }
                  />
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
