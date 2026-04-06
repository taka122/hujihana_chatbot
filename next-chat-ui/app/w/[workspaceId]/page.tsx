"use client";

import { MouseEvent as ReactMouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { PanelRightOpen } from "lucide-react";

import { ChatPanel } from "@/components/chat-panel";
import { DocTable } from "@/components/doc-table";
import { DocUploader } from "@/components/doc-uploader";
import { IngestionReportDialog } from "@/components/ingestion-report-dialog";
import { LogoutButton } from "@/components/logout-button";
import { SourceViewer } from "@/components/source-viewer";
import { WorkspaceSelector } from "@/components/workspace-selector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { Citation } from "@/lib/api/types";
import { useDocs } from "@/lib/hooks/use-docs";

type WorkspacePageProps = {
  params: {
    workspaceId: string;
  };
};

const RESIZE_HANDLE_WIDTH = 12;
const DOC_PANEL_MIN_WIDTH = 240;
const CHAT_PANEL_MIN_WIDTH = 300;
const SOURCE_PANEL_MIN_WIDTH = 280;
const DEFAULT_DOC_PANEL_WIDTH = 260;
const DEFAULT_SOURCE_PANEL_WIDTH = 550;

const clamp = (value: number, min: number, max: number) => {
  const upper = Math.max(min, max);
  return Math.min(upper, Math.max(min, value));
};

export default function WorkspacePage({ params }: WorkspacePageProps) {
  const workspaceId = params.workspaceId;
  const docsQuery = useDocs(workspaceId, true);

  const [reportOpen, setReportOpen] = useState(false);
  const [reportDocId, setReportDocId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [sourceSheetOpen, setSourceSheetOpen] = useState(false);
  const [docPanelWidth, setDocPanelWidth] = useState(DEFAULT_DOC_PANEL_WIDTH);
  const [sourcePanelWidth, setSourcePanelWidth] = useState(DEFAULT_SOURCE_PANEL_WIDTH);
  const [activeHandle, setActiveHandle] = useState<"left" | "right" | null>(null);

  const layoutRef = useRef<HTMLDivElement | null>(null);
  const docPanelWidthRef = useRef(docPanelWidth);
  const sourcePanelWidthRef = useRef(sourcePanelWidth);

  const sortedDocs = useMemo(() => {
    if (!docsQuery.data) {
      return [];
    }
    return [...docsQuery.data].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));
  }, [docsQuery.data]);

  const openReport = (docId: string) => {
    setReportDocId(docId);
    setReportOpen(true);
  };

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setSourceSheetOpen(true);
  };

  useEffect(() => {
    docPanelWidthRef.current = docPanelWidth;
  }, [docPanelWidth]);

  useEffect(() => {
    sourcePanelWidthRef.current = sourcePanelWidth;
  }, [sourcePanelWidth]);

  useEffect(() => {
    if (!activeHandle) {
      return;
    }

    const stopResizing = () => setActiveHandle(null);
    const onMouseMove = (event: MouseEvent) => {
      const rect = layoutRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }

      const fixedWidth = RESIZE_HANDLE_WIDTH * 2;
      if (activeHandle === "left") {
        const maxDocWidth =
          rect.width - sourcePanelWidthRef.current - CHAT_PANEL_MIN_WIDTH - fixedWidth;
        const nextDocWidth = clamp(event.clientX - rect.left, DOC_PANEL_MIN_WIDTH, maxDocWidth);
        setDocPanelWidth(nextDocWidth);
        return;
      }

      const maxSourceWidth =
        rect.width - docPanelWidthRef.current - CHAT_PANEL_MIN_WIDTH - fixedWidth;
      const nextSourceWidth = clamp(rect.right - event.clientX, SOURCE_PANEL_MIN_WIDTH, maxSourceWidth);
      setSourcePanelWidth(nextSourceWidth);
    };

    const prevCursor = document.body.style.cursor;
    const prevUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", stopResizing);
    window.addEventListener("mouseleave", stopResizing);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", stopResizing);
      window.removeEventListener("mouseleave", stopResizing);
      document.body.style.cursor = prevCursor;
      document.body.style.userSelect = prevUserSelect;
    };
  }, [activeHandle]);

  useEffect(() => {
    const syncWidthsWithViewport = () => {
      const rect = layoutRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }
      const fixedWidth = RESIZE_HANDLE_WIDTH * 2;
      const maxDocWidth =
        rect.width - sourcePanelWidthRef.current - CHAT_PANEL_MIN_WIDTH - fixedWidth;
      const maxSourceWidth =
        rect.width - docPanelWidthRef.current - CHAT_PANEL_MIN_WIDTH - fixedWidth;

      if (docPanelWidthRef.current > maxDocWidth) {
        setDocPanelWidth(clamp(docPanelWidthRef.current, DOC_PANEL_MIN_WIDTH, maxDocWidth));
      }
      if (sourcePanelWidthRef.current > maxSourceWidth) {
        setSourcePanelWidth(
          clamp(sourcePanelWidthRef.current, SOURCE_PANEL_MIN_WIDTH, maxSourceWidth)
        );
      }
    };

    syncWidthsWithViewport();
    window.addEventListener("resize", syncWidthsWithViewport);
    return () => window.removeEventListener("resize", syncWidthsWithViewport);
  }, []);

  const startResize = (handle: "left" | "right") => (event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setActiveHandle(handle);
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1800px] flex-col gap-4 p-4 lg:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm backdrop-blur">
        <div>
          <p className="text-xs font-semibold tracking-[0.08em] text-slate-500">藤花歯科クリニック専用Chatbot</p>
          <h1 className="text-lg font-semibold text-slate-900">受付マニュアル</h1>
        </div>
        <div className="flex items-center gap-2">
          <WorkspaceSelector currentWorkspaceId={workspaceId} />
          <LogoutButton className="gap-2" />
          <Sheet open={sourceSheetOpen} onOpenChange={setSourceSheetOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" className="gap-2 lg:hidden">
                <PanelRightOpen className="h-4 w-4" />
                Source
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="p-0 sm:max-w-2xl">
              <SheetHeader className="border-b border-slate-200 p-4">
                <SheetTitle>Source Viewer</SheetTitle>
                <SheetDescription>引用を開いて原文を確認します。</SheetDescription>
              </SheetHeader>
              <div className="p-4">
                <SourceViewer workspaceId={workspaceId} citation={selectedCitation} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <section className="flex-1">
        <div
          ref={layoutRef}
          className="hidden h-full min-h-0 lg:grid"
          style={{
            gridTemplateColumns: `${docPanelWidth}px ${RESIZE_HANDLE_WIDTH}px minmax(0, 1fr) ${RESIZE_HANDLE_WIDTH}px ${sourcePanelWidth}px`
          }}
        >
          <Card className="min-w-0 border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Docs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              <DocUploader workspaceId={workspaceId} />
              <DocTable
                workspaceId={workspaceId}
                docs={sortedDocs}
                isLoading={docsQuery.isLoading}
                isError={docsQuery.isError}
                onOpenReport={openReport}
              />
            </CardContent>
          </Card>

          <button
            type="button"
            aria-label="Resize docs panel"
            title="Drag to resize"
            onMouseDown={startResize("left")}
            className="group relative h-full w-full cursor-col-resize touch-none"
          >
            <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-slate-300 transition-colors group-hover:bg-blue-500" />
          </button>

          <div className="min-w-0 px-2">
            <ChatPanel workspaceId={workspaceId} onCitationClick={handleCitationClick} />
          </div>

          <button
            type="button"
            aria-label="Resize source panel"
            title="Drag to resize"
            onMouseDown={startResize("right")}
            className="group relative h-full w-full cursor-col-resize touch-none"
          >
            <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-slate-300 transition-colors group-hover:bg-blue-500" />
          </button>

          <div className="min-w-0">
            <SourceViewer workspaceId={workspaceId} citation={selectedCitation} />
          </div>
        </div>

        <div className="grid gap-4 lg:hidden">
          <Card className="border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Docs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              <DocUploader workspaceId={workspaceId} />
              <DocTable
                workspaceId={workspaceId}
                docs={sortedDocs}
                isLoading={docsQuery.isLoading}
                isError={docsQuery.isError}
                onOpenReport={openReport}
              />
            </CardContent>
          </Card>

          <ChatPanel workspaceId={workspaceId} onCitationClick={handleCitationClick} />
        </div>
      </section>

      <IngestionReportDialog
        workspaceId={workspaceId}
        docId={reportDocId}
        open={reportOpen}
        onOpenChange={setReportOpen}
      />
    </main>
  );
}
