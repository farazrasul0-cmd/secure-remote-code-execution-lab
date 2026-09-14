export type ExecutionStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'COMPILE_ERROR'
  | 'TIME_LIMIT_EXCEEDED'
  | 'MEMORY_LIMIT_EXCEEDED'
  | 'OUTPUT_LIMIT_EXCEEDED'
  | 'RUNTIME_ERROR'
  | 'RESOURCE_LIMIT_EXCEEDED';

export type SupportedLanguage = 'python' | 'c' | 'cpp' | 'rust' | 'go' | 'javascript';

export interface LanguageInfo {
  id: string;
  name: string;
  extension: string;
  is_compiled: boolean;
  monaco_id: string;
  boilerplate: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface Submission {
  id: string;
  user_id: string;
  language: string;
  source_code: string;
  stdin_data?: string | null;
  status: ExecutionStatus;
  exit_code?: number | null;
  execution_time_ms?: number | null;
  peak_memory_bytes?: number | null;
  output_summary?: string | null;
  telemetry: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
}

export interface SubmissionCreate {
  language?: string;
  source_code: string;
  stdin_data?: string | null;
}

export interface SubmissionListResponse {
  items: Submission[];
  total: number;
  page: number;
  size: number;
}

export interface StreamChunk {
  type: 'stdout' | 'stderr' | 'system' | 'status';
  data?: string;
  sequence: number;
  timestamp?: number;
  status?: ExecutionStatus;
  exit_code?: number;
  execution_time_ms?: number;
  peak_memory_bytes?: number;
}

export type WebSocketState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'STREAMING'
  | 'FINISHED'
  | 'ERROR';

export interface ExecutionTelemetry {
  execution_time_ms?: number | null;
  peak_memory_bytes?: number | null;
  exit_code?: number | null;
  status: ExecutionStatus;
}
