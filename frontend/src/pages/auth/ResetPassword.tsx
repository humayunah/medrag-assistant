import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../../services/supabase";

export default function ResetPassword() {
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      });
      if (updateError) throw updateError;
      navigate("/signin");
    } catch (err: any) {
      setError(err?.message ?? "Failed to reset password. Please try again.");
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
            Set a new password
          </p>
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
              htmlFor="password"
              className="mb-1 block text-sm font-medium"
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: "#0f172a",
              }}
            >
              New password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
              style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
              placeholder="Enter new password"
            />
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="mb-1 block text-sm font-medium"
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: "#0f172a",
              }}
            >
              Confirm password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
              style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
              placeholder="Re-enter new password"
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
            {loading ? "Updating..." : "Reset password"}
          </button>
        </form>
      </div>
    </div>
  );
}
