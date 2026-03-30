"use client";

import { useEffect, useState } from "react";
import { KeyRound, Settings } from "lucide-react";

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
import { useToast } from "@/components/ui/use-toast";
import {
  clearApiKey,
  getStoredApiKey,
  isApiKeyHeaderSafe,
  saveApiKey
} from "@/lib/api-key-store";

export function ApiKeySettingsFab() {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [configured, setConfigured] = useState(false);

  useEffect(() => {
    const current = getStoredApiKey();
    setInputValue(current ?? "");
    setConfigured(Boolean(current));
  }, [open]);

  const handleSave = () => {
    if (inputValue.trim().length > 0 && !isApiKeyHeaderSafe(inputValue)) {
      toast({
        title: "API KEYの形式が不正です",
        description: "ヘッダに送れない文字（全角文字・絵文字・改行など）が含まれています。",
        variant: "destructive"
      });
      return;
    }
    saveApiKey(inputValue);
    const current = getStoredApiKey();
    setConfigured(Boolean(current));
    setOpen(false);
    toast({
      title: current ? "API KEYを保存しました" : "API KEY設定を削除しました",
      description: current ? "次回リクエストから反映されます。" : "環境変数のキーを使います。"
    });
  };

  const handleClear = () => {
    clearApiKey();
    setInputValue("");
    setConfigured(false);
    toast({
      title: "API KEY設定を削除しました",
      description: "環境変数のキーを使います。"
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          type="button"
          size="icon"
          className="fixed bottom-5 left-5 z-40 h-12 w-12 rounded-full shadow-lg"
          aria-label="API key settings"
        >
          <Settings className="h-5 w-5" />
          {configured && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-400" />}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-4 w-4" />
            Gemini API KEY 設定
          </DialogTitle>
          <DialogDescription>Geminiキーを上書き設定できます。</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Input
            type="password"
            autoComplete="off"
            placeholder="sk-... または AIza..."
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
          />
          <p className="text-xs text-slate-500">`X-GEMINI-API-Key` ヘッダに設定されます。</p>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClear}>
            クリア
          </Button>
          <Button type="button" onClick={handleSave}>
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
