import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../../services/api";
import { supabase } from "../../services/supabase";

interface InvitationDetails {
  email: string;
  role: string;
  org_name: string;
}

export default function AcceptInvitation() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);

  useEffect(() => {
    if (!token) {
      setError("Invalid invitation link. No token provided.");
      setValidating(false);
      return;
    }

    async function validateToken() {
      try {
        const { data } = await api.get(`/invitations/${token}`);
        setInvitation(data);
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ??
            err?.message ??
            "This invitation is invalid or has expired.",
        );
      } finally {
        setValidating(false);
      }
    }

    validateToken();
  }, [token]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      const { data } = await api.post(`/invitations/${token}/accept`, {
        full_name: fullName,
        password,
      });

      // Auto sign-in after accepting the invitation
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: data.email ?? invitation?.email ?? "",
        password,
      });

      if (signInError) throw signInError;

      navigate("/dashboard");
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
          err?.message ??
          "Failed to accept invitation. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: "#faf7f2" }}
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">
        {/* Brand */}
        <div className="mb-8 text-center">
          <h1
            className="text-3xl"
            style={{
              fontFamily: "'DM Serif Display', serif",
              color: "#0f172a",
            }}
          >
            Med<span style={{ color: "#d97706" }}>RAG</span>
          </h1>
          <p
            className="mt-1 text-sm"
            style={{
              fontFamily: "'IBM Plex Sans', sans-serif",
              color: "#64748b",
            }}
          >
            Accept your invitation
          </p>
        </div>

        {/* Loading / Validating */}
        {validating ? (
          <div className="flex items-center justify-center py-12">
            <svg
              className="h-6 w-6 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              style={{ color: "#d97706" }}
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
            <span
              className="ml-2 text-sm"
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: "#64748b",
              }}
            >
              Validating invitation...
            </span>
          </div>
        ) : error && !invitation ? (
          /* Error without invitation (validation failed) */
          <div
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
          >
            {error}
          </div>
        ) : invitation ? (
          <>
            {/* Invitation details */}
            <div
              className="mb-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
              style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
            >
              <p className="text-sm" style={{ color: "#64748b" }}>
                You have been invited to join
              </p>
              <p
                className="mt-1 text-base font-semibold"
                style={{ color: "#0f172a" }}
              >
                {invitation.org_name}
              </p>
              <div className="mt-2 flex items-center gap-2 text-sm">
                <span style={{ color: "#64748b" }}>Email:</span>
                <span style={{ color: "#0f172a" }}>{invitation.email}</span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-sm">
                <span style={{ color: "#64748b" }}>Role:</span>
                <span
                  className="inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize"
                  style={{
                    backgroundColor: "#fef3c7",
                    color: "#92400e",
                  }}
                >
                  {invitation.role}
                </span>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div
                className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label
                  htmlFor="fullName"
                  className="mb-1 block text-sm font-medium"
                  style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    color: "#0f172a",
                  }}
                >
                  Full name
                </label>
                <input
                  id="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                  style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
                  placeholder="Jane Doe"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="mb-1 block text-sm font-medium"
                  style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    color: "#0f172a",
                  }}
                >
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                  style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
                  placeholder="Create a password"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  backgroundColor: "#d97706",
                }}
              >
                {loading ? (
                  <svg
                    className="mr-2 h-4 w-4 animate-spin"
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
                ) : null}
                {loading ? "Accepting..." : "Accept invitation"}
              </button>
            </form>
          </>
        ) : null}
      </div>
    </div>
  );
}
