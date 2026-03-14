import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../services/api";
import type {
  QueryResponse,
  CitationSource,
  Conversation,
  QueryMessage,
  Document,
} from "../types";

/* ─────────────────────────── Constants ─────────────────────────── */

const FONT_HEADING = "'DM Serif Display', serif";
const FONT_BODY = "'IBM Plex Sans', sans-serif";

const COLOR = {
  slate: "#0f172a",
  amber: "#d97706",
  green: "#059669",
  cream: "#faf7f2",
} as const;

/* ─────────────────────────── API helpers ─────────────────────────── */

async function fetchConversations(): Promise<Conversation[]> {
  const { data } = await api.get("/conversations");
  return data.conversations ?? [];
}

async function fetchMessages(conversationId: string): Promise<QueryMessage[]> {
  const { data } = await api.get(
    `/conversations/${conversationId}/messages`,
  );
  return Array.isArray(data) ? data : data.messages ?? [];
}

async function fetchDocuments(): Promise<Document[]> {
  const { data } = await api.get("/documents");
  return data.documents ?? [];
}

async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/conversations/${id}`);
}

interface QueryPayload {
  query: string;
  conversation_id?: string;
  document_ids?: string[];
}

async function postQuery(payload: QueryPayload): Promise<QueryResponse> {
  const { data } = await api.post("/queries", payload);
  return data;
}

/* ─────────────────────────── Main Component ─────────────────────── */

export default function QueryChat() {
  const queryClient = useQueryClient();

  /* ── Conversations state ── */
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);

  /* ── Citation panel ── */
  const [selectedCitation, setSelectedCitation] =
    useState<CitationSource | null>(null);
  const [citationPanelOpen, setCitationPanelOpen] = useState(false);

  /* ── Input state ── */
  const [inputValue, setInputValue] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);

  /* ── Refs ── */
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* ── Queries ── */
  const { data: conversations = [], isLoading: convLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: fetchConversations,
  });

  const { data: messages = [], isLoading: messagesLoading } = useQuery({
    queryKey: ["messages", activeConversationId],
    queryFn: () => fetchMessages(activeConversationId!),
    enabled: !!activeConversationId,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
  });

  /* ── Mutations ── */
  const queryMutation = useMutation({
    mutationFn: postQuery,
    onSuccess: (data) => {
      // If we started a new conversation, activate it
      if (!activeConversationId && data.conversation_id) {
        setActiveConversationId(data.conversation_id);
      }
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["messages", data.conversation_id],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_data, deletedId) => {
      if (activeConversationId === deletedId) {
        setActiveConversationId(null);
      }
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  /* ── Auto-scroll ── */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, queryMutation.isPending]);

  /* ── Focus input on conversation change ── */
  useEffect(() => {
    inputRef.current?.focus();
  }, [activeConversationId]);

  /* ── Optimistic user message for display while pending ── */
  const pendingUserMessage = queryMutation.isPending
    ? queryMutation.variables?.query
    : null;

  /* ── Merged message list ── */
  const displayMessages: QueryMessage[] = useMemo(() => {
    const list = [...messages];
    if (pendingUserMessage) {
      list.push({
        id: "__pending_user",
        role: "user",
        content: pendingUserMessage,
        citations: [],
        created_at: new Date().toISOString(),
      });
    }
    return list;
  }, [messages, pendingUserMessage]);

  /* ── Submit ── */
  const handleSubmit = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed || queryMutation.isPending) return;
    queryMutation.mutate({
      query: trimmed,
      conversation_id: activeConversationId ?? undefined,
      document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
    });
    setInputValue("");
  }, [
    inputValue,
    queryMutation,
    activeConversationId,
    selectedDocIds,
  ]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  /* ── New conversation ── */
  const handleNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setSelectedCitation(null);
    setCitationPanelOpen(false);
    setInputValue("");
    inputRef.current?.focus();
  }, []);

  /* ── Citation click ── */
  const handleCitationClick = useCallback((citation: CitationSource) => {
    setSelectedCitation(citation);
    setCitationPanelOpen(true);
  }, []);

  /* ── Document filter toggle ── */
  const toggleDocFilter = useCallback(
    (docId: string) => {
      setSelectedDocIds((prev) =>
        prev.includes(docId)
          ? prev.filter((id) => id !== docId)
          : [...prev, docId],
      );
    },
    [],
  );

  /* ─────────────────────────── Render ─────────────────────────── */

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ fontFamily: FONT_BODY, backgroundColor: COLOR.cream }}
    >
      {/* ════════════════ Left Sidebar ════════════════ */}
      <aside className="w-72 shrink-0 flex flex-col border-r border-slate-200 bg-white">
        {/* Header */}
        <div className="px-4 py-4 border-b border-slate-100">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 active:scale-[0.98]"
            style={{ backgroundColor: COLOR.slate }}
          >
            <PlusIcon />
            New Conversation
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {convLoading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-12 px-4">
              <ChatBubbleIcon className="w-10 h-10 mx-auto text-slate-300 mb-3" />
              <p className="text-sm text-slate-400">No conversations yet</p>
              <p className="text-xs text-slate-300 mt-1">
                Ask a question to get started
              </p>
            </div>
          ) : (
            <ul className="space-y-0.5">
              {conversations.map((conv) => (
                <ConversationItem
                  key={conv.id}
                  conversation={conv}
                  isActive={conv.id === activeConversationId}
                  onSelect={() => {
                    setActiveConversationId(conv.id);
                    setSelectedCitation(null);
                    setCitationPanelOpen(false);
                  }}
                  onDelete={() => deleteMutation.mutate(conv.id)}
                />
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* ════════════════ Center Panel ════════════════ */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header bar */}
        <header className="shrink-0 px-6 py-4 border-b border-slate-200 bg-white/80 backdrop-blur-sm">
          <h2
            className="text-lg text-slate-900 tracking-tight"
            style={{ fontFamily: FONT_HEADING }}
          >
            {activeConversationId
              ? conversations.find((c) => c.id === activeConversationId)
                  ?.title || "Conversation"
              : "New Conversation"}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Ask questions about your medical documents
          </p>
        </header>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!activeConversationId && displayMessages.length === 0 ? (
            <EmptyState />
          ) : messagesLoading ? (
            <div className="flex items-center justify-center h-full">
              <Spinner />
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {displayMessages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onCitationClick={handleCitationClick}
                  selectedCitation={selectedCitation}
                />
              ))}

              {/* Thinking indicator */}
              {queryMutation.isPending && <ThinkingIndicator />}

              {/* Error state */}
              {queryMutation.isError && (
                <InsufficientInfoBanner
                  message={
                    (queryMutation.error as Error)?.message ||
                    "Something went wrong. Please try again."
                  }
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom input area */}
        <div className="shrink-0 border-t border-slate-200 bg-white px-6 py-4">
          <div className="max-w-3xl mx-auto">
            {/* Document filter */}
            <div className="relative mb-2">
              <button
                type="button"
                onClick={() => setFilterOpen(!filterOpen)}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors"
              >
                <FilterIcon />
                {selectedDocIds.length === 0
                  ? "All documents"
                  : `${selectedDocIds.length} document${selectedDocIds.length > 1 ? "s" : ""} selected`}
                <ChevronIcon open={filterOpen} />
              </button>

              {filterOpen && documents.length > 0 && (
                <div className="absolute bottom-full left-0 mb-2 w-72 max-h-48 overflow-y-auto bg-white border border-slate-200 rounded-lg shadow-lg z-20">
                  {documents
                    .filter((d) => d.status === "ready")
                    .map((doc) => (
                      <label
                        key={doc.id}
                        className="flex items-center gap-2 px-3 py-2 hover:bg-slate-50 cursor-pointer text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={selectedDocIds.includes(doc.id)}
                          onChange={() => toggleDocFilter(doc.id)}
                          className="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                        />
                        <span className="truncate text-slate-700">
                          {doc.filename}
                        </span>
                      </label>
                    ))}
                </div>
              )}
            </div>

            {/* Input row */}
            <div className="flex items-end gap-3">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={queryMutation.isPending}
                  placeholder="Ask a question about your documents..."
                  rows={1}
                  className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/40 focus:border-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  style={{
                    minHeight: "44px",
                    maxHeight: "120px",
                    fontFamily: FONT_BODY,
                  }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "auto";
                    target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                  }}
                />
              </div>
              <button
                onClick={handleSubmit}
                disabled={!inputValue.trim() || queryMutation.isPending}
                className="shrink-0 w-11 h-11 rounded-xl flex items-center justify-center text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{
                  backgroundColor: inputValue.trim()
                    ? COLOR.amber
                    : "#94a3b8",
                }}
                title="Send message"
              >
                {queryMutation.isPending ? (
                  <SpinnerSmall />
                ) : (
                  <SendIcon />
                )}
              </button>
            </div>
            <p className="text-[11px] text-slate-300 mt-2 text-center">
              Shift+Enter for new line. Responses are AI-generated and should be
              verified.
            </p>
          </div>
        </div>
      </main>

      {/* ════════════════ Right Panel — Citations ════════════════ */}
      <div
        className={`shrink-0 border-l border-slate-200 bg-white transition-all duration-300 ease-in-out overflow-hidden ${
          citationPanelOpen ? "w-80" : "w-0"
        }`}
      >
        {citationPanelOpen && selectedCitation && (
          <div className="w-80 h-full flex flex-col">
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 py-4 border-b border-slate-100">
              <h3
                className="text-sm font-semibold text-slate-900"
                style={{ fontFamily: FONT_HEADING }}
              >
                Citation Details
              </h3>
              <button
                onClick={() => setCitationPanelOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                title="Close panel"
              >
                <CloseIcon />
              </button>
            </div>

            {/* Citation content */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
              {/* Document info */}
              <div>
                <label className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">
                  Document
                </label>
                <p className="mt-1 text-sm font-medium text-slate-900 break-words">
                  {selectedCitation.filename}
                </p>
              </div>

              {/* Page & section */}
              <div className="grid grid-cols-2 gap-3">
                {selectedCitation.page_number !== null && (
                  <div>
                    <label className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">
                      Page
                    </label>
                    <p className="mt-1 text-sm text-slate-700">
                      {selectedCitation.page_number}
                    </p>
                  </div>
                )}
                {selectedCitation.section && (
                  <div>
                    <label className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">
                      Section
                    </label>
                    <p className="mt-1 text-sm text-slate-700">
                      {selectedCitation.section}
                    </p>
                  </div>
                )}
              </div>

              {/* Relevance score */}
              <div>
                <label className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">
                  Relevance
                </label>
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.round(selectedCitation.relevance_score * 100)}%`,
                        backgroundColor:
                          selectedCitation.relevance_score >= 0.7
                            ? COLOR.green
                            : selectedCitation.relevance_score >= 0.4
                              ? COLOR.amber
                              : "#ef4444",
                      }}
                    />
                  </div>
                  <span className="text-xs font-medium text-slate-600 w-10 text-right">
                    {Math.round(selectedCitation.relevance_score * 100)}%
                  </span>
                </div>
              </div>

              {/* Content preview */}
              <div>
                <label className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">
                  Content Preview
                </label>
                <div className="mt-2 p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">
                    {selectedCitation.chunk_text.length > 300
                      ? `${selectedCitation.chunk_text.slice(0, 300)}...`
                      : selectedCitation.chunk_text}
                  </p>
                </div>
              </div>

              {/* View document link */}
              <button
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-all"
                title="View full document (coming soon)"
                disabled
              >
                <ExternalLinkIcon />
                View Document
                <span className="text-[10px] text-slate-400 ml-1">
                  (coming soon)
                </span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────── Sub-components ─────────────────────── */

