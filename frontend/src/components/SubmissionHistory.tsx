import React, { useEffect, useState } from 'react';
import { History, RefreshCw, ChevronUp, ChevronDown, Code, Clock, HardDrive } from 'lucide-react';
import { api } from '../services/api';
import { Submission } from '../types';
import { useAuth } from '../context/AuthContext';

interface SubmissionHistoryProps {
  onSelectSubmission: (submission: Submission) => void;
  refreshTrigger?: number;
}

export const SubmissionHistory: React.FC<SubmissionHistoryProps> = ({
  onSelectSubmission,
  refreshTrigger,
}) => {
  const { isAuthenticated } = useAuth();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchHistory = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const response = await api.listSubmissions(1, 15);
      setSubmissions(response.items);
    } catch (err) {
      console.error('Failed to fetch submission history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchHistory();
    } else {
      setSubmissions([]);
    }
  }, [isAuthenticated, refreshTrigger]);

  const formatMemory = (bytes?: number | null) => {
    if (!bytes) return '—';
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'TIME_LIMIT_EXCEEDED':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'MEMORY_LIMIT_EXCEEDED':
      case 'RUNTIME_ERROR':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg mt-4 transition-all">
      {/* Drawer Header */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-3 bg-slate-800/80 hover:bg-slate-800 cursor-pointer flex items-center justify-between transition-colors"
      >
        <div className="flex items-center space-x-2.5">
          <History className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Execution History & Audit Log
          </h3>
          {isAuthenticated && (
            <span className="text-[11px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full font-mono">
              {submissions.length} records
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {isAuthenticated && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                fetchHistory();
              }}
              disabled={isLoading}
              className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-700 transition-colors"
              title="Refresh history"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
            </button>
          )}
          <button className="text-slate-400 hover:text-slate-200 p-1">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Drawer Body */}
      {isOpen && (
        <div className="p-4 bg-slate-950/70 border-t border-slate-800/80 max-h-64 overflow-y-auto">
          {!isAuthenticated ? (
            <div className="text-center py-6 text-slate-400 text-xs">
              <p>Sign in with an account to persist and view your historical code executions.</p>
            </div>
          ) : submissions.length === 0 ? (
            <div className="text-center py-6 text-slate-500 text-xs">
              <p>No executions logged yet. Click "Run Code" above to dispatch your first submission.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {submissions.map((sub) => (
                <div
                  key={sub.id}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-3 rounded-lg flex flex-wrap items-center justify-between gap-3 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span
                      className={`text-[11px] font-mono px-2 py-0.5 rounded border font-semibold ${getStatusColor(
                        sub.status
                      )}`}
                    >
                      {sub.status}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {sub.id.slice(0, 8)}...
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(sub.created_at).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="flex items-center space-x-4 text-xs font-mono text-slate-400">
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-sky-400" />
                      <span>{sub.execution_time_ms != null ? `${sub.execution_time_ms}ms` : '—'}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <HardDrive className="w-3 h-3 text-purple-400" />
                      <span>{formatMemory(sub.peak_memory_bytes)}</span>
                    </div>
                    <button
                      onClick={() => onSelectSubmission(sub)}
                      className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-sky-300 hover:text-sky-200 px-2.5 py-1 rounded text-xs transition-colors border border-slate-700"
                    >
                      <Code className="w-3.5 h-3.5" />
                      <span>Load in Editor</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
