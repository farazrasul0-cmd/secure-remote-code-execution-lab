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

export interface TestCase {
  id: string;
  is_hidden: boolean;
  weight: number;
  order: number;
  explanation?: string | null;
  input_data?: string | null;
  expected_output?: string | null;
}

export interface Problem {
  id: string;
  title: string;
  slug: string;
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  time_limit_ms: number;
  memory_limit_mb: number;
  is_published: boolean;
  created_at: string;
  test_case_count?: number;
  sample_cases_count?: number;
}

export interface ProblemDetail extends Problem {
  sample_test_cases: TestCase[];
  total_test_cases: number;
  total_points: number;
}

export interface TestCaseResult {
  test_case_id: string;
  order: number;
  status: string;
  passed: boolean;
  duration_ms: number;
  memory_bytes: number;
  is_hidden: boolean;
  weight: number;
  earned_points: number;
  input_data?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  diff?: string | null;
  error_message?: string | null;
}

export interface GradingScorecard {
  submission_id: string;
  problem_id: string;
  overall_status: string;
  total_score: number;
  max_score: number;
  percentage: number;
  passed_count: number;
  total_test_cases: number;
  execution_time_ms: number;
  peak_memory_bytes: number;
  compile_error?: string | null;
  test_case_results: TestCaseResult[];
}

