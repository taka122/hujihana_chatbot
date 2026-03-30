"use client";

import { ExternalLink, FileText, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Citation } from "@/lib/api/types";
import { useSourcePreview } from "@/lib/hooks/use-source-preview";
import { extractPageNumber, withPageAnchor } from "@/lib/utils";

type SourceViewerProps = {
  workspaceId: string;
  citation: Citation | null;
};

function looksLikePdf(url: string): boolean {
  return /\.pdf($|\?)/i.test(url);
}

export function SourceViewer({ workspaceId, citation }: SourceViewerProps) {
  const previewQuery = useSourcePreview(
    workspaceId,
    citation?.doc_id ?? "",
    citation?.ref ?? "",
    Boolean(citation)
  );

  if (!citation) {
    return (
      <Card className="h-full border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Source Viewer</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[65vh] items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
            引用をクリックするとここに原文を表示します。
          </div>
        </CardContent>
      </Card>
    );
  }

  const page = extractPageNumber(citation.ref);
  const previewUrl =
    previewQuery.data?.url && looksLikePdf(previewQuery.data.url)
      ? withPageAnchor(previewQuery.data.url, page)
      : previewQuery.data?.url;

  const previewSnippet = citation.snippet || previewQuery.data?.snippet || previewQuery.data?.text || "";

  return (
    <Card className="h-full border-slate-200">
      <CardHeader className="space-y-2 pb-3">
        <CardTitle className="text-base">Source Viewer</CardTitle>
        <div className="space-y-1 text-sm text-slate-600">
          <p className="font-medium text-slate-900">{citation.file_name}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{citation.ref_type}</Badge>
            <span>{citation.ref}</span>
            {citation.score != null && <span>score: {citation.score.toFixed(3)}</span>}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="preview" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="preview">Preview</TabsTrigger>
            <TabsTrigger value="snippet">Snippet</TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="space-y-3">
            {previewQuery.isLoading && (
              <div className="flex h-[56vh] items-center justify-center gap-2 rounded-md border border-slate-200 bg-slate-50 text-sm text-slate-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                ソースを読み込み中...
              </div>
            )}

            {previewQuery.isError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                プレビュー取得に失敗しました。引用スニペットは下のタブで確認できます。
              </div>
            )}

            {!previewQuery.isLoading && !previewQuery.isError && previewUrl && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-500">
                    {page ? `ページジャンプ: ${page}` : "参照位置のページ情報なし"}
                  </p>
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-9 items-center gap-1 rounded-md border border-slate-200 px-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
                  >
                    別タブで開く
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <iframe
                  src={previewUrl}
                  title="source-preview"
                  className="h-[56vh] w-full rounded-md border border-slate-200 bg-white"
                />
              </div>
            )}

            {!previewQuery.isLoading && !previewUrl && (
              <div className="flex h-[56vh] flex-col items-center justify-center gap-2 rounded-md border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-600">
                <FileText className="h-5 w-5" />
                プレビューURLがないためスニペット表示のみ利用できます。
              </div>
            )}
          </TabsContent>

          <TabsContent value="snippet">
            <div className="max-h-[56vh] space-y-2 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">引用テキスト</p>
              {previewSnippet ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                  <mark className="rounded bg-yellow-200/80 px-1 py-0.5">{previewSnippet}</mark>
                </p>
              ) : (
                <p className="text-sm text-slate-500">スニペットが取得できませんでした。</p>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
