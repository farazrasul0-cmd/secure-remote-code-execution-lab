import React from 'react';
import {
  Award,
  CheckCircle2,
  Clock,
  Cpu,
  Lock,
  Unlock,
  XCircle,
  AlertTriangle,
  X,
} from 'lucide-react';
import { GradingScorecard as IGradingScorecard } from '../types';

interface GradingScorecardProps {
  scorecard: IGradingScorecard | null;
  isOpen: boolean;
  onClose: () => void;
  isSubmitting?: boolean;
}

export const GradingScorecard: React.FC<GradingScorecardProps> = ({
  scorecard,
  isOpen,
  onClose,
  isSubmitting = false,
}) => {
  if (!isOpen) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-600/50">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Accepted
          </span>
        );
      case 'PARTIAL':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-600/50">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Partial Credit
          </span>
        );
      case 'TIME_LIMIT_EXCEEDED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-950/80 text-orange-300 border border-orange-600/50">
            <Clock className="w-3.5 h-3.5 mr-1" /> Time Limit Exceeded
          </span>
        );
      case 'COMPILE_ERROR':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-950/80 text-purple-300 border border-purple-600/50">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Compile Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-300 border border-rose-600/50">
            <XCircle className="w-3.5 h-3.5 mr-1" /> {status}
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="bg-slate-800/90 px-6 py-4 border-b border-slate-700/80 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-sky-950/60 border border-sky-700/40 text-sky-400">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
                <span>Autograding Evaluation Scorecard</span>
              </h2>
              <p className="text-xs text-slate-400">
                Oracle-based verification and deterministic test harness results
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-700/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isSubmitting ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="w-10 h-10 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm font-medium text-slate-300">
                Evaluating test vectors in isolated sandbox...
              </p>
            </div>
          ) : scorecard ? (
            <>
              {/* Summary Stats Card */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
                    Score
                  </span>
                  <div className="mt-1 flex items-baseline space-x-1.5">
                    <span className="text-2xl font-extrabold text-white">
                      {scorecard.total_score}
                    </span>
                    <span className="text-xs text-slate-400">
                      / {scorecard.max_score} pts
                    </span>
                    <span className="text-xs font-semibold text-sky-400 ml-1">
                      ({scorecard.percentage}%)
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
                    Verdict
                  </span>
                  <div className="mt-1.5">{getStatusBadge(scorecard.overall_status)}</div>
                </div>

                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
                    Passed Tests
                  </span>
                  <div className="mt-1 flex items-baseline space-x-1">
                    <span className="text-xl font-bold text-slate-200">
                      {scorecard.passed_count}
                    </span>
                    <span className="text-xs text-slate-400">
                      / {scorecard.total_test_cases} passed
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
                    Execution
                  </span>
                  <div className="mt-1 text-xs text-slate-300 space-y-0.5">
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{scorecard.execution_time_ms} ms</span>
                    </div>
                    {scorecard.peak_memory_bytes > 0 && (
                      <div className="flex items-center space-x-1">
                        <Cpu className="w-3 h-3 text-slate-400" />
                        <span>{(scorecard.peak_memory_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Compiler Error Notice if applicable */}
              {scorecard.compile_error && (
                <div className="bg-purple-950/40 border border-purple-800/60 rounded-xl p-4">
                  <div className="flex items-center space-x-2 text-purple-300 font-semibold text-xs mb-2">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Compiler Diagnostics (Phase 1 Build Error)</span>
                  </div>
                  <pre className="font-mono text-xs text-purple-200 bg-purple-950/80 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap">
                    {scorecard.compile_error}
                  </pre>
                </div>
              )}

              {/* Test Cases List */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Test Case Results & Oracle Comparison
                </h3>

                <div className="space-y-2.5">
                  {scorecard.test_case_results.map((tc, idx) => (
                    <div
                      key={tc.test_case_id || idx}
                      className={`border rounded-xl p-3.5 transition-all ${
                        tc.passed
                          ? 'bg-slate-950/40 border-emerald-900/40'
                          : 'bg-slate-950/60 border-rose-900/40'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {tc.passed ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <XCircle className="w-4 h-4 text-rose-400" />
                          )}
                          <span className="text-xs font-bold text-slate-200">
                            Test Case #{tc.order || idx + 1}
                          </span>
                          {tc.is_hidden ? (
                            <span className="inline-flex items-center text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono border border-slate-700">
                              <Lock className="w-2.5 h-2.5 mr-1" /> Hidden Test
                            </span>
                          ) : (
                            <span className="inline-flex items-center text-[10px] bg-sky-950/60 text-sky-300 px-2 py-0.5 rounded font-mono border border-sky-800/50">
                              <Unlock className="w-2.5 h-2.5 mr-1" /> Sample Case
                            </span>
                          )}
                        </div>

                        <div className="flex items-center space-x-3 text-xs">
                          <span className="text-slate-400">
                            {tc.duration_ms} ms
                          </span>
                          <span
                            className={`font-semibold ${
                              tc.passed ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {tc.earned_points} / {tc.weight} pts
                          </span>
                        </div>
                      </div>

                      {/* Visible Test Case Details */}
                      {!tc.is_hidden ? (
                        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                          <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase block font-sans mb-1">
                              Input
                            </span>
                            <pre className="text-slate-300 whitespace-pre-wrap">
                              {tc.input_data}
                            </pre>
                          </div>
                          <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase block font-sans mb-1">
                              Expected vs Actual
                            </span>
                            <div className="space-y-1">
                              <div className="text-emerald-300">
                                Exp: {tc.expected_output}
                              </div>
                              <div
                                className={
                                  tc.passed ? 'text-emerald-300' : 'text-rose-300'
                                }
                              >
                                Act: {tc.actual_output || '(no output)'}
                              </div>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="mt-2 text-[11px] text-slate-500 italic flex items-center space-x-1.5 bg-slate-900/40 px-3 py-1.5 rounded-lg border border-slate-800/60">
                          <Lock className="w-3 h-3 text-slate-400" />
                          <span>
                            Oracle test vector hidden to uphold information hiding and prevent hardcoding.
                          </span>
                        </div>
                      )}

                      {/* Diff view on failure if available */}
                      {tc.diff && (
                        <div className="mt-2 text-xs font-mono bg-rose-950/30 border border-rose-900/40 p-2.5 rounded-lg text-rose-200 overflow-x-auto whitespace-pre-wrap">
                          {tc.diff}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-center text-slate-400 text-sm py-8">
              No scorecard available.
            </p>
          )}
        </div>

        {/* Modal Footer */}
        <div className="bg-slate-800/80 px-6 py-3 border-t border-slate-700/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
