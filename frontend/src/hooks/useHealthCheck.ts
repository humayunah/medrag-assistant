import { useEffect, useState } from "react";

type ServerStatus = "checking" | "waking" | "ready" | "error";

export function useHealthCheck() {
  const [status, setStatus] = useState<ServerStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 30; // ~60s max

    const check = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL?.replace("/api/v1", "") || "";
        const res = await fetch(`${baseUrl}/health/live`, {
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok && !cancelled) {
          setStatus("ready");
          return;
        }
      } catch {
        // Server not ready
      }

      attempts++;
      if (!cancelled) {
        if (attempts >= maxAttempts) {
          setStatus("error");
        } else {
          setStatus("waking");
          setTimeout(check, 2000);
        }
      }
    };

    check();
    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}
