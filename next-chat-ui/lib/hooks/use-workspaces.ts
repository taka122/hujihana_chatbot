"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createWorkspace, deleteWorkspace, fetchWorkspaces } from "@/lib/api/client";
import type { CreateWorkspaceRequest, Workspace } from "@/lib/api/types";

const WORKSPACES_QUERY_KEY = ["workspaces"];

export function useWorkspaces(enabled = true) {
  return useQuery<Workspace[]>({
    queryKey: WORKSPACES_QUERY_KEY,
    queryFn: fetchWorkspaces,
    enabled
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateWorkspaceRequest) => createWorkspace(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: WORKSPACES_QUERY_KEY });
    }
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (workspaceId: string) => deleteWorkspace(workspaceId),
    onSuccess: async (_, workspaceId) => {
      queryClient.removeQueries({ queryKey: ["docs", workspaceId] });
      await queryClient.invalidateQueries({ queryKey: WORKSPACES_QUERY_KEY });
    }
  });
}
