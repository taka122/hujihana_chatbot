"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteDoc } from "@/lib/api/client";

export function useDeleteDoc(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (docId: string) => deleteDoc(workspaceId, docId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["docs", workspaceId] });
    }
  });
}
