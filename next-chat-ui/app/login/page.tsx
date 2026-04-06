"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { saveClinicKey } from "@/lib/auth";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length > 0) {
      saveClinicKey(password);
      window.location.assign("/");
    } else {
      setError("合言葉を入力してください");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 border border-slate-100">
        <div className="text-center mb-8">
          <h2 className="text-sm font-semibold text-emerald-600 tracking-wider uppercase mb-2">
            Hujihana Dental Clinic
          </h2>
          <h1 className="text-3xl font-bold text-slate-800">
            藤花歯科クリニック<br />専用AI助手
          </h1>
          <p className="mt-4 text-slate-500 text-sm">
            このアプリは医院スタッフ専用です。<br />
            決められた合言葉を入力してログインしてください。
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              合言葉（パスワード）
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="block w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 text-center font-medium animate-pulse">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-4 rounded-xl transition-all shadow-lg hover:shadow-xl active:scale-[0.98]"
          >
            ログインする
          </button>
        </form>

        <div className="mt-12 text-center text-xs text-slate-400">
          &copy; 2026 藤花歯科クリニック × VEXUM
        </div>
      </div>
    </div>
  );
}
