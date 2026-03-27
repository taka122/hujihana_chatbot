"use client";

import { AlertTriangle, Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useIngestionReport } from "@/lib/hooks/use-ingestion-report";

type IngestionReportDialogProps = {
  workspaceId: string;
  docId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function IngestionReportDialog({
  workspaceId,
  docId,
  open,
  onOpenChange
}: IngestionReportDialogProps) {
  const reportQuery = useIngestionReport(workspaceId, docId ?? "", open && Boolean(docId));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Ingestion Report</DialogTitle>
          <DialogDescription>失敗を含めた取り込み結果を表示します。</DialogDescription>
        </DialogHeader>

        {reportQuery.isLoading && (
          <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            レポートを取得中...
          </div>
        )}

        {reportQuery.isError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            取り込みレポートの取得に失敗しました。しばらくして再試行してください。
          </div>
        )}

        {reportQuery.data && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <p className="text-xs text-slate-500">成功ページ</p>
                <p className="text-lg font-semibold text-slate-900">{reportQuery.data.extracted_pages}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <p className="text-xs text-slate-500">失敗ページ</p>
                <p className="text-lg font-semibold text-red-600">{reportQuery.data.failed_pages.length}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <p className="text-xs text-slate-500">OCR利用ページ</p>
                <p className="text-lg font-semibold text-slate-900">{reportQuery.data.ocr_used_pages.length}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-white p-3">
                <p className="text-xs text-slate-500">Chunk数</p>
                <p className="text-lg font-semibold text-slate-900">{reportQuery.data.chunk_count}</p>
              </div>
            </div>

            <div className="rounded-md border border-slate-200 bg-white p-3 text-sm">
              <p className="text-slate-600">
                推定コスト: {reportQuery.data.estimated_cost == null ? "-" : reportQuery.data.estimated_cost}
              </p>
            </div>

            <div className="rounded-md border border-slate-200">
              <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                failed_pages
              </div>
              {reportQuery.data.failed_pages.length === 0 ? (
                <p className="p-3 text-sm text-slate-500">失敗ページはありません。</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[120px]">page</TableHead>
                      <TableHead>reason</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reportQuery.data.failed_pages.map((failed) => (
                      <TableRow key={`${failed.page}-${failed.reason}`}>
                        <TableCell>{failed.page}</TableCell>
                        <TableCell>{failed.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>

            {reportQuery.data.ocr_used_pages.length > 0 && (
              <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                OCR / Vision利用ページ: {reportQuery.data.ocr_used_pages.join(", ")}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
