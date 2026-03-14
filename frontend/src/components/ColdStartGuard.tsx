import type { ReactNode } from "react";
import { useHealthCheck } from "../hooks/useHealthCheck";

export function ColdStartGuard({ children }: { children: ReactNode }) {
  const status = useHealthCheck();

  if (status === "ready") return <>{children}</>;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f172a]">
      <div className="text-center max-w-md px-8">
        {/* Pulse ring animation */}
        <div className="relative mx-auto mb-8 w-20 h-20">
          <div className="absolute inset-0 rounded-full border-2 border-amber-500/30 animate-ping" />
          <div className="absolute inset-2 rounded-full border-2 border-amber-500/50 animate-ping [animation-delay:200ms]" />
          <div className="absolute inset-4 rounded-full border-2 border-amber-500/70 animate-pulse" />
          <div className="absolute inset-[22px] rounded-full bg-amber-500" />
        </div>

        <h2
          className="text-xl font-semibold text-white mb-2"
          style={{ fontFamily: "'DM Serif Display', serif" }}
        >
          {status === "error" ? "Connection Error" : "Waking Up Server"}
        </h2>

        <p className="text-slate-400 text-sm leading-relaxed">
          {status === "error" ? (
            <>
              Unable to reach the server. Please check your connection and{" "}
              <button
                onClick={() => window.location.reload()}
                className="text-amber-500 underline underline-offset-2 hover:text-amber-400"
              >
                try again
              </button>
              .
            </>
          ) : (
            <>
              The server is spinning up from a cold start. This typically takes
              about <span className="text-amber-500 font-medium">30 seconds</span>.
            </>
          )}
        </p>

        {status === "waking" && (
          <div className="mt-6 w-full bg-slate-800 rounded-full h-1 overflow-hidden">
            <div className="h-full bg-amber-500 rounded-full animate-[progress_8s_ease-in-out_infinite]" />
          </div>
        )}
      </div>
    </div>
  );
}
