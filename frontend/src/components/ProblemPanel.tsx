import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Clock,
  Cpu,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Problem, ProblemDetail } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface ProblemPanelProps {
  onSelectProblem?: (problem: ProblemDetail) => void;
  onSubmitForGrading: (problemSlug: string) => void;
  isGrading: boolean;
}

export const ProblemPanel: React.FC<ProblemPanelProps> = ({
  onSelectProblem,
  onSubmitForGrading,
  isGrading,
}) => {
  const { isAuthenticated } = useAuth();
  const [problems, setProblems] = useState<Problem[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string>('');
  const [problemDetail, setProblemDetail] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isAuthenticated) {
      loadProblems();
    } else {
      setProblems([]);
      setProblemDetail(null);
      setLoading(false);
    }
  }, [isAuthenticated]);

  const loadProblems = async () => {
    try {
      setLoading(true);
      const list = await api.listProblems();
      setProblems(list);
      if (list.length > 0) {
        selectProblem(list[0].slug);
      }
    } catch (err) {
      console.error('Failed to load problems:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectProblem = async (slug: string) => {
    setSelectedSlug(slug);
    try {
      const detail = await api.getProblem(slug);
      setProblemDetail(detail);
      if (onSelectProblem) {
        onSelectProblem(detail);
      }
    } catch (err) {
      console.error('Failed to fetch problem detail:', err);
    }
  };

  const getDifficultyBadge = (diff: string) => {
    switch (diff) {
      case 'EASY':
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-700/50">
            EASY
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-700/50">
            MEDIUM
          </span>
        );
      case 'HARD':
        return (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-700/50">
            HARD
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 shadow-md">
      {/* Problem Selector & Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-bold text-slate-200">
            Problem Catalog & Autograding
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={selectedSlug}
            onChange={(e) => selectProblem(e.target.value)}
            disabled={loading || isGrading}
            className="bg-slate-800 text-slate-200 text-xs font-medium px-2.5 py-1 rounded-lg border border-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
          >
            {problems.map((p) => (
              <option key={p.id} value={p.slug}>
                {p.title} ({p.difficulty})
              </option>
            ))}
          </select>

          <button
            onClick={() => problemDetail && onSubmitForGrading(problemDetail.slug)}
            disabled={isGrading || !problemDetail}
            className="flex items-center space-x-1.5 px-3 py-1 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-lg shadow-md active:scale-95 disabled:opacity-50 transition-all"
          >
            {isGrading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Grading...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-sky-200" />
                <span>Submit for Grading</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Problem Details */}
      {problemDetail ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">
                {problemDetail.title}
              </h3>
              {getDifficultyBadge(problemDetail.difficulty)}
            </div>
            <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-mono">
              <span className="flex items-center space-x-1">
                <Clock className="w-3 h-3 text-slate-500" />
                <span>{problemDetail.time_limit_ms}ms</span>
              </span>
              <span className="flex items-center space-x-1">
                <Cpu className="w-3 h-3 text-slate-500" />
                <span>{problemDetail.memory_limit_mb}MB</span>
              </span>
              <span>{problemDetail.total_test_cases} Test Vectors</span>
            </div>
          </div>

          {/* Description */}
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-wrap max-h-36 overflow-y-auto">
            {problemDetail.description}
          </div>

          {/* Sample Cases */}
          {problemDetail.sample_test_cases.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Sample Test Cases
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                {problemDetail.sample_test_cases.slice(0, 2).map((tc, idx) => (
                  <div
                    key={tc.id || idx}
                    className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800 space-y-1"
                  >
                    <div className="text-[10px] text-sky-400 font-semibold flex items-center justify-between">
                      <span>Sample Case #{tc.order || idx + 1}</span>
                      <span className="text-slate-500 font-normal">
                        Weight: {tc.weight} pts
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">Input:</span>
                      <pre className="text-slate-300 text-[11px] whitespace-pre-wrap">
                        {tc.input_data}
                      </pre>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">Expected:</span>
                      <pre className="text-emerald-400 text-[11px] whitespace-pre-wrap">
                        {tc.expected_output}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="py-4 text-center text-xs text-slate-500">
          Loading problem specification...
        </div>
      )}
    </div>
  );
};
