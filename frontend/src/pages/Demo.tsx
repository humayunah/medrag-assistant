import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";
import { useAuthContext } from "../components/AuthProvider";

/* ------------------------------------------------------------------ */
/*  Design tokens                                                      */
/* ------------------------------------------------------------------ */

const FONT_HEADING = "'DM Serif Display', serif";
const FONT_BODY = "'IBM Plex Sans', sans-serif";

const COLOR = {
  slate: "#0f172a",
  amber: "#d97706",
  cream: "#faf7f2",
} as const;

/* ------------------------------------------------------------------ */
/*  Suggested queries                                                  */
/* ------------------------------------------------------------------ */

const SUGGESTIONS = [
  {
    label: "Cardiology",
    query: "What treatments are used for atrial fibrillation and cardioversion?",
    icon: HeartIcon,
  },
  {
    label: "Orthopedic",
    query: "What are the post-operative findings in knee arthroplasty?",
    icon: BoneIcon,
  },
  {
    label: "Neurology",
    query: "What neuropsychological symptoms are evaluated in neurology consultations?",
    icon: BrainIcon,
  },
  {
    label: "Radiology",
    query: "What did the MRI brain scan reveal?",
    icon: ScanIcon,
  },
  {
    label: "Gastroenterology",
    query: "What are the indications for laparoscopic cholecystectomy?",
    icon: ClipboardIcon,
  },
] as const;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function Demo() {
  const navigate = useNavigate();
  const { enterDemoMode } = useAuthContext();

  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState("");

  /* ── Acquire demo token on mount ── */
  useEffect(() => {
    let cancelled = false;

    async function acquireSession() {
      try {
        const { data } = await api.post("/demo/session");

        if (cancelled) return;

        // Install a one-time request interceptor that injects the demo token.
        // We store the interceptor id so we could eject it later if needed.
        const interceptorId = api.interceptors.request.use((config) => {
          config.headers.Authorization = `Bearer ${data.access_token}`;
          return config;
        });

        // Stash for potential cleanup
        (window as unknown as Record<string, unknown>).__demoInterceptorId =
          interceptorId;
        (window as unknown as Record<string, unknown>).__demoTenantId =
          data.demo_tenant_id;

        enterDemoMode();
        setStatus("ready");
      } catch (err: unknown) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Failed to start demo session";
        setErrorMessage(message);
        setStatus("error");
      }
    }

    acquireSession();

    return () => {
      cancelled = true;
    };
  }, []);

  /* ── Navigate with pre-filled query ── */
  function handleSuggestionClick(query: string) {
    navigate("/query", { state: { prefill: query } });
  }

  /* ── Loading state ── */
  if (status === "loading") {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center"
        style={{ fontFamily: FONT_BODY, backgroundColor: COLOR.cream }}
      >
        <Spinner />
        <p
          className="mt-6 text-lg text-[#0f172a]/70"
          style={{ fontFamily: FONT_HEADING }}
        >
          Preparing your demo environment...
        </p>
        <p className="mt-2 text-sm text-[#0f172a]/40">
          This should only take a moment.
        </p>
      </div>
    );
  }

  /* ── Error state ── */
  if (status === "error") {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center px-6"
        style={{ fontFamily: FONT_BODY, backgroundColor: COLOR.cream }}
      >
        <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mb-5">
          <ErrorIcon />
        </div>
        <h2
          className="text-2xl text-[#0f172a] mb-2"
          style={{ fontFamily: FONT_HEADING }}
        >
          Unable to Start Demo
        </h2>
        <p className="text-sm text-[#0f172a]/55 max-w-md text-center mb-6">
          {errorMessage}
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center px-5 py-2.5 text-sm font-semibold text-white rounded-lg transition-colors hover:opacity-90"
            style={{ backgroundColor: COLOR.amber }}
          >
            Try Again
          </button>
          <Link
            to="/"
            className="inline-flex items-center px-5 py-2.5 text-sm font-medium text-[#0f172a] rounded-lg border border-[#0f172a]/15 hover:bg-[#0f172a]/5 transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  /* ── Ready state ── */
  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ fontFamily: FONT_BODY, backgroundColor: COLOR.cream }}
    >
      {/* ── Demo mode banner ── */}
      <div
        className="w-full px-4 py-3 flex items-center justify-center gap-3 text-sm"
        style={{ backgroundColor: COLOR.slate, color: "#fff" }}
      >
        <span className="inline-flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: COLOR.amber }}
          />
          <span className="font-medium">You're in demo mode</span>
          <span className="hidden sm:inline text-white/50">&mdash;</span>
        </span>
        <Link
          to="/signup"
          className="inline-flex items-center gap-1 px-3 py-1 rounded-md text-xs font-semibold transition-colors hover:opacity-90"
          style={{ backgroundColor: COLOR.amber, color: "#fff" }}
        >
          Sign up for full access
          <ArrowRightSmallIcon />
        </Link>
      </div>

      {/* ── Main content ── */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16 sm:py-24">
        {/* Header */}
        <div className="text-center mb-12">
          <div
            className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-6"
            style={{ backgroundColor: `${COLOR.amber}18` }}
          >
            <SparklesIcon />
          </div>
          <h1
            className="text-3xl sm:text-4xl tracking-tight text-[#0f172a] mb-3"
            style={{ fontFamily: FONT_HEADING }}
          >
            Try MedRAG Assistant
          </h1>
          <p className="text-[#0f172a]/55 text-base sm:text-lg max-w-lg mx-auto leading-relaxed">
            Explore how AI-powered retrieval answers medical document queries.
            Pick a suggestion below or head to the query page.
          </p>
        </div>

        {/* ── Suggestion cards ── */}
        <div className="w-full max-w-2xl grid gap-3">
          {SUGGESTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.query}
                onClick={() => handleSuggestionClick(s.query)}
                className="group flex items-center gap-4 w-full text-left px-5 py-4 rounded-xl border border-[#0f172a]/[0.06] bg-white hover:bg-white hover:shadow-lg hover:shadow-[#0f172a]/[0.04] hover:border-[#d97706]/30 transition-all duration-200"
              >
                {/* Icon */}
                <div
                  className="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-[#0f172a] group-hover:text-white transition-colors duration-200"
                  style={{
                    backgroundColor: `${COLOR.amber}12`,
                  }}
                >
                  <span className="group-hover:hidden">
                    <Icon color={COLOR.slate} />
                  </span>
                  <span
                    className="hidden group-hover:inline-flex w-10 h-10 rounded-lg items-center justify-center"
                    style={{ backgroundColor: COLOR.amber }}
                  >
                    <Icon color="#fff" />
                  </span>
                </div>

                {/* Text */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-widest text-[#0f172a]/35 mb-0.5">
                    Try asking
                  </p>
                  <p className="text-sm text-[#0f172a]/80 leading-snug truncate sm:whitespace-normal">
                    {s.query}
                  </p>
                </div>

                {/* Arrow */}
                <div className="shrink-0 text-[#0f172a]/20 group-hover:text-[#d97706] transition-colors">
                  <ArrowRightIcon />
                </div>
              </button>
            );
          })}
        </div>

        {/* ── Direct link ── */}
        <div className="mt-10 flex flex-col items-center gap-4">
          <Link
            to="/query"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white rounded-xl transition-all hover:opacity-90 hover:-translate-y-0.5 shadow-lg"
            style={{
              backgroundColor: COLOR.amber,
              boxShadow: `0 8px 24px ${COLOR.amber}30`,
            }}
          >
            Open Query Interface
            <ArrowRightSmallIcon />
          </Link>
          <p className="text-xs text-[#0f172a]/35">
            Demo session expires in 1 hour
          </p>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-[#0f172a]/[0.06] py-6 px-6">
        <div className="max-w-2xl mx-auto flex items-center justify-between text-xs text-[#0f172a]/35">
          <span style={{ fontFamily: FONT_HEADING }} className="text-sm text-[#0f172a]/50">
            MedRAG Assistant
          </span>
          <span>Demo mode &middot; Read-only access</span>
        </div>
      </footer>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Icons (inline SVGs, no external deps)                              */
/* ------------------------------------------------------------------ */

function Spinner() {
  return (
    <svg
      className="w-8 h-8 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke={COLOR.amber}
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill={COLOR.amber}
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      className="w-7 h-7 text-red-500"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
      />
    </svg>
  );
}

function SparklesIcon() {
  return (
    <svg
      className="w-7 h-7"
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
  );
}

function ArrowRightIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function ArrowRightSmallIcon() {
  return (
    <svg
      className="w-3.5 h-3.5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2.5}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function HeartIcon({ color }: { color: string }) {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
      />
    </svg>
  );
}

function BoneIcon({ color }: { color: string }) {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15.75 6.75a3 3 0 11-6 0M15.75 6.75v10.5m-7.5-10.5a3 3 0 116 0m-6 0v10.5m0 0a3 3 0 106 0m-6 0a3 3 0 116 0"
      />
    </svg>
  );
}

function BrainIcon({ color }: { color: string }) {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a3.187 3.187 0 01-1.47.88L12 18.75l-3.06-.9a3.187 3.187 0 01-1.47-.88L5 14.5m14 0V20a1 1 0 01-1 1h-2.5M5 14.5V20a1 1 0 001 1h2.5m5-3.75V21"
      />
    </svg>
  );
}

function ScanIcon({ color }: { color: string }) {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M3.75 12h16.5"
      />
    </svg>
  );
}

function ClipboardIcon({ color }: { color: string }) {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z"
      />
    </svg>
  );
}
