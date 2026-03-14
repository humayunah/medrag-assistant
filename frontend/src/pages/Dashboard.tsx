import { useCallback, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthContext } from "../components/AuthProvider";
import { useWebSocket } from "../hooks/useWebSocket";
import api from "../services/api";
import type { DocumentStatus } from "../types";

/* ── Types ────────────────────────────────────────────────────────────── */

interface DocumentDTO {
  id: string;
  tenant_id: string;
  uploaded_by: string | null;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  ocr_confidence: number | null;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}

interface DocumentListDTO {
  documents: DocumentDTO[];
  total: number;
  page: number;
  page_size: number;
}

/* ── Constants ────────────────────────────────────────────────────────── */

const PAGE_SIZE = 20;

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "ready", label: "Ready" },
  { value: "failed", label: "Failed" },
];

const FONT_HEADING = "'DM Serif Display', serif";
const FONT_BODY = "'IBM Plex Sans', sans-serif";

/* ── Helpers ──────────────────────────────────────────────────────────── */

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/* ── Status Badge ─────────────────────────────────────────────────────── */

function StatusBadge({ status }: { status: DocumentStatus }) {
  const config: Record<
    string,
    { bg: string; text: string; dot: string; pulse?: boolean }
  > = {
    ready: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
    processing: {
      bg: "bg-amber-50",
      text: "text-amber-700",
      dot: "bg-amber-500",
      pulse: true,
    },
    failed: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
    pending: { bg: "bg-slate-100", text: "text-slate-600", dot: "bg-slate-400" },
    archived: { bg: "bg-slate-100", text: "text-slate-500", dot: "bg-slate-400" },
  };
  const c = config[status] ?? config.pending;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${c.dot} ${c.pulse ? "animate-pulse" : ""}`}
      />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/* ── OCR Confidence Indicator ─────────────────────────────────────────── */

function OcrConfidence({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  let color: string;
  if (pct >= 80) color = "text-emerald-600";
  else if (pct >= 60) color = "text-amber-600";
  else color = "text-red-600";

  return (
    <span className={`text-xs font-medium ${color}`} title={`OCR confidence: ${pct}%`}>
      {pct}%
    </span>
  );
}

/* ── Upload Modal ─────────────────────────────────────────────────────── */

function UploadModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: async (fileToUpload: File) => {
      const formData = new FormData();
      formData.append("file", fileToUpload);
      const res = await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setFile(null);
      onClose();
    },
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }, []);

  const handleConfirm = () => {
    if (file) uploadMutation.mutate(file);
  };

  const handleClose = () => {
    if (!uploadMutation.isPending) {
      setFile(null);
      uploadMutation.reset();
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Dialog */}
      <div
        className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6"
        style={{ fontFamily: FONT_BODY }}
      >
        <h2
          className="text-xl text-[#0f172a] mb-4"
          style={{ fontFamily: FONT_HEADING }}
        >
          Upload Document
        </h2>

        {/* Drop zone */}
        <div
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
            dragOver
              ? "border-[#d97706] bg-amber-50"
              : "border-slate-300 hover:border-slate-400 bg-slate-50"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
            onChange={(e) => {
              const picked = e.target.files?.[0];
              if (picked) setFile(picked);
            }}
          />

          <svg
            className="mx-auto w-10 h-10 text-slate-400 mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
          <p className="text-sm text-slate-600">
            Drag &amp; drop a file here, or{" "}
            <span className="text-[#d97706] font-medium">browse</span>
          </p>
          <p className="text-xs text-slate-400 mt-1">
            PDF, PNG, JPEG, TIFF
          </p>
        </div>

        {/* Selected file preview */}
        {file && (
          <div className="mt-4 flex items-center gap-3 rounded-lg bg-slate-50 border border-slate-200 px-4 py-3">
            <svg
              className="w-5 h-5 text-slate-400 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-[#0f172a] truncate">{file.name}</p>
              <p className="text-xs text-slate-500">{formatFileSize(file.size)}</p>
            </div>
            <button
              className="text-slate-400 hover:text-slate-600 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              title="Remove"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        )}

        {/* Error */}
        {uploadMutation.isError && (
          <p className="mt-3 text-sm text-red-600">
            Upload failed.{" "}
            {(uploadMutation.error as { response?: { data?: { detail?: string } } })
              ?.response?.data?.detail || "Please try again."}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            onClick={handleClose}
            disabled={uploadMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!file || uploadMutation.isPending}
            className="px-5 py-2 text-sm font-medium text-white bg-[#d97706] hover:bg-amber-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {uploadMutation.isPending && <Spinner />}
            {uploadMutation.isPending ? "Uploading..." : "Upload"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Spinner ──────────────────────────────────────────────────────────── */

function Spinner({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

/* ── Empty State ──────────────────────────────────────────────────────── */

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-20 h-20 rounded-2xl bg-amber-50 flex items-center justify-center mb-5">
        <svg
          className="w-10 h-10 text-[#d97706]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
          />
        </svg>
      </div>
      <h3
        className="text-lg text-[#0f172a] mb-2"
        style={{ fontFamily: FONT_HEADING }}
      >
        No documents yet
      </h3>
      <p
        className="text-sm text-slate-500 mb-6 max-w-xs"
        style={{ fontFamily: FONT_BODY }}
      >
        Upload your first document to get started. We support PDF, PNG, JPEG, and TIFF
        files.
      </p>
      <button
        onClick={onUpload}
        className="px-5 py-2.5 text-sm font-medium text-white bg-[#d97706] hover:bg-amber-600 rounded-lg transition-colors flex items-center gap-2"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4.5v15m7.5-7.5h-15"
          />
        </svg>
        Upload Document
      </button>
    </div>
  );
}

/* ── Pagination ───────────────────────────────────────────────────────── */

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;

  const pages: (number | "...")[] = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== "...") {
      pages.push("...");
    }
  }

  return (
    <div className="flex items-center justify-center gap-1 pt-6 pb-2">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-sm rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>

      {pages.map((p, idx) =>
        p === "..." ? (
          <span key={`ellipsis-${idx}`} className="px-2 text-slate-400 text-sm">
            ...
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`w-9 h-9 text-sm rounded-lg transition-colors ${
              p === page
                ? "bg-[#0f172a] text-white font-medium"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {p}
          </button>
        ),
      )}

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  );
}

