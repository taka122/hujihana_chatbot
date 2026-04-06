"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, LockKeyhole } from "lucide-react";

import { clearClinicKey, saveClinicKey } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

export default function LoginPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    clearClinicKey();
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    try {
      setIsSubmitting(true);
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password })
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message ?? "ログインに失敗しました。");
      }

      saveClinicKey(password);
      toast({
        title: "ログインしました",
        description: "チャット画面へ移動します。"
      });
      router.replace("/");
      router.refresh();
    } catch (error) {
      toast({
        title: "ログイン失敗",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md border-slate-200 shadow-sm">
        <CardHeader className="space-y-3">
          <div className="flex items-center gap-2 text-slate-600">
            <LockKeyhole className="h-5 w-5" />
            <p className="text-sm font-semibold">藤花歯科クリニック専用Chatbot</p>
          </div>
          <div>
            <CardTitle>ログイン</CardTitle>
            <CardDescription>利用のたびに共通パスワードを入力してください。</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleSubmit}>
            <Input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="共通パスワード"
              autoComplete="current-password"
            />
            <Button className="w-full gap-2" type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              ログイン
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