/* ── Conversation list item ── */

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
}: ConversationItemProps) {
  const [hovering, setHovering] = useState(false);

  const dateStr = useMemo(() => {
    const d = new Date(conversation.updated_at || conversation.created_at);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }, [conversation.updated_at, conversation.created_at]);

  return (
    <li
      className={`group relative flex items-center rounded-lg cursor-pointer transition-colors ${
        isActive
          ? "bg-amber-50 border border-amber-200"
          : "hover:bg-slate-50 border border-transparent"
      }`}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onClick={onSelect}
    >
      <div className="flex-1 min-w-0 px-3 py-2.5">
        <p
          className={`text-sm truncate ${
            isActive ? "font-medium text-slate-900" : "text-slate-700"
          }`}
        >
          {conversation.title || "Untitled"}
        </p>
        <p className="text-[11px] text-slate-400 mt-0.5">{dateStr}</p>
      </div>

      {/* Delete button */}
      {hovering && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors"
          title="Delete conversation"
        >
          <CloseIcon />
        </button>
      )}
    </li>
  );
}

/* ── Message bubble ── */

interface MessageBubbleProps {
  message: QueryMessage;
  onCitationClick: (citation: CitationSource) => void;
  selectedCitation: CitationSource | null;
}

function MessageBubble({
  message,
  onCitationClick,
  selectedCitation,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "text-white rounded-br-md"
            : "bg-white text-slate-800 border border-slate-100 rounded-bl-md shadow-sm"
        }`}
        style={isUser ? { backgroundColor: COLOR.slate } : undefined}
      >
        {/* Message content */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {isUser ? (
            message.content
          ) : (
            <AssistantContent
              content={message.content}
              citations={message.citations}
              onCitationClick={onCitationClick}
              selectedCitation={selectedCitation}
            />
          )}
        </div>

        {/* Timestamp */}
        <p
          className={`text-[10px] mt-2 ${
            isUser ? "text-slate-400" : "text-slate-300"
          }`}
        >
          {message.id === "__pending_user"
            ? "Sending..."
            : formatTime(message.created_at)}
        </p>
      </div>
    </div>
  );
}

/* ── Assistant content with inline citations ── */

interface AssistantContentProps {
  content: string;
  citations: CitationSource[];
  onCitationClick: (citation: CitationSource) => void;
  selectedCitation: CitationSource | null;
}

function AssistantContent({
  content,
  citations,
  onCitationClick,
  selectedCitation,
}: AssistantContentProps) {
  // Look for [Source N] patterns in the text and render them as badges
  const parts = content.split(/(\[Source \d+\])/g);

  return (
    <>
      {parts.map((part, i) => {
        const sourceMatch = part.match(/^\[Source (\d+)\]$/);
        if (sourceMatch) {
          const sourceIndex = parseInt(sourceMatch[1], 10) - 1;
          const citation = citations[sourceIndex];
          if (!citation) return <span key={i}>{part}</span>;

          const isSelected =
            selectedCitation?.document_id === citation.document_id &&
            selectedCitation?.chunk_text === citation.chunk_text;

          return (
            <button
              key={i}
              onClick={() => onCitationClick(citation)}
              className={`inline-flex items-center gap-0.5 mx-0.5 px-1.5 py-0.5 rounded-md text-[11px] font-medium transition-all hover:opacity-80 ${
                isSelected
                  ? "ring-2 ring-amber-400 ring-offset-1"
                  : ""
              }`}
              style={{
                backgroundColor: `${COLOR.amber}18`,
                color: COLOR.amber,
              }}
              title={`${citation.filename}${citation.page_number ? ` — p.${citation.page_number}` : ""}`}
            >
              <SourceIcon />
              {sourceMatch[1]}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}

      {/* Citation chips row for all citations if not referenced inline */}
      {citations.length > 0 &&
        !content.includes("[Source") && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-slate-100">
            {citations.map((citation, i) => {
              const isSelected =
                selectedCitation?.document_id === citation.document_id &&
                selectedCitation?.chunk_text === citation.chunk_text;

              return (
                <button
                  key={i}
                  onClick={() => onCitationClick(citation)}
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all hover:opacity-80 ${
                    isSelected
                      ? "ring-2 ring-amber-400 ring-offset-1"
                      : ""
                  }`}
                  style={{
                    backgroundColor: `${COLOR.amber}18`,
                    color: COLOR.amber,
                  }}
                  title={citation.filename}
                >
                  <SourceIcon />
                  Source {i + 1}
                </button>
              );
            })}
          </div>
        )}
    </>
  );
}

