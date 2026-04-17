"use client";

import { useState } from "react";
import { AlertCircle, Download, ExternalLink, FileWarning, Loader2, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/use-toast";
import { fetchDocPresignedUrl } from "@/lib/api/client";
import type { Doc } from "@/lib/api/types";
import { useDeleteDoc } from "@/lib/hooks/use-delete-doc";
import { formatDateTime, toDownloadUrl } from "@/lib/utils";

type DocTableProps = {
  workspaceId: string;
  docs: Doc[];
  isLoading: boolean;
  isError: boolean;
  onOpenReport: (docId: string) => void;
};

function StatusBadge({ doc }: { doc: Doc }) {
  if (doc.status === "ready") {
    return <Badge variant="success">Ready</Badge>;
  }
  if (doc.status === "processing") {
    return (
      <Badge variant="warning" className="gap-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        Processing
      </Badge>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <Badge variant="destructive">Failed</Badge>
      {doc.fail_reason && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button className="inline-flex items-center text-red-600" type="button" aria-label="failed reason">
              <AlertCircle className="h-4 w-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="top">{doc.fail_reason}</TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}

export function DocTable({ workspaceId, docs, isLoading, isError, onOpenReport }: DocTableProps) {
  const { toast } = useToast();
  const deleteDoc = useDeleteDoc(workspaceId);
  const [openingDocId, setOpeningDocId] = useState<string | null>(null);
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const deletingDocId = deleteDoc.isPending ? (deleteDoc.variables ?? null) : null;

  const handleOpenDoc = async (doc: Doc) => {
    const previewWindow = window.open("", "_blank");
    if (!previewWindow) {
      toast({
        title: "プレビューを開けませんでした",
        description: "ブラウザのポップアップブロックを解除して再試行してください。",
        variant: "destructive"
      });
      return;
    }

    setOpeningDocId(doc.doc_id);
    try {
      const previewUrl = await fetchDocPresignedUrl(workspaceId, doc.doc_id);
      previewWindow.location.href = previewUrl;
    } catch (error) {
      previewWindow.close();
      toast({
        title: "ドキュメントを開けませんでした",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    } finally {
      setOpeningDocId((current) => (current === doc.doc_id ? null : current));
    }
  };

  const handleDownloadDoc = async (doc: Doc) => {
    const downloadWindow = window.open("", "_blank");
    if (!downloadWindow) {
      toast({
        title: "ダウンロードを開始できませんでした",
        description: "ブラウザのポップアップブロックを解除して再試行してください。",
        variant: "destructive"
      });
      return;
    }

    setDownloadingDocId(doc.doc_id);
    try {
      const previewUrl = await fetchDocPresignedUrl(workspaceId, doc.doc_id);
      downloadWindow.location.href = toDownloadUrl(previewUrl);
    } catch (error) {
      downloadWindow.close();
      toast({
        title: "ダウンロードに失敗しました",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    } finally {
      setDownloadingDocId((current) => (current === doc.doc_id ? null : current));
    }
  };

  const handleDeleteDoc = async (doc: Doc) => {
    const confirmed = window.confirm(`「${doc.file_name}」を削除します。この操作は取り消せません。`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteDoc.mutateAsync(doc.doc_id);
      toast({
        title: "ドキュメントを削除しました",
        description: doc.file_name
      });
    } catch (error) {
      toast({
        title: "ドキュメント削除に失敗しました",
        description: error instanceof Error ? error.message : "不明なエラー",
        variant: "destructive"
      });
    }
  };

  if (isLoading) {
    return <p className="p-3 text-sm text-slate-500">ドキュメント一覧を読み込み中...</p>;
  }

  if (isError) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
        <p className="font-medium">ドキュメント一覧の取得に失敗しました。</p>
        <p className="mt-1">接続先API・バックエンド起動状態・Workspaceの存在を確認して再読み込みしてください。</p>
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500">
        ファイルがありません。上のアップロードエリアから資料を投入してください。
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="max-h-[56vh] overflow-auto rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[220px]">ファイル名</TableHead>
              <TableHead>種別</TableHead>
              <TableHead>ステータス</TableHead>
              <TableHead>ページ数</TableHead>
              <TableHead className="min-w-[140px]">タグ</TableHead>
              <TableHead>更新日時</TableHead>
              <TableHead>アクション</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {docs.map((doc) => {
              const isBusy =
                openingDocId === doc.doc_id ||
                downloadingDocId === doc.doc_id ||
                deletingDocId === doc.doc_id;

              return (
                <TableRow key={doc.doc_id}>
                  <TableCell className="font-medium text-slate-800">{doc.file_name}</TableCell>
                  <TableCell className="text-slate-600">{doc.mime}</TableCell>
                  <TableCell>
                    <StatusBadge doc={doc} />
                  </TableCell>
                  <TableCell>{doc.page_count ?? "-"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {doc.tags.length === 0 ? (
                        <span className="text-xs text-slate-400">-</span>
                      ) : (
                        doc.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-[10px]">
                            {tag}
                          </Badge>
                        ))
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-slate-500">
                    {formatDateTime(doc.updated_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void handleOpenDoc(doc)}
                        disabled={isBusy}
                      >
                        {openingDocId === doc.doc_id ? (
                          <>
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                            開く...
                          </>
                        ) : (
                          <>
                            <ExternalLink className="mr-1 h-3 w-3" />
                            内容を開く
                          </>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void handleDownloadDoc(doc)}
                        disabled={isBusy}
                      >
                        {downloadingDocId === doc.doc_id ? (
                          <>
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                            DL中...
                          </>
                        ) : (
                          <>
                            <Download className="mr-1 h-3 w-3" />
                            ダウンロード
                          </>
                        )}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => onOpenReport(doc.doc_id)} disabled={isBusy}>
                        Ingestion Report
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => void handleDeleteDoc(doc)}
                        disabled={isBusy}
                      >
                        {deletingDocId === doc.doc_id ? (
                          <>
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                            削除中...
                          </>
                        ) : (
                          <>
                            <Trash2 className="mr-1 h-3 w-3" />
                            削除
                          </>
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      {docs.some((doc) => doc.status === "failed") && (
        <div className="mt-2 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          <FileWarning className="h-4 w-4" />
          取り込み失敗は隠さず表示しています。理由を確認し、必要なら再アップロードしてください。
        </div>
      )}
    </TooltipProvider>
  );
}
