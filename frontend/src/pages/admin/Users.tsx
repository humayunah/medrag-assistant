import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../../services/api";
import type { AppRole, Invitation } from "../../types";

const FONT_HEADING = "'DM Serif Display', serif";
const FONT_BODY = "'IBM Plex Sans', sans-serif";

const ROLES: AppRole[] = ["admin", "doctor", "nurse", "staff"];

const roleBadgeColors: Record<AppRole, string> = {
  admin: "bg-red-100 text-red-700",
  doctor: "bg-blue-100 text-blue-700",
  nurse: "bg-emerald-100 text-emerald-700",
  staff: "bg-slate-100 text-slate-600",
};

const statusBadgeColors: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  accepted: "bg-emerald-100 text-emerald-700",
  expired: "bg-slate-100 text-slate-500",
  revoked: "bg-red-100 text-red-700",
};

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

export default function Users() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<AppRole>("staff");
  const [error, setError] = useState<string | null>(null);

  // ── Fetch invitations ──
  const {
    data: invitations = [],
    isLoading,
    isError,
  } = useQuery<Invitation[]>({
    queryKey: ["invitations"],
    queryFn: async () => {
      const { data } = await api.get("/invitations");
      return data;
    },
  });

  // ── Send invitation ──
  const sendInvite = useMutation({
    mutationFn: async ({ email, role }: { email: string; role: AppRole }) => {
      await api.post("/invitations", { email, role });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invitations"] });
      setModalOpen(false);
      setInviteEmail("");
      setInviteRole("staff");
      setError(null);
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail ?? "Failed to send invitation.");
    },
  });

  // ── Revoke invitation ──
  const revokeInvite = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/invitations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
  });

  function handleInviteSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    sendInvite.mutate({ email: inviteEmail, role: inviteRole });
  }

  const pendingInvitations = invitations.filter((i) => i.status === "pending");
  const otherInvitations = invitations.filter((i) => i.status !== "pending");

  return (
    <div className="p-6 lg:p-10 max-w-6xl mx-auto" style={{ fontFamily: FONT_BODY }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1
            className="text-3xl text-[#0f172a]"
            style={{ fontFamily: FONT_HEADING }}
          >
            Team Members
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage your organization&apos;s team and invitations
          </p>
        </div>
        <button
          onClick={() => {
            setModalOpen(true);
            setError(null);
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-[#d97706] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-amber-700 active:scale-[0.98]"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Invite User
        </button>
      </div>

      {/* User list placeholder */}
      <section className="mb-10">
        <h2
          className="text-lg text-[#0f172a] mb-4"
          style={{ fontFamily: FONT_HEADING }}
        >
          Members
        </h2>
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="px-6 py-12 text-center">
            <svg className="mx-auto h-10 w-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
            <p className="mt-3 text-sm text-slate-500">
              User list will be available once the users endpoint is connected.
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Use the invitation system below to add team members.
            </p>
          </div>
        </div>
      </section>

      {/* Pending Invitations */}
      <section className="mb-10">
        <h2
          className="text-lg text-[#0f172a] mb-4"
          style={{ fontFamily: FONT_HEADING }}
        >
          Pending Invitations
        </h2>

        {isLoading ? (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-12 text-center">
            <Spinner className="h-6 w-6 mx-auto text-[#d97706]" />
            <p className="mt-3 text-sm text-slate-500">Loading invitations...</p>
          </div>
        ) : isError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-6 text-center">
            <p className="text-sm text-red-600">Failed to load invitations. Please try again.</p>
          </div>
        ) : pendingInvitations.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-12 text-center">
            <svg className="mx-auto h-10 w-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
            </svg>
            <p className="mt-3 text-sm text-slate-500">No pending invitations</p>
            <p className="mt-1 text-xs text-slate-400">
              Click &quot;Invite User&quot; to add team members.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60">
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Email</th>
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Role</th>
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Status</th>
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Expires</th>
                  <th className="px-6 py-3 text-right font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pendingInvitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 text-[#0f172a]">{inv.email}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${roleBadgeColors[inv.role]}`}
                      >
                        {inv.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadgeColors[inv.status] ?? "bg-slate-100 text-slate-600"}`}
                      >
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(inv.expires_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => revokeInvite.mutate(inv.id)}
                        disabled={revokeInvite.isPending}
                        className="text-xs font-medium text-red-600 hover:text-red-700 transition disabled:opacity-50"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Past Invitations */}
      {otherInvitations.length > 0 && (
        <section>
          <h2
            className="text-lg text-[#0f172a] mb-4"
            style={{ fontFamily: FONT_HEADING }}
          >
            Past Invitations
          </h2>
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60">
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Email</th>
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Role</th>
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Status</th>
                  <th className="px-6 py-3 text-left font-medium text-slate-500">Sent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {otherInvitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 text-[#0f172a]">{inv.email}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${roleBadgeColors[inv.role]}`}
                      >
                        {inv.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadgeColors[inv.status] ?? "bg-slate-100 text-slate-600"}`}
                      >
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(inv.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Invite Modal ── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setModalOpen(false)}
          />

          {/* Modal */}
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl mx-4">
            <div className="flex items-center justify-between mb-5">
              <h3
                className="text-xl text-[#0f172a]"
                style={{ fontFamily: FONT_HEADING }}
              >
                Invite User
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 transition"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleInviteSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="invite-email"
                  className="mb-1 block text-sm font-medium text-[#0f172a]"
                >
                  Email Address
                </label>
                <input
                  id="invite-email"
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                  placeholder="colleague@example.com"
                />
              </div>

              <div>
                <label
                  htmlFor="invite-role"
                  className="mb-1 block text-sm font-medium text-[#0f172a]"
                >
                  Role
                </label>
                <select
                  id="invite-role"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as AppRole)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 bg-white capitalize"
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role} className="capitalize">
                      {role}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sendInvite.isPending}
                  className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[#d97706] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:opacity-60"
                >
                  {sendInvite.isPending && <Spinner />}
                  {sendInvite.isPending ? "Sending..." : "Send Invite"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