/* ── Thinking indicator ── */

function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-md px-5 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            <span
              className="w-2 h-2 rounded-full animate-bounce"
              style={{ backgroundColor: COLOR.amber, animationDelay: "0ms" }}
            />
            <span
              className="w-2 h-2 rounded-full animate-bounce"
              style={{
                backgroundColor: COLOR.amber,
                animationDelay: "150ms",
              }}
            />
            <span
              className="w-2 h-2 rounded-full animate-bounce"
              style={{
                backgroundColor: COLOR.amber,
                animationDelay: "300ms",
              }}
            />
          </div>
          <div>
            <p className="text-sm text-slate-600">Generating answer...</p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              MedRAG Provider
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Insufficient info / error banner ── */

function InsufficientInfoBanner({ message }: { message: string }) {
  return (
    <div className="flex justify-start">
      <div
        className="max-w-[85%] rounded-2xl rounded-bl-md px-4 py-3 border"
        style={{
          backgroundColor: `${COLOR.amber}0d`,
          borderColor: `${COLOR.amber}30`,
        }}
      >
        <div className="flex items-start gap-2.5">
          <WarningIcon />
          <div>
            <p className="text-sm text-slate-700">{message}</p>
            <p className="text-xs text-slate-400 mt-1.5">
              Try uploading more relevant documents or rephrasing your question.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Empty state ── */

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
        style={{ backgroundColor: `${COLOR.amber}15` }}
      >
        <svg
          className="w-8 h-8"
          fill="none"
          viewBox="0 0 24 24"
          stroke={COLOR.amber}
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"
          />
        </svg>
      </div>
      <h3
        className="text-xl text-slate-900 mb-2"
        style={{ fontFamily: FONT_HEADING }}
      >
        Ask your documents anything
      </h3>
      <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
        Start a conversation to query your uploaded medical documents. Answers
        are generated using retrieval-augmented generation with inline citations.
      </p>
      <div className="flex flex-wrap justify-center gap-2 mt-6">
        {[
          "Summarize key findings",
          "What are the side effects?",
          "Compare treatment options",
        ].map((suggestion) => (
          <span
            key={suggestion}
            className="px-3 py-1.5 rounded-full text-xs text-slate-500 border border-slate-200 bg-white"
          >
            {suggestion}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────── Utility ─────────────────────── */

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/* ─────────────────────── Icons (inline SVGs) ─────────────────────── */

function PlusIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg
      className="w-3.5 h-3.5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z"
      />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function SourceIcon() {
  return (
    <svg
      className="w-3 h-3"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
      />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
      />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      className="w-5 h-5 shrink-0 mt-0.5"
      fill="none"
      viewBox="0 0 24 24"
      stroke={COLOR.amber}
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
      />
    </svg>
  );
}

function ChatBubbleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <div className="flex items-center gap-2 text-slate-400">
      <svg
        className="w-5 h-5 animate-spin"
        fill="none"
        viewBox="0 0 24 24"
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
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span className="text-sm">Loading...</span>
    </div>
  );
}

function SpinnerSmall() {
  return (
    <svg
      className="w-4 h-4 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
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
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
