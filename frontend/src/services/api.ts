import { AuthToken, Submission, SubmissionCreate, SubmissionListResponse, User } from '../types';

const TOKEN_KEY = 'rce_auth_token';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem(TOKEN_KEY);
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem(TOKEN_KEY);
    }
    return this.token;
  }

  private getHeaders(contentType: string = 'application/json'): HeadersInit {
    const headers: Record<string, string> = {};
    if (contentType) {
      headers['Content-Type'] = contentType;
    }
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const isFormData = options.body instanceof URLSearchParams || options.body instanceof FormData;
    const defaultHeaders = isFormData
      ? this.getHeaders('')
      : this.getHeaders('application/json');

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
    };

    const response = await fetch(endpoint, config);
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // use default error message
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Authentication API
  async login(username: string, password: string): Promise<AuthToken> {
    const body = new URLSearchParams();
    body.append('username', username);
    body.append('password', password);

    const token = await this.request<AuthToken>('/api/v1/auth/login', {
      method: 'POST',
      body,
    });
    this.setToken(token.access_token);
    return token;
  }

  async register(data: { username: string; email: string; password: string }): Promise<User> {
    return this.request<User>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/api/v1/auth/me');
  }

  logout() {
    this.setToken(null);
  }

  // Submissions API
  async createSubmission(payload: SubmissionCreate): Promise<Submission> {
    return this.request<Submission>('/api/v1/submissions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async listSubmissions(page: number = 1, size: number = 20): Promise<SubmissionListResponse> {
    return this.request<SubmissionListResponse>(`/api/v1/submissions?page=${page}&size=${size}`);
  }

  async getSubmission(id: string): Promise<Submission> {
    return this.request<Submission>(`/api/v1/submissions/${id}`);
  }

  // Health API
  async checkHealth(): Promise<{ status: string; checks: Record<string, unknown> }> {
    return this.request<{ status: string; checks: Record<string, unknown> }>('/api/v1/health');
  }

  // Problems & Autograding API
  async listProblems(difficulty?: string): Promise<import('../types').Problem[]> {
    const query = difficulty ? `?difficulty=${difficulty}` : '';
    return this.request<import('../types').Problem[]>(`/api/v1/problems${query}`);
  }

  async getProblem(identifier: string): Promise<import('../types').ProblemDetail> {
    return this.request<import('../types').ProblemDetail>(`/api/v1/problems/${identifier}`);
  }

  async submitProblemForGrading(
    identifier: string,
    payload: { language: string; source_code: string }
  ): Promise<import('../types').GradingScorecard> {
    return this.request<import('../types').GradingScorecard>(`/api/v1/problems/${identifier}/submit`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getGradingScorecard(submissionId: string): Promise<import('../types').GradingScorecard> {
    return this.request<import('../types').GradingScorecard>(`/api/v1/problems/submissions/${submissionId}/grading`);
  }
}

export const api = new ApiClient();
