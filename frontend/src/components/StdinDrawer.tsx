import React from 'react';
import { X, Trash2, SlidersHorizontal } from 'lucide-react';

interface StdinDrawerProps {
  isOpen: boolean;
  value: string;
  onChange: (val: string) => void;
  onClose: () => void;
  disabled?: boolean;
}

export const StdinDrawer: React.FC<StdinDrawerProps> = ({
  isOpen,
  value,
  onChange,
  onClose,
  disabled,
}) => {
  if (!isOpen) return null;

  return (
    <div className="bg-slate-850 border border-slate-750 rounded-xl p-3.5 mt-2 shadow-md bg-slate-900/90 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <SlidersHorizontal className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-semibold text-slate-200">
            Standard Input (sys.stdin stream)
          </h3>
          <span className="text-[10px] text-slate-400 font-mono">
            Piped into container at launch
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onChange('')}
            disabled={disabled || !value}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 text-xs flex items-center space-x-1 disabled:opacity-40"
            title="Clear stdin content"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Enter data to pipe to sys.stdin (e.g. numbers, lines of text, JSON payload)..."
        rows={3}
        className="w-full bg-slate-950/80 border border-slate-700/80 rounded-lg p-2.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50 resize-y"
      />
    </div>
  );
};
