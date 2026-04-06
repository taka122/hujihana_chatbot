"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { importDriveFolder, uploadDoc } from "@/lib/api/client";

type UploadVariables = {
  file: File;
  onProgress?: (percent: number) => void;
};

type DriveImportVariables = {
  folderUrl: string;
};

export function useUploadDoc(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ file, onProgress }: UploadVariables) => {
      return uploadDoc(workspaceId, file, onProgress);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["docs", workspaceId] });
    }
  });
}

export function useImportDriveFolder(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ folderUrl }: DriveImportVariables) => {
      return importDriveFolder(workspaceId, folderUrl);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["docs", workspaceId] });
    }
  });
}