/* ── Document Row ─────────────────────────────────────────────────────── */

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: DocumentDTO;
  onDelete: (id: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);

  return (
    <div className="flex items-center gap-4 px-5 py-4 bg-white rounded-xl border border-slate-200/80 hover:border-slate-300 transition-colors">
      {/* File icon */}
      <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
        <svg
          className="w-5 h-5 text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
          />
        </svg>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#0f172a] truncate" title={doc.filename}>
          {doc.filename}
        </p>
        <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
          <span>{formatFileSize(doc.file_size_bytes)}</span>
          <span className="w-0.5 h-0.5 rounded-full bg-slate-300" />
          <span>{relativeTime(doc.created_at)}</span>
          {doc.page_count != null && (
            <>
              <span className="w-0.5 h-0.5 rounded-full bg-slate-300" />
              <span>
                {doc.page_count} {doc.page_count === 1 ? "page" : "pages"}
              </span>
            </>
          )}
        </div>
      </div>

      {/* OCR confidence */}
      {doc.ocr_confidence != null && (
        <div className="hidden sm:flex flex-col items-center shrink-0" title="OCR Confidence">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">
            OCR
          </span>
          <OcrConfidence value={doc.ocr_confidence} />
        </div>
      )}

      {/* Status */}
      <StatusBadge status={doc.status} />

      {/* Delete */}
      {confirming ? (
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => {
              onDelete(doc.id);
              setConfirming(false);
            }}
            className="px-2.5 py-1 text-xs font-medium text-white bg-[#dc2626] hover:bg-red-700 rounded-md transition-colors"
          >
            Confirm
          </button>
          <button
            onClick={() => setConfirming(false)}
            className="px-2.5 py-1 text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setConfirming(true)}
          className="p-2 text-slate-400 hover:text-[#dc2626] transition-colors rounded-lg hover:bg-red-50 shrink-0"
          title="Delete document"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
            />
          </svg>
        </button>
      )}
    </div>
  );
}

/* ── Dashboard Page ───────────────────────────────────────────────────── */

