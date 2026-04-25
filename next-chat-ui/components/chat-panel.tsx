"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, SendHorizontal } from "lucide-react";

import { AnswerCard } from "@/components/answer-card";
import { ClarificationCard } from "@/components/clarification-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import type { ChatResponse, Citation } from "@/lib/api/types";
import { useChat } from "@/lib/hooks/use-chat";

type ChatTurn = {
  id: string;
  query: string;
  response?: ChatResponse;
  error?: string;
  isLoading?: boolean;
};

type ChatPanelProps = {
  workspaceId: string;
  onCitationClick: (citation: Citation) => void;
};

function storageKey(workspaceId: string): string {
  return `universal-rag-chat-history-${workspaceId}`;
}

export function ChatPanel({ workspaceId, onCitationClick }: ChatPanelProps) {
  const { toast } = useToast();
  const chat = useChat(workspaceId);
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTurns([]);
    const raw = window.localStorage.getItem(storageKey(workspaceId));
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw) as ChatTurn[];
      if (Array.isArray(parsed)) {
        setTurns(parsed.filter((turn) => !turn.isLoading));
      }
    } catch {
      window.localStorage.removeItem(storageKey(workspaceId));
    }
  }, [workspaceId]);

  useEffect(() => {
    window.localStorage.setItem(
      storageKey(workspaceId),
      JSON.stringify(turns.filter((turn) => !turn.isLoading))
    );
  }, [workspaceId, turns]);

  useEffect(() => {
    const node = logRef.current;
    if (!node) {
      return;
    }
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [turns]);

  const pendingCount = useMemo(() => turns.filter((turn) => turn.isLoading).length, [turns]);

  const sendQuery = async (query: string) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setTurns((prev) => [...prev, { id, query, isLoading: true }]);

    try {
      const response = await chat.mutateAsync(query);
      setTurns((prev) =>
        prev.map((turn) => (turn.id === id ? { id, query, response, isLoading: false } : turn))
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "不明なエラー";
      setTurns((prev) =>
        prev.map((turn) =>
          turn.id === id
            ? {
                id,
                query,
                error: `${message}。接続先APIとドキュメント状態を確認してください。`,
                isLoading: false
              }
            : turn
        )
      );

      toast({
        title: "問い合わせに失敗しました",
        description: message,
        variant: "destructive"
      });
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = input.trim();
    if (!query || chat.isPending) {
      return;
    }
    setInput("");
    await sendQuery(query);
  };

  const handleKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const query = input.trim();
      if (!query || chat.isPending) {
        return;
      }
      setInput("");
      await sendQuery(query);
    }
  };

  return (
    <Card className="h-full border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Chat</CardTitle>
      </CardHeader>
      <CardContent className="flex h-[76vh] flex-col gap-3 pt-0">
        <div ref={logRef} className="flex-1 space-y-3 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 p-3">
          {turns.length === 0 && (
            <p className="text-sm text-slate-500">
              質問を入力すると回答と引用が表示されます。例: 「契約解除の条件を教えて」
            </p>
          )}

          {turns.map((turn) => (
            <div key={turn.id} className="space-y-2">
              <div className="ml-auto w-fit max-w-[92%] rounded-lg bg-slate-900 px-3 py-2 text-sm text-white">
                {turn.query}
              </div>

              {turn.isLoading && (
                <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  回答を生成中...
                </div>
              )}

              {turn.error && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  <p className="font-medium">回答取得エラー</p>
                  <p className="mt-1">{turn.error}</p>
                </div>
              )}

              {turn.response?.clarification?.needed ? (
                <ClarificationCard
                  clarification={turn.response.clarification}
                  disabled={chat.isPending}
                  onSelect={(option) => {
                    void sendQuery(option);
                  }}
                />
              ) : (
                turn.response && (
                  <AnswerCard response={turn.response} onCitationClick={onCitationClick} />
                )
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-1.5">
          <Textarea
            placeholder="質問を入力（Enterで送信 / Shift+Enterで改行）"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              void handleKeyDown(event);
            }}
            rows={2}
            className="min-h-[64px] bg-white"
          />
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>{pendingCount > 0 ? `送信中: ${pendingCount}` : "準備完了"}</span>
            <Button type="submit" disabled={chat.isPending || input.trim().length === 0} className="gap-2">
              {chat.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
              送信
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
