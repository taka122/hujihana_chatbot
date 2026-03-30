"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchSourcePreview } from "@/lib/api/client";
import type { SourcePreview } from "@/lib/api/types";

export function useSourcePreview(
  workspaceId: string,
  docId: string,
  ref: string,
  enabled = true
) {
  return useQuery<SourcePreview>({
    queryKey: ["source-preview", workspaceId, docId, ref],
    queryFn: () => fetchSourcePreview(workspaceId, docId, ref),
    enabled: enabled && Boolean(workspaceId) && Boolean(docId) && Boolean(ref)
  });
}
