import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuthContext } from "../../components/AuthProvider";

export default function ForgotPassword() {
  const { forgotPassword } = useAuthContext();

  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err: any) {
      setError(err?.message ?? "Failed to send reset link. Please try again.");
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
            Reset your password
          </p>
        </div>

        {/* Success */}
        {success ? (
          <div
            className="rounded-lg border border-green-200 bg-green-50 px-4 py-5 text-center"
            style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
          >
            <svg
              className="mx-auto mb-2 h-10 w-10 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            <p className="text-sm font-medium text-green-800">
              A password reset link has been sent to{" "}
              <span className="font-semibold">{email}</span>. Please check your
              inbox.
            </p>
            <Link
              to="/signin"
              className="mt-3 inline-block text-sm font-medium transition hover:underline"
              style={{ color: "#d97706" }}
            >
              Back to sign in
            </Link>
          </div>
        ) : (
          <>
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
                  htmlFor="email"
                  className="mb-1 block text-sm font-medium"
                  style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    color: "#0f172a",
                  }}
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                  style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
                  placeholder="you@example.com"
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
                {loading ? "Sending..." : "Send reset link"}
              </button>
            </form>

            <p
              className="mt-6 text-center text-sm"
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: "#64748b",
              }}
            >
              <Link
                to="/signin"
                className="font-medium transition hover:underline"
                style={{ color: "#d97706" }}
              >
                Back to sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
