import { Link } from "react-router-dom";

/* ------------------------------------------------------------------ */
/*  Keyframe styles injected once via <style> tag                     */
/* ------------------------------------------------------------------ */
const animationStyles = `
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(28px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to   { opacity: 1; transform: translateX(0); }
}
@keyframes pulseGlow {
  0%, 100% { opacity: 0.45; }
  50%      { opacity: 0.7; }
}

.anim-fade-up-1 { animation: fadeInUp 0.7s ease-out 0.1s both; }
.anim-fade-up-2 { animation: fadeInUp 0.7s ease-out 0.25s both; }
.anim-fade-up-3 { animation: fadeInUp 0.7s ease-out 0.4s both; }
.anim-fade-up-4 { animation: fadeInUp 0.7s ease-out 0.55s both; }
.anim-fade-in    { animation: fadeIn 0.9s ease-out 0.3s both; }
.anim-slide-left { animation: slideInLeft 0.6s ease-out both; }

.dot-grid {
  background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1px);
  background-size: 28px 28px;
}

.heading-font { font-family: 'DM Serif Display', serif; }
.body-font    { font-family: 'IBM Plex Sans', sans-serif; }
`;

/* ------------------------------------------------------------------ */
/*  Inline SVG icon components (no external libs)                     */
/* ------------------------------------------------------------------ */

function IconCitation() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
      <path d="M9 15h6" />
      <path d="M9 11h6" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l7 4v5c0 5.25-3.5 9.74-7 11-3.5-1.26-7-5.75-7-11V6l7-4Z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.35-4.35" />
      <path d="M11 8v6" />
      <path d="M8 11h6" />
    </svg>
  );
}

function IconBolt() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z" />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function IconCpu() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 15h3M1 9h3M1 15h3" />
    </svg>
  );
}

function IconMessageCircle() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z" />
    </svg>
  );
}

function IconArrowRight() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block ml-1.5">
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const features = [
  {
    icon: <IconCitation />,
    title: "Citation-Backed Answers",
    desc: "Every response references the exact source document and page number. No hallucinated claims — just traceable, auditable evidence.",
  },
  {
    icon: <IconShield />,
    title: "Multi-Tenant RBAC",
    desc: "Full organization isolation with granular roles: Admin, Doctor, Nurse, and Staff. Each tenant's data stays completely separate.",
  },
  {
    icon: <IconSearch />,
    title: "Hybrid Search",
    desc: "Combines pgvector semantic search with BM25 keyword matching, fused via Reciprocal Rank Fusion for superior retrieval accuracy.",
  },
  {
    icon: <IconBolt />,
    title: "Real-Time Processing",
    desc: "WebSocket-driven updates stream processing status live as documents are ingested, chunked, embedded, and indexed.",
  },
];

const steps = [
  {
    num: "01",
    icon: <IconUpload />,
    title: "Upload",
    desc: "Drop PDF or scanned medical documents. Tesseract OCR handles image-based pages automatically.",
  },
  {
    num: "02",
    icon: <IconCpu />,
    title: "Process",
    desc: "Documents are chunked, embedded, and indexed into pgvector. BM25 indices update in parallel for hybrid retrieval.",
  },
  {
    num: "03",
    icon: <IconMessageCircle />,
    title: "Query",
    desc: "Ask natural-language questions. Gemini AI synthesizes answers grounded in your documents with inline citations.",
  },
];

