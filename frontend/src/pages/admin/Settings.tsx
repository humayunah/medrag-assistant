import { useState, useEffect, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../../services/api";
import type { Tenant } from "../../types";

const FONT_HEADING = "'DM Serif Display', serif";
const FONT_BODY = "'IBM Plex Sans', sans-serif";

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

export default function Settings() {
  const queryClient = useQueryClient();
  const [orgName, setOrgName] = useState("");
  const [saved, setSaved] = useState(false);

  // ── Fetch tenant info ──
  const {
    data: tenant,
    isLoading,
    isError,
  } = useQuery<Tenant>({
    queryKey: ["tenant-me"],
    queryFn: async () => {
      const { data } = await api.get("/tenants/me");
      return data;
    },
  });

  // Sync form when data loads
  useEffect(() => {
    if (tenant?.name) {
      setOrgName(tenant.name);
    }
  }, [tenant?.name]);

  // ── Update org name ──
  const updateName = useMutation({
    mutationFn: async (name: string) => {
      await api.patch("/tenants/me", { name });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-me"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!orgName.trim()) return;
    updateName.mutate(orgName.trim());
  }

  const hasChanged = tenant?.name !== orgName.trim();

  return (
    <div className="p-6 lg:p-10 max-w-3xl mx-auto" style={{ fontFamily: FONT_BODY }}>
      {/* Header */}
      <div className="mb-8">
        <h1
          className="text-3xl text-[#0f172a]"
          style={{ fontFamily: FONT_HEADING }}
        >
          Organization Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your organization&apos;s profile and configuration
        </p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm px-6 py-16 text-center">
          <Spinner className="h-6 w-6 mx-auto text-[#d97706]" />
          <p className="mt-3 text-sm text-slate-500">Loading settings...</p>
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-6 text-center">
          <p className="text-sm text-red-600">
            Failed to load organization settings. Please try again.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* ── Organization Name ── */}
          <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="px-6 py-5 border-b border-slate-100">
              <h2
                className="text-lg text-[#0f172a]"
                style={{ fontFamily: FONT_HEADING }}
              >
                General
              </h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Basic information about your organization
              </p>
            </div>
            <form onSubmit={handleSave} className="px-6 py-5 space-y-4">
              <div>
                <label
                  htmlFor="org-name"
                  className="mb-1 block text-sm font-medium text-[#0f172a]"
                >
                  Organization Name
                </label>
                <input
                  id="org-name"
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => {
                    setOrgName(e.target.value);
                    setSaved(false);
                  }}
                  className="w-full max-w-md rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                  placeholder="Your organization name"
                />
              </div>

              {tenant?.slug && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-400">
                    Slug
                  </label>
                  <p className="text-sm text-slate-500 font-mono bg-slate-50 rounded-lg px-3 py-2 max-w-md">
                    {tenant.slug}
                  </p>
                </div>
              )}

              {tenant?.created_at && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-400">
                    Created
                  </label>
                  <p className="text-sm text-slate-500">
                    {new Date(tenant.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </p>
                </div>
              )}

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={!hasChanged || updateName.isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-[#d97706] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {updateName.isPending && <Spinner />}
                  {updateName.isPending ? "Saving..." : "Save Changes"}
                </button>

                {saved && (
                  <span className="inline-flex items-center gap-1 text-sm text-emerald-600">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                    Saved
                  </span>
                )}

                {updateName.isError && (
                  <span className="text-sm text-red-600">
                    Failed to save. Please try again.
                  </span>
                )}
              </div>
            </form>
          </section>

          {/* ── Current Plan ── */}
          <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="px-6 py-5 border-b border-slate-100">
              <h2
                className="text-lg text-[#0f172a]"
                style={{ fontFamily: FONT_HEADING }}
              >
                Subscription
              </h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Your current plan and usage
              </p>
            </div>
            <div className="px-6 py-5">
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-[#0f172a]">
                  Free Tier
                </span>
                <span className="text-xs text-slate-400">
                  Basic features included
                </span>
              </div>

              <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-lg bg-slate-50 px-4 py-3">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Team Members
                  </p>
                  <p className="mt-1 text-lg font-semibold text-[#0f172a]">
                    &mdash; <span className="text-sm font-normal text-slate-400">/ 5</span>
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-4 py-3">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Documents
                  </p>
                  <p className="mt-1 text-lg font-semibold text-[#0f172a]">
                    &mdash; <span className="text-sm font-normal text-slate-400">/ 50</span>
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-4 py-3">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Queries / Month
                  </p>
                  <p className="mt-1 text-lg font-semibold text-[#0f172a]">
                    &mdash; <span className="text-sm font-normal text-slate-400">/ 100</span>
                  </p>
                </div>
              </div>

              <p className="mt-4 text-xs text-slate-400">
                Upgrade options will be available in a future release.
              </p>
            </div>
          </section>

          {/* ── Danger Zone ── */}
          <section className="rounded-xl border border-red-200 bg-white shadow-sm">
            <div className="px-6 py-5 border-b border-red-100">
              <h2
                className="text-lg text-red-700"
                style={{ fontFamily: FONT_HEADING }}
              >
                Danger Zone
              </h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Irreversible actions that affect your entire organization
              </p>
            </div>
            <div className="px-6 py-5">
              <div className="flex items-start gap-4 rounded-lg border border-red-100 bg-red-50/50 px-4 py-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#0f172a]">
                    Delete Organization
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Permanently delete this organization and all its data, including documents,
                    conversations, and team member access. This action cannot be undone.
                  </p>
                </div>
                <button
                  disabled
                  className="shrink-0 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 opacity-50 cursor-not-allowed"
                  title="Organization deletion is not yet available"
                >
                  Delete Organization
                </button>
              </div>
              <p className="mt-3 text-xs text-slate-400">
                Organization deletion is currently disabled. Contact support if you need to delete your organization.
              </p>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
