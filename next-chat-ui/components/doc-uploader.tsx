"use client";

import { useCallback, useState } from "react";
import { FileUp, FolderUp, Loader2 } from "lucide-react";
import { useDropzone, type FileRejection } from "react-dropzone";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { useImportDriveFolder, useUploadDoc } from "@/lib/hooks/use-upload";

type DocUploaderProps = {
  workspaceId: string;
};

const ACCEPTED_FILES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "video/mp4": [".mp4", ".m4v"],
  "video/quicktime": [".mov"],
  "video/x-msvideo": [".avi"],
  "video/x-matroska": [".mkv"],
  "video/webm": [".webm"]
};

export function DocUploader({ workspaceId }: DocUploaderProps) {
  const { toast } = useToast();
  const uploadDoc = useUploadDoc(workspaceId);
  const importDriveFolder = useImportDriveFolder(workspaceId);
  const [uploading, setUploading] = useState<{ fileName: string; percent: number } | null>(null);
  const [driveFolderUrl, setDriveFolderUrl] = useState("");

  const onDrop = useCallback(
    async (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      if (fileRejections.length > 0) {
        const first = fileRejections[0];
        toast({
          title: "対応外のファイルです",
          description: `${first.file.name}: ${first.errors[0]?.message ?? "アップロードできません"}`,
          variant: "destructive"
        });
      }

      for (const file of acceptedFiles) {
        setUploading({ fileName: file.name, percent: 0 });
        toast({
          title: "アップロード開始",
          description: `${file.name} を取り込み中です。`
        });

        try {
          await uploadDoc.mutateAsync({
            file,
            onProgress: (percent) => setUploading({ fileName: file.name, percent })
          });
          toast({
            title: "アップロード完了",
            description: `${file.name} を受け付けました。解析完了まで数秒かかる場合があります。`
          });
        } catch (error) {
          toast({
            title: "アップロード失敗",
            description:
              error instanceof Error
                ? `${error.message}。ファイル形式・容量・暗号化有無を確認してください。`
                : "原因不明です。再試行してください。",
            variant: "destructive"
          });
        }
      }

      setUploading(null);
    },
    [toast, uploadDoc]
  );

  const handleDriveImport = async () => {
    const trimmed = driveFolderUrl.trim();
    if (!trimmed) {
      toast({
        title: "Google DriveフォルダURLを入力してください",
        description: "https://drive.google.com/drive/folders/... の形式で入力してください。",
        variant: "destructive"
      });
      return;
    }

    try {
      const result = await importDriveFolder.mutateAsync({ folderUrl: trimmed });
      toast({
        title: "Google Drive取込を開始しました",
        description: `追加: ${result.queued_count}件 / スキップ: ${result.skipped_count}件`
      });
      setDriveFolderUrl("");
    } catch (error) {
      toast({
        title: "Google Drive取込に失敗しました",
        description: error instanceof Error ? error.message : "不明なエラーです。",
        variant: "destructive"
      });
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_FILES,
    multiple: true,
    disabled: uploadDoc.isPending || importDriveFolder.isPending
  });

  return (
    <div className="space-y-3">
      <Card
        {...getRootProps()}
        className="cursor-pointer border-dashed border-slate-300 bg-slate-50/80 p-4 transition hover:border-blue-400 hover:bg-blue-50"
      >
        <input {...getInputProps()} />
        <div className="flex items-center gap-3">
          {uploadDoc.isPending ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          ) : (
            <FileUp className="h-5 w-5 text-blue-600" />
          )}
          <div>
            <p className="text-sm font-semibold text-slate-900">
              {isDragActive ? "ここにドロップ" : "ファイルをドラッグ&ドロップ / クリックで選択"}
            </p>
            <p className="text-xs text-slate-500">pdf, docx, txt, md, pptx, xlsx, png, jpg, mp4, mov, avi, mkv, webm</p>
          </div>
        </div>

        {uploading && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-600">
              <span className="truncate">{uploading.fileName}</span>
              <span>{uploading.percent}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-200">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all"
                style={{ width: `${Math.min(100, Math.max(0, uploading.percent))}%` }}
              />
            </div>
          </div>
        )}
      </Card>

      <Card className="border-slate-200 bg-white p-4">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-slate-900">Google DriveフォルダURLから動画を取り込む</p>
          <p className="text-xs text-slate-500">
            `https://drive.google.com/drive/folders/...` を貼り付けると、動画を取込対象に追加できます。
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={driveFolderUrl}
              onChange={(event) => setDriveFolderUrl(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleDriveImport();
                }
              }}
              placeholder="https://drive.google.com/drive/folders/..."
              disabled={importDriveFolder.isPending}
            />
            <Button
              type="button"
              className="gap-2"
              onClick={() => void handleDriveImport()}
              disabled={importDriveFolder.isPending || driveFolderUrl.trim().length === 0}
            >
              {importDriveFolder.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FolderUp className="h-4 w-4" />
              )}
              {importDriveFolder.isPending ? "取込中..." : "取込開始"}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
