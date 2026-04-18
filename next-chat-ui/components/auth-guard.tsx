"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

export function AuthGuard({
  children,
  loginRequired
}: {
  children: React.ReactNode;
  loginRequired: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);

    if (!loginRequired) {
      setAuthorized(true);
      return;
    }

    const checkAuth = () => {
      const isAuth = isAuthenticated();
      const isLoginPage = pathname === "/login";

      if (!isAuth && !isLoginPage) {
        setAuthorized(false);
        router.replace("/login");
      } else {
        setAuthorized(true);
      }
    };

    checkAuth();
  }, [loginRequired, pathname, router]);

  if (!loginRequired) return <>{children}</>;

  // ログインページへのアクセスは常に許可
  if (pathname === "/login") return <>{children}</>;

  // クライアント側でのマウント前、または認証チェック中はスピナーを表示
  if (!hasMounted || !authorized) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return <>{children}</>;
}
