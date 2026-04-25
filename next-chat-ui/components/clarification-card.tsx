"use client";

import { HelpCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChatClarification } from "@/lib/api/types";

type ClarificationCardProps = {
  clarification: ChatClarification;
  onSelect: (option: string) => void;
  disabled?: boolean;
};

/**
 * 曖昧クエリに対する聞き返しUI。
 * 候補ボタンをクリックすると、自動でその文言を再質問する。
 * ユーザーは候補を選ばず、自由入力で別の質問を投げることもできる。
 */
export function ClarificationCard({ clarification, onSelect, disabled }: ClarificationCardProps) {
  return (
    <Card className="border-amber-200 bg-amber-50/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm text-amber-900">
          <HelpCircle className="h-4 w-4" />
          もう少し詳しく教えてください
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-relaxed text-slate-800">{clarification.question}</p>

        {clarification.options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {clarification.options.map((option, index) => (
              <Button
                key={`${option}-${index}`}
                type="button"
                variant="outline"
                size="sm"
                disabled={disabled}
                onClick={() => onSelect(option)}
                className="border-amber-300 bg-white text-sm hover:bg-amber-100"
              >
                {option}
              </Button>
            ))}
          </div>
        )}

        <p className="text-xs text-slate-500">
          ボタンをタップするとそのまま質問できます。直接入力でも構いません。
        </p>
      </CardContent>
    </Card>
  );
}
