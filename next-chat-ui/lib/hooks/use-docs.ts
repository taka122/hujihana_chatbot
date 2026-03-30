"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchDocs } from "@/lib/api/client";
import type { Doc } from "@/lib/api/types";

export function useDocs(workspaceId: string, enabled = true) {
  return useQuery<Doc[]>({
    queryKey: ["docs", workspaceId],
    queryFn: () => fetchDocs(workspaceId),
    enabled: Boolean(workspaceId) && enabled,
    refetchInterval: (query) => {
      const docs = query.state.data;
      const hasProcessing = docs?.some((doc) => doc.status === "processing");
      return hasProcessing ? 3000 : false;
    }
  });
}