export default function Dashboard() {
  useAuthContext(); // ensure user is authenticated

  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [uploadOpen, setUploadOpen] = useState(false);

  // Query params
  const page = Number(searchParams.get("page")) || 1;
  const search = searchParams.get("search") || "";
  const statusFilter = searchParams.get("status") || "";

  // Update search params helper
  const setParam = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        // Reset to page 1 when filters change
        if (key !== "page") next.delete("page");
        return next;
      });
    },
    [setSearchParams],
  );

  // Fetch documents
  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery<DocumentListDTO>({
    queryKey: ["documents", page, search, statusFilter],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        page,
        page_size: PAGE_SIZE,
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get("/documents", { params });
      return res.data;
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  // WebSocket: live processing updates
  const handleWSEvent = useCallback(
    (event: { document_id: string; status: string; progress: number }) => {
      queryClient.setQueriesData<DocumentListDTO>(
        { queryKey: ["documents"] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            documents: old.documents.map((doc) =>
              doc.id === event.document_id
                ? { ...doc, status: event.status as DocumentStatus }
                : doc,
            ),
          };
        },
      );
      // If a document just became ready or failed, refetch to get updated metadata
      if (event.status === "ready" || event.status === "failed") {
        queryClient.invalidateQueries({ queryKey: ["documents"] });
      }
    },
    [queryClient],
  );

  useWebSocket(handleWSEvent);

  // Derived stats
  const stats = useMemo(() => {
    if (!data) return null;
    const docs = data.documents;
    const totalSize = docs.reduce((sum, d) => sum + d.file_size_bytes, 0);
    const ready = docs.filter((d) => d.status === "ready").length;
    const processing = docs.filter((d) => d.status === "processing").length;
    const failed = docs.filter((d) => d.status === "failed").length;
    return { count: data.total, totalSize, ready, processing, failed };
  }, [data]);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const documents = data?.documents ?? [];

  // Search debounce timer ref
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleSearchChange = useCallback(
    (value: string) => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
      searchTimerRef.current = setTimeout(() => {
        setParam("search", value);
      }, 300);
    },
    [setParam],
  );

  return (
    <div
      className="min-h-full bg-[#faf7f2]"
      style={{ fontFamily: FONT_BODY }}
    >
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-6">
          <h1
            className="text-2xl text-[#0f172a]"
            style={{ fontFamily: FONT_HEADING }}
          >
            Documents
          </h1>
          <button
            onClick={() => setUploadOpen(true)}
            className="px-5 py-2.5 text-sm font-medium text-white bg-[#d97706] hover:bg-amber-600 rounded-lg transition-colors flex items-center gap-2 shadow-sm"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
            Upload Document
          </button>
        </div>

        {/* ── Stats Bar ───────────────────────────────────────────── */}
        {stats && stats.count > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
            <StatCard label="Documents" value={String(stats.count)} />
            <StatCard label="Total Size" value={formatFileSize(stats.totalSize)} />
            <StatCard
              label="Ready"
              value={String(stats.ready)}
              valueColor="text-[#059669]"
            />
            <StatCard
              label="Processing"
              value={String(stats.processing)}
              valueColor="text-[#d97706]"
            />
            <StatCard
              label="Failed"
              value={String(stats.failed)}
              valueColor="text-[#dc2626]"
            />
          </div>
        )}

        {/* ── Search + Filters ────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
              />
            </svg>
            <input
              type="text"
              placeholder="Search documents..."
              defaultValue={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-slate-200 rounded-lg text-[#0f172a] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#d97706]/30 focus:border-[#d97706] transition-colors"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setParam("status", e.target.value)}
            className="px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-lg text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#d97706]/30 focus:border-[#d97706] transition-colors sm:w-44"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* ── Content ─────────────────────────────────────────────── */}
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Spinner className="w-6 h-6 text-[#d97706]" />
          </div>
        ) : isError ? (
          <div className="text-center py-24">
            <p className="text-red-600 text-sm mb-2">Failed to load documents</p>
            <p className="text-xs text-slate-500">
              {(error as { message?: string })?.message || "Unknown error"}
            </p>
          </div>
        ) : documents.length === 0 && !search && !statusFilter ? (
          <EmptyState onUpload={() => setUploadOpen(true)} />
        ) : documents.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-sm text-slate-500">
              No documents match your filters.
            </p>
          </div>
        ) : (
          <>
            {/* Delete error */}
            {deleteMutation.isError && (
              <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                Failed to delete document. Please try again.
              </div>
            )}

            {/* Document list */}
            <div className="space-y-2">
              {documents.map((doc) => (
                <DocumentRow
                  key={doc.id}
                  doc={doc}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
            </div>

            {/* Pagination */}
            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={(p) => setParam("page", String(p))}
            />
          </>
        )}
      </div>

      {/* Upload Modal */}
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  );
}

/* ── Stat Card ────────────────────────────────────────────────────────── */

function StatCard({
  label,
  value,
  valueColor = "text-[#0f172a]",
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 px-4 py-3">
      <p className="text-[11px] uppercase tracking-wider text-slate-400 mb-0.5">
        {label}
      </p>
      <p className={`text-lg font-semibold ${valueColor}`}>{value}</p>
    </div>
  );
}
