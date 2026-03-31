"use client";

import { useEffect, useRef } from "react";
import { ExternalLink, FileText, Loader2, Video } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Citation } from "@/lib/api/types";
import { useSourcePreview } from "@/lib/hooks/use-source-preview";
import { extractPageNumber, extractTimestamp, withPageAnchor } from "@/lib/utils";

type SourceViewerProps = {
  workspaceId: string;
  citation: Citation | null;
};

function looksLikePdf(url: string): boolean {
  return /\.pdf($|\?)/i.test(url);
}

function isVideo(mime?: string, ref_type?: string): boolean {
  return ref_type === "video" || !!mime?.startsWith("video/");
}

export function SourceViewer({ workspaceId, citation }: SourceViewerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const previewQuery = useSourcePreview(
    workspaceId,
    citation?.doc_id ?? "",
    citation?.ref ?? "",
    Boolean(citation)
  );

  const timestamp = citation ? extractTimestamp(citation.ref) : null;
  const isVideoSource = isVideo(citation?.mime_type, citation?.ref_type);

  useEffect(() => {
    if (isVideoSource && timestamp !== null && videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.play().catch(() => {
        /* ignore autoplay block */
      });
    }
  }, [isVideoSource, timestamp, citation?.doc_id]);

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
                    {isVideoSource
                      ? `タイムスタンプ: ${citation.ref}`
                      : page
                      ? `ページジャンプ: ${page}`
                      : "参照位置情報なし"}
                  </p>
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-9 items-center gap-1 rounded-md bg-blue-600 px-4 text-sm font-medium text-white hover:bg-blue-700 shadow-sm transition-all"
                  >
                    <ExternalLink className="h-4 w-4" />
                    大画面で開く
                  </a>
                </div>
                {isVideoSource ? (
                  <div className="relative aspect-video w-full overflow-hidden rounded-md border border-slate-200 bg-black">
                    <video
                      ref={videoRef}
                      src={previewUrl}
                      controls
                      className="h-full w-full"
                    />
                  </div>
                ) : (
                  <iframe
                    src={previewUrl}
                    title="source-preview"
                    className="h-[56vh] w-full rounded-md border border-slate-200 bg-white"
                  />
                )}
              </div>
            )}

            {!previewQuery.isLoading && !previewUrl && (
              <div className="flex h-[56vh] flex-col items-center justify-center gap-2 rounded-md border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-600">
                {isVideoSource ? <Video className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
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
