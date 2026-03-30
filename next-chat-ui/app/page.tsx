"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { useCreateWorkspace, useWorkspaces } from "@/lib/hooks/use-workspaces";

export default function HomePage() {
  const router = useRouter();
  const { toast } = useToast();
  const [name, setName] = useState("デモWorkspace");
  const { data: workspaces, isLoading, isError, error, refetch } = useWorkspaces(true);
  const createWorkspace = useCreateWorkspace();

  useEffect(() => {
    if (workspaces && workspaces.length > 0) {
      router.replace(`/w/${workspaces[0].id}`);
    }
  }, [router, workspaces]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      toast({
        title: "Workspace名を入力してください",
        variant: "destructive"
      });
      return;
    }

    try {
      const workspace = await createWorkspace.mutateAsync({ name: trimmed });
      toast({ title: "Workspaceを作成しました", description: workspace.name });
      router.replace(`/w/${workspace.id}`);
    } catch (error) {
      toast({
        title: "Workspace作成に失敗しました",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Universal RAG PoC</CardTitle>
          <CardDescription>最初にWorkspaceを選択または作成します。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && <p className="text-sm text-slate-500">Workspace一覧を取得中...</p>}
          {isError && (
            <div className="space-y-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <p>Workspace一覧の取得に失敗しました。</p>
              <p className="text-xs text-red-600">接続先API設定とバックエンド起動状態を確認してください。</p>
              {error instanceof Error && <p className="text-xs text-red-600">{error.message}</p>}
              <Button variant="outline" size="sm" onClick={() => void refetch()}>
                再試行
              </Button>
            </div>
          )}
          {!isLoading && !isError && (!workspaces || workspaces.length === 0) && (
            <form className="space-y-3" onSubmit={handleCreate}>
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Workspace名" />
              <Button className="w-full" type="submit" disabled={createWorkspace.isPending}>
                {createWorkspace.isPending ? "作成中..." : "Workspace作成"}
              </Button>
            </form>
          )}
          {!isLoading && workspaces && workspaces.length > 0 && (
            <p className="text-sm text-slate-500">Workspaceへ移動中...</p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
