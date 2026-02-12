import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Auth helpers
export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) throw error;
  return data;
}

export async function signUp(email: string, password: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  });

  if (error) throw error;
  return data;
}

export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

export async function getCurrentUser() {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  return user;
}

export async function getSession() {
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error) throw error;
  return session;
}

/**
 * Get a valid (non-expired) access token, refreshing the session if needed.
 * Use this instead of getSession() when sending tokens to the backend.
 */
export async function getValidAccessToken(): Promise<string | null> {
  const { data: { session }, error } = await supabase.auth.getSession();

  if (error || !session) {
    return null;
  }

  // If token expires within 60 seconds, refresh it proactively
  const expiresAt = session.expires_at; // Unix timestamp in seconds
  if (expiresAt) {
    const now = Math.floor(Date.now() / 1000);
    if (expiresAt - now < 60) {
      const { data: { session: refreshed }, error: refreshError } =
        await supabase.auth.refreshSession();
      if (refreshError || !refreshed) {
        return null;
      }
      return refreshed.access_token;
    }
  }

  return session.access_token;
}
