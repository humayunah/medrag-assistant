export type AppRole = "admin" | "doctor" | "nurse" | "staff";
export type DocumentStatus =
  | "pending"
  | "processing"
  | "ready"
  | "failed"
  | "archived";
export type InvitationStatus = "pending" | "accepted" | "expired" | "revoked";

export interface UserProfile {
  id: string;
  tenant_id: string;
  role: AppRole;
  full_name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  settings: Record<string, unknown>;
  created_at: string;
}

export interface Document {
  id: string;
  tenant_id: string;
  uploaded_by: string;
  filename: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  page_count: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface CitationSource {
  document_id: string;
  filename: string;
  page_number: number | null;
  section: string | null;
  chunk_text: string;
  relevance_score: number;
}

export interface QueryMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationSource[];
  created_at: string;
}

export interface QueryResponse {
  answer: string;
  citations: CitationSource[];
  conversation_id: string;
  cached: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: AppRole;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserProfile;
}

export interface HealthResponse {
  status: string;
  version?: string;
  checks?: Record<string, string>;
}

export interface ErrorResponse {
  detail: string;
  request_id?: string;
}
