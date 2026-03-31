"use client";

import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChatResponse, Citation } from "@/lib/api/types";

type AnswerCardProps = {
  response: ChatResponse;
  onCitationClick: (citation: Citation) => void;
};

const NOT_FOUND_HINTS = ["見つからない", "不明", "情報不足", "根拠なし", "not found"];

function isNoEvidence(response: ChatResponse): boolean {
  if (response.citations.length === 0) {
    return true;
  }
  const text = `${response.answer.conclusion} ${response.answer.details} ${response.answer.notes}`.toLowerCase();
  return NOT_FOUND_HINTS.some((hint) => text.includes(hint));
}

export function AnswerCard({ response, onCitationClick }: AnswerCardProps) {
  const noEvidence = isNoEvidence(response);

  return (
    <Card className="border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm text-slate-700">回答</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <section className="space-y-1">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">結論</h4>
          <p className="text-sm leading-relaxed text-slate-900">{response.answer.conclusion || "-"}</p>
        </section>

        <section className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">根拠</h4>
          {response.citations.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {response.citations.map((citation, index) => (
                <div key={`${citation.doc_id}-${citation.ref}-${index}`} className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onCitationClick(citation)}
                    className="max-w-[180px] truncate rounded-r-none border-r-0"
                  >
                    <span className="truncate text-xs">
                      {citation.file_name} {citation.ref}
                    </span>
                  </Button>
                  {citation.url ? (
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                      className="rounded-l-none px-2 text-blue-600 hover:text-blue-700"
                      title="ファイルを別タブで開く"
                    >
                      <a href={citation.url} target="_blank" rel="noreferrer">
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" disabled className="rounded-l-none px-2 opacity-50">
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <Badge variant="outline">引用なし</Badge>
          )}
        </section>

        <section className="space-y-1">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">補足</h4>
          <p className="text-sm leading-relaxed text-slate-700">{response.answer.details || "-"}</p>
          <p className="text-xs text-slate-500">{response.answer.notes || ""}</p>
        </section>

        {response.answer.next_actions.length > 0 && (
          <section className="space-y-1">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">次アクション</h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
              {response.answer.next_actions.map((action, index) => (
                <li key={`${action}-${index}`}>{action}</li>
              ))}
            </ul>
          </section>
        )}

        {noEvidence && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-medium">ソース内に十分な根拠が見つかりませんでした。</p>
            <p className="mt-1">
              断定はできません。追加資料例: 契約書、運用規程、会議議事録、原本PDFの高解像度版。
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
