import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuthContext } from "../../components/AuthProvider";

export default function SignUp() {
  const { signUp } = useAuthContext();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await signUp(email, password, fullName, orgName);
      setSuccess(true);
    } catch (err: any) {
      setError(err?.message ?? "Sign up failed. Please try again.");
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
            Create your account
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
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm font-medium text-green-800">
              Check your email for a verification link to complete your
              registration.
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

              <div>
                <label
                  htmlFor="orgName"
                  className="mb-1 block text-sm font-medium"
                  style={{
                    fontFamily: "'IBM Plex Sans', sans-serif",
                    color: "#0f172a",
                  }}
                >
                  Organization name
                </label>
                <input
                  id="orgName"
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                  style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
                  placeholder="Your organization"
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
                {loading ? "Creating account..." : "Create account"}
              </button>
            </form>

            <p
              className="mt-6 text-center text-sm"
              style={{
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: "#64748b",
              }}
            >
              Already have an account?{" "}
              <Link
                to="/signin"
                className="font-medium transition hover:underline"
                style={{ color: "#d97706" }}
              >
                Sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
