"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { useCreateWorkspace, useDeleteWorkspace, useWorkspaces } from "@/lib/hooks/use-workspaces";

type WorkspaceSelectorProps = {
  currentWorkspaceId: string;
};

export function WorkspaceSelector({ currentWorkspaceId }: WorkspaceSelectorProps) {
  const router = useRouter();
  const { toast } = useToast();
  const { data: workspaces, isLoading } = useWorkspaces();
  const createWorkspace = useCreateWorkspace();
  const deleteWorkspace = useDeleteWorkspace();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");

  const currentWorkspace = useMemo(() => {
    if (!workspaces || workspaces.length === 0) {
      return null;
    }

    const matched = workspaces.find((workspace) => workspace.id === currentWorkspaceId);
    if (matched) {
      return matched;
    }
    return workspaces[0];
  }, [currentWorkspaceId, workspaces]);

  const currentValue = currentWorkspace?.id;

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      toast({ title: "Workspace名を入力してください", variant: "destructive" });
      return;
    }

    try {
      const workspace = await createWorkspace.mutateAsync({ name: trimmed });
      toast({
        title: "Workspaceを作成しました",
        description: workspace.name
      });
      setDialogOpen(false);
      setName("");
      router.push(`/w/${workspace.id}`);
    } catch (error) {
      toast({
        title: "Workspace作成に失敗しました",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    }
  };

  const handleDeleteCurrentWorkspace = async () => {
    if (!currentWorkspace) {
      return;
    }

    const remaining = (workspaces ?? []).filter((workspace) => workspace.id !== currentWorkspace.id);
    const confirmed = window.confirm(
      `「${currentWorkspace.name}」を削除します。関連ドキュメントとチャンクも削除され、この操作は取り消せません。`
    );
    if (!confirmed) {
      return;
    }

    try {
      await deleteWorkspace.mutateAsync(currentWorkspace.id);
      toast({
        title: "Workspaceを削除しました",
        description: currentWorkspace.name
      });
      if (remaining.length > 0) {
        router.push(`/w/${remaining[0].id}`);
        return;
      }
      router.push("/");
    } catch (error) {
      toast({
        title: "Workspace削除に失敗しました",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Select
        value={currentValue}
        onValueChange={(workspaceId) => {
          if (workspaceId !== currentWorkspaceId) {
            router.push(`/w/${workspaceId}`);
          }
        }}
      >
        <SelectTrigger className="w-[220px] bg-white">
          <SelectValue placeholder={isLoading ? "読み込み中..." : "Workspaceを選択"} />
        </SelectTrigger>
        <SelectContent>
          {(workspaces ?? []).map((workspace) => (
            <SelectItem key={workspace.id} value={workspace.id}>
              {workspace.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="icon" aria-label="workspace create">
            <Plus className="h-4 w-4" />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle>新規Workspace作成</DialogTitle>
              <DialogDescription>名前を入力して作成すると、すぐに切り替わります。</DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              <Input
                placeholder="例: 企業A"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <DialogFooter className="mt-4">
              <Button type="submit" disabled={createWorkspace.isPending}>
                {createWorkspace.isPending ? "作成中..." : "作成"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <Button
        variant="destructive"
        size="icon"
        aria-label="workspace delete"
        disabled={!currentWorkspace || deleteWorkspace.isPending || createWorkspace.isPending}
        onClick={() => void handleDeleteCurrentWorkspace()}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
