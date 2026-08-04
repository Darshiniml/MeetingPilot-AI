import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { motion } from "framer-motion";
import api from "../../services/api";
import { Mail, Lock } from "lucide-react";
import { Button } from "../../components/ui/Button";

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.post("/auth/login", { email, password });
      login(response.data.access_token, response.data.refresh_token);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid email or password combination.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-dark text-slate-100 flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Decorative Blur Blobs */}
      <div className="absolute top-1/4 left-1/3 w-80 h-80 rounded-full bg-indigo-600/10 blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 rounded-full bg-violet-600/10 blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-8 shadow-2xl relative z-10 text-left"
      >
        {/* Title */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-white shadow-xl shadow-indigo-500/20 text-lg mx-auto mb-4">
            MP
          </div>
          <h2 className="font-display font-bold text-xl text-slate-100 tracking-tight">Welcome Back</h2>
          <p className="text-xs text-zinc-500 mt-1">Sign in to sync your meetings & schedules</p>
        </div>

        {error && (
          <div className="p-3 mb-5 rounded-lg border border-red-500/20 bg-red-500/5 text-xs font-semibold text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              />
            </div>
          </div>

          <Button variant="primary" fullWidth type="submit" disabled={loading} className="py-2.5 mt-2">
            {loading ? "Authenticating..." : "Login"}
          </Button>
        </form>

        <p className="text-center text-xs text-zinc-500 mt-6">
          Don't have an account?{" "}
          <Link to="/register" className="text-indigo-400 font-semibold hover:underline">
            Create account
          </Link>
        </p>
      </motion.div>
    </div>
  );
};

export default LoginPage;
