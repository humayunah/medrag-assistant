import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "../../services/api";

const FONT_HEADING = "'DM Serif Display', serif";
const FONT_BODY = "'IBM Plex Sans', sans-serif";

const ACTION_TYPES = [
  { value: "", label: "All Actions" },
  { value: "create", label: "Create" },
  { value: "update", label: "Update" },
  { value: "delete", label: "Delete" },
  { value: "login", label: "Login" },
  { value: "logout", label: "Logout" },
  { value: "upload", label: "Upload" },
  { value: "query", label: "Query" },
  { value: "invite", label: "Invite" },
];

interface AuditEntry {
  id: string;
  timestamp: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
}

interface AuditResponse {
  items: AuditEntry[];
  total: number;
  page: number;
  page_size: number;
}

const PAGE_SIZE = 20;

function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
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

export default function AuditLog() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [userSearch, setUserSearch] = useState("");

  const { data, isLoading, isError } = useQuery<AuditResponse>({
    queryKey: ["audit-logs", page, actionFilter, dateFrom, dateTo, userSearch],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(PAGE_SIZE));
      if (actionFilter) params.set("action", actionFilter);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (userSearch) params.set("user", userSearch);

      const { data } = await api.get(`/audit-logs?${params.toString()}`);
      return data;
    },
    retry: false,
  });

  const entries = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function handleFilterChange() {
    setPage(1);
  }

  return (
    <div className="p-6 lg:p-10 max-w-7xl mx-auto" style={{ fontFamily: FONT_BODY }}>
      {/* Header */}
      <div className="mb-8">
        <h1
          className="text-3xl text-[#0f172a]"
          style={{ fontFamily: FONT_HEADING }}
        >
          Audit Log
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Track all activity across your organization
        </p>
      </div>

      {/* Filter bar */}
      <div className="mb-6 flex flex-wrap items-end gap-4">
        {/* Action type */}
        <div className="min-w-[160px]">
          <label className="mb-1 block text-xs font-medium text-slate-500 uppercase tracking-wider">
            Action
          </label>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              handleFilterChange();
            }}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
          >
            {ACTION_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Date from */}
        <div className="min-w-[150px]">
          <label className="mb-1 block text-xs font-medium text-slate-500 uppercase tracking-wider">
            From
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              handleFilterChange();
            }}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
          />
        </div>

        {/* Date to */}
        <div className="min-w-[150px]">
          <label className="mb-1 block text-xs font-medium text-slate-500 uppercase tracking-wider">
            To
          </label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              handleFilterChange();
            }}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
          />
        </div>

        {/* User search */}
        <div className="flex-1 min-w-[200px]">
          <label className="mb-1 block text-xs font-medium text-slate-500 uppercase tracking-wider">
            User
          </label>
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              value={userSearch}
              onChange={(e) => {
                setUserSearch(e.target.value);
                handleFilterChange();
              }}
              placeholder="Search by email or name..."
              className="w-full rounded-lg border border-slate-300 pl-9 pr-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
            />
          </div>
        </div>

        {/* Clear filters */}
        {(actionFilter || dateFrom || dateTo || userSearch) && (
          <button
            onClick={() => {
              setActionFilter("");
              setDateFrom("");
              setDateTo("");
              setUserSearch("");
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-16 text-center">
          <Spinner className="h-6 w-6 mx-auto text-[#d97706]" />
          <p className="mt-3 text-sm text-slate-500">Loading audit log...</p>
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-16 text-center">
          <svg
            className="mx-auto h-10 w-10 text-slate-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
          </svg>
          <p className="mt-3 text-sm font-medium text-[#0f172a]">
            Audit log not available yet
          </p>
          <p className="mt-1 text-xs text-slate-400">
            The audit log endpoint is not yet connected. Activity will appear here once{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px] font-mono">
              GET /api/v1/audit-logs
            </code>{" "}
            is implemented.
          </p>
        </div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-16 text-center">
          <svg
            className="mx-auto h-10 w-10 text-slate-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
          </svg>
          <p className="mt-3 text-sm font-medium text-[#0f172a]">No activity recorded</p>
          <p className="mt-1 text-xs text-slate-400">
            Audit events will appear here as your team uses the platform.
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60">
                    <th className="px-6 py-3 text-left font-medium text-slate-500 whitespace-nowrap">Timestamp</th>
                    <th className="px-6 py-3 text-left font-medium text-slate-500 whitespace-nowrap">User</th>
                    <th className="px-6 py-3 text-left font-medium text-slate-500 whitespace-nowrap">Action</th>
                    <th className="px-6 py-3 text-left font-medium text-slate-500 whitespace-nowrap">Resource Type</th>
                    <th className="px-6 py-3 text-left font-medium text-slate-500 whitespace-nowrap">Resource ID</th>
                    <th className="px-6 py-3 text-left font-medium text-slate-500 whitespace-nowrap">IP Address</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {entries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 text-slate-500 whitespace-nowrap">
                        {new Date(entry.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-[#0f172a] whitespace-nowrap">{entry.user_email}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 capitalize">
                          {entry.action}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600 whitespace-nowrap font-mono text-xs">
                        {entry.resource_type}
                      </td>
                      <td className="px-6 py-4 text-slate-400 whitespace-nowrap font-mono text-xs">
                        {entry.resource_id}
                      </td>
                      <td className="px-6 py-4 text-slate-400 whitespace-nowrap font-mono text-xs">
                        {entry.ip_address}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Showing {(page - 1) * PAGE_SIZE + 1}
              &ndash;
              {Math.min(page * PAGE_SIZE, total)} of {total} entries
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
