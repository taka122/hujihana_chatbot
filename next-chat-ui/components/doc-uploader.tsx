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
  "video/mp4": [".mp4"],
  "video/quicktime": [".mov"],
  "video/x-msvideo": [".avi"],
  "video/x-matroska": [".mkv"]
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

  const handleDriveImport = useCallback(async () => {
    const trimmed = driveFolderUrl.trim();
    if (!trimmed) {
      toast({
        title: "DriveフォルダURLが未入力です",
        description: "Google DriveフォルダのURLまたはフォルダIDを入力してください。",
        variant: "destructive"
      });
      return;
    }

    try {
      const result = await importDriveFolder.mutateAsync({ folderUrl: trimmed });
      setDriveFolderUrl("");
      toast({
        title: "Driveフォルダ取込を開始しました",
        description: `${result.queued_count}件を受付、${result.skipped_count}件をスキップしました。`
      });
    } catch (error) {
      toast({
        title: "Drive取込失敗",
        description: error instanceof Error ? error.message : "Google Driveフォルダを確認できませんでした。",
        variant: "destructive"
      });
    }
  }, [driveFolderUrl, importDriveFolder, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_FILES,
    multiple: true,
    disabled: uploadDoc.isPending || importDriveFolder.isPending
  });

  return (
    <Card className="border-slate-300 bg-slate-50/80 p-4">
      <div
        {...getRootProps()}
        className="cursor-pointer rounded-lg border border-dashed border-slate-300 p-4 transition hover:border-blue-400 hover:bg-blue-50"
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
            <p className="text-xs text-slate-500">pdf, docx, txt, md, pptx, xlsx, png, jpg, mp4, mov, avi, mkv</p>
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
      </div>

      <div className="mt-4 space-y-2 border-t border-slate-200 pt-4">
        <p className="text-sm font-semibold text-slate-900">Google Driveフォルダから動画を取り込む</p>
        <p className="text-xs text-slate-500">
          フォルダURLまたはフォルダIDを貼り付けると、フォルダ内の動画ファイルをまとめて登録します。
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
            disabled={importDriveFolder.isPending}
          >
            {importDriveFolder.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FolderUp className="h-4 w-4" />
            )}
            取込開始
          </Button>
        </div>
      </div>
    </Card>
  );
}
