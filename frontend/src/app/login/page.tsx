"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff, LogIn, Bot } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please enter both username and password.");
      return;
    }
    setError("");
    setIsLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (res.ok) {
        router.push("/dashboard");
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Invalid username or password.");
      }
    } catch {
      // If backend is not running, allow proceeding for frontend dev
      setError("Could not reach the backend. Make sure the server is running.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-black font-sans relative overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[150px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 blur-[150px] rounded-full pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="z-10 w-full max-w-sm mx-4"
      >
        <div className="glass-pane p-8 flex flex-col gap-6">
          
          {/* Header */}
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center shadow-lg">
              <Bot size={28} className="text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">Meet Assistant</h1>
              <p className="text-sm text-zinc-500 mt-1">Sign in to your account</p>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            
            {/* Username */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="username" className="text-xs font-medium text-zinc-400 tracking-wide">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="your_username"
                className="w-full glass-input px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600"
              />
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-xs font-medium text-zinc-400 tracking-wide">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full glass-input px-4 py-3 pr-12 text-sm text-zinc-200 placeholder:text-zinc-600"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2"
              >
                {error}
              </motion.p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white font-medium py-3 rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-[0.98] mt-1"
            >
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <LogIn size={16} />
                  Sign In
                </>
              )}
            </button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
