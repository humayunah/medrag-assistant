import { useCallback, useEffect, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "../services/supabase";
import type { AppRole, UserProfile } from "../types";
import api from "../services/api";

interface AuthState {
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  loading: boolean;
  role: AppRole | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    profile: null,
    loading: true,
    role: null,
  });

  const fetchProfile = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setState((s) => ({
        ...s,
        profile: data.profile,
        role: data.profile?.role ?? null,
      }));
    } catch {
      // Profile fetch failed — user might not have completed setup
    }
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState((s) => ({
        ...s,
        session,
        user: session?.user ?? null,
        loading: false,
      }));
      if (session) fetchProfile();
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState((s) => ({
        ...s,
        session,
        user: session?.user ?? null,
        loading: false,
      }));
      if (session) fetchProfile();
      else setState((s) => ({ ...s, profile: null, role: null }));
    });

    return () => subscription.unsubscribe();
  }, [fetchProfile]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
    },
    [],
  );

  const signUp = useCallback(
    async (email: string, password: string, fullName: string, orgName: string) => {
      const { data } = await api.post("/auth/signup", {
        email,
        password,
        full_name: fullName,
        org_name: orgName,
      });
      // Sign in after signup
      await supabase.auth.signInWithPassword({ email, password });
      return data;
    },
    [],
  );

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setState({
      user: null,
      session: null,
      profile: null,
      loading: false,
      role: null,
    });
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) throw error;
  }, []);

  return {
    ...state,
    isAuthenticated: !!state.session,
    signIn,
    signUp,
    signOut,
    forgotPassword,
  };
}