const techStack = [
  "React",
  "FastAPI",
  "PostgreSQL",
  "pgvector",
  "Supabase",
  "Tesseract OCR",
  "Gemini AI",
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function Landing() {
  return (
    <>
      {/* Inject keyframes + font import */}
      <style>{animationStyles}</style>

      <div className="body-font bg-[#faf7f2] text-[#0f172a] min-h-screen overflow-x-hidden">
        {/* ========== NAV ========== */}
        <nav className="relative z-20 w-full px-6 py-5 flex items-center justify-between max-w-7xl mx-auto">
          <Link to="/" className="flex items-center gap-2.5 group">
            {/* Logo mark */}
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-[#0f172a] text-white text-sm font-bold tracking-tight heading-font">
              M
            </span>
            <span className="heading-font text-xl tracking-tight text-[#0f172a]">
              MedRAG
            </span>
          </Link>

          <div className="flex items-center gap-3">
            <Link
              to="/signin"
              className="hidden sm:inline-flex px-4 py-2 text-sm font-medium text-[#0f172a] rounded-lg border border-[#0f172a]/15 hover:bg-[#0f172a]/5 transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/demo"
              className="inline-flex px-4 py-2 text-sm font-semibold text-white bg-[#d97706] rounded-lg hover:bg-[#b45309] transition-colors shadow-sm"
            >
              Live Demo
            </Link>
          </div>
        </nav>

        {/* ========== HERO ========== */}
        <section className="relative pt-12 pb-24 sm:pt-20 sm:pb-32 px-6">
          {/* Dot-grid background decoration */}
          <div
            aria-hidden="true"
            className="dot-grid absolute inset-0 opacity-[0.35] pointer-events-none"
          />
          {/* Amber glow accent */}
          <div
            aria-hidden="true"
            className="absolute top-16 left-1/2 -translate-x-1/2 w-[480px] h-[480px] rounded-full bg-[#d97706]/8 blur-[100px] pointer-events-none"
            style={{ animation: "pulseGlow 6s ease-in-out infinite" }}
          />

          <div className="relative z-10 max-w-3xl mx-auto text-center">
            {/* Eyebrow */}
            <p className="anim-fade-up-1 inline-flex items-center gap-2 px-3 py-1 mb-6 text-xs font-semibold uppercase tracking-widest text-[#059669] bg-[#059669]/10 rounded-full border border-[#059669]/20">
              <span className="w-1.5 h-1.5 rounded-full bg-[#059669] inline-block" />
              Open-Source RAG Platform
            </p>

            <h1 className="anim-fade-up-2 heading-font text-4xl sm:text-5xl md:text-6xl leading-[1.1] tracking-tight">
              Medical Documents,{" "}
              <span className="text-[#d97706]">Intelligently</span> Answered
            </h1>

            <p className="anim-fade-up-3 mt-6 text-lg sm:text-xl text-[#0f172a]/65 max-w-2xl mx-auto leading-relaxed">
              Upload clinical PDFs, research papers, and scanned records.
              Ask questions in plain language and get citation-backed answers
              grounded in <em>your</em> documents — not the open internet.
            </p>

            <div className="anim-fade-up-4 mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/demo"
                className="inline-flex items-center px-7 py-3.5 text-base font-semibold text-white bg-[#d97706] rounded-xl hover:bg-[#b45309] transition-all shadow-lg shadow-[#d97706]/20 hover:shadow-[#d97706]/30 hover:-translate-y-0.5"
              >
                Try Live Demo
                <IconArrowRight />
              </Link>
              <Link
                to="/signin"
                className="inline-flex items-center px-7 py-3.5 text-base font-semibold text-[#0f172a] bg-white rounded-xl border border-[#0f172a]/15 hover:border-[#0f172a]/30 hover:bg-[#0f172a]/[0.03] transition-all"
              >
                Sign In
              </Link>
            </div>
          </div>

          {/* Decorative crosshair lines */}
          <div aria-hidden="true" className="hidden lg:block absolute top-24 left-[8%] w-px h-32 bg-gradient-to-b from-transparent via-[#0f172a]/10 to-transparent" />
          <div aria-hidden="true" className="hidden lg:block absolute top-32 right-[10%] w-px h-24 bg-gradient-to-b from-transparent via-[#d97706]/20 to-transparent" />
        </section>

        {/* ========== FEATURES GRID ========== */}
        <section className="relative py-20 sm:py-28 px-6 bg-white">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-14">
              <p className="text-xs font-semibold uppercase tracking-widest text-[#d97706] mb-3">
                Capabilities
              </p>
              <h2 className="heading-font text-3xl sm:text-4xl tracking-tight">
                Built for Clinical Rigor
              </h2>
              <p className="mt-4 text-[#0f172a]/55 max-w-lg mx-auto">
                Every feature is designed around the requirements of medical
                document workflows — accuracy, auditability, and access control.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-6 lg:gap-8">
              {features.map((f, i) => (
                <div
                  key={f.title}
                  className="group relative p-7 sm:p-8 rounded-2xl border border-[#0f172a]/[0.06] bg-[#faf7f2]/60 hover:bg-white hover:shadow-lg hover:shadow-[#0f172a]/[0.04] transition-all duration-300"
                  style={{
                    animationDelay: `${i * 0.1}s`,
                  }}
                >
                  {/* Icon container */}
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#0f172a] text-white mb-5 group-hover:bg-[#d97706] transition-colors duration-300">
                    {f.icon}
                  </div>
                  <h3 className="heading-font text-xl mb-2">{f.title}</h3>
                  <p className="text-[#0f172a]/60 leading-relaxed text-[0.938rem]">
                    {f.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ========== HOW IT WORKS ========== */}
        <section className="py-20 sm:py-28 px-6">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-xs font-semibold uppercase tracking-widest text-[#059669] mb-3">
                Workflow
              </p>
              <h2 className="heading-font text-3xl sm:text-4xl tracking-tight">
                Three Steps to Answers
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
              {steps.map((s, i) => (
                <div key={s.num} className="relative text-center group">
                  {/* Connector line (between cards on md+) */}
                  {i < steps.length - 1 && (
                    <div
                      aria-hidden="true"
                      className="hidden md:block absolute top-14 left-[calc(50%+40px)] w-[calc(100%-80px)] h-px border-t-2 border-dashed border-[#0f172a]/10"
                    />
                  )}

                  {/* Step number badge */}
                  <span className="inline-block mb-4 text-xs font-bold tracking-widest text-[#d97706]/70 uppercase">
                    Step {s.num}
                  </span>

                  {/* Icon circle */}
                  <div className="mx-auto w-[72px] h-[72px] rounded-2xl bg-white border border-[#0f172a]/[0.08] shadow-sm flex items-center justify-center text-[#0f172a] mb-5 group-hover:border-[#d97706]/30 group-hover:shadow-md transition-all duration-300">
                    {s.icon}
                  </div>

                  <h3 className="heading-font text-xl mb-2">{s.title}</h3>
                  <p className="text-[#0f172a]/55 text-[0.938rem] leading-relaxed max-w-xs mx-auto">
                    {s.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ========== TECH STACK ========== */}
        <section className="py-16 sm:py-20 px-6 bg-[#0f172a]">
          <div className="max-w-5xl mx-auto text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#d97706] mb-3">
              Tech Stack
            </p>
            <h2 className="heading-font text-2xl sm:text-3xl text-white tracking-tight mb-10">
              Modern Infrastructure, Clinical Grade
            </h2>

            <div className="flex flex-wrap items-center justify-center gap-3">
              {techStack.map((t) => (
                <span
                  key={t}
                  className="inline-flex px-4 py-2 text-sm font-medium rounded-lg border border-white/10 text-white/80 bg-white/[0.04] hover:bg-white/[0.08] hover:text-white transition-colors"
                  style={{ fontFamily: "'IBM Plex Mono', 'Fira Code', monospace" }}
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* ========== CTA FOOTER ========== */}
        <section className="py-20 sm:py-28 px-6">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="heading-font text-3xl sm:text-4xl tracking-tight mb-4">
              Ready to Explore?
            </h2>
            <p className="text-[#0f172a]/55 text-lg mb-10 max-w-md mx-auto">
              See how RAG-powered search transforms the way you work with
              medical documents.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/demo"
                className="inline-flex items-center px-7 py-3.5 text-base font-semibold text-white bg-[#d97706] rounded-xl hover:bg-[#b45309] transition-all shadow-lg shadow-[#d97706]/20 hover:shadow-[#d97706]/30 hover:-translate-y-0.5"
              >
                Try Live Demo
                <IconArrowRight />
              </Link>
              <Link
                to="/signup"
                className="inline-flex items-center px-7 py-3.5 text-base font-semibold text-[#0f172a] bg-white rounded-xl border border-[#0f172a]/15 hover:border-[#0f172a]/30 transition-all"
              >
                Create Account
              </Link>
            </div>
          </div>
        </section>

        {/* ========== FOOTER BAR ========== */}
        <footer className="border-t border-[#0f172a]/[0.06] py-8 px-6">
          <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[#0f172a]/40">
            <span className="heading-font text-base text-[#0f172a]/60">
              MedRAG Assistant
            </span>
            <span>
              Built with FastAPI, React &amp; pgvector
            </span>
          </div>
        </footer>
      </div>
    </>
  );
}
