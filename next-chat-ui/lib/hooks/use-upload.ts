"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { uploadDoc } from "@/lib/api/client";

type UploadVariables = {
  file: File;
  onProgress?: (percent: number) => void;
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
