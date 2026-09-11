import React from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Flame,
  Shield,
  FileWarning,
  Cpu,
  HardDrive,
  Hash,
  Lock,
} from 'lucide-react';
import { ExecutionStatus, ExecutionTelemetry } from '../types';

interface TelemetryPanelProps {
  telemetry: ExecutionTelemetry | null;
  status: ExecutionStatus | null;
  isRunning: boolean;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({
  telemetry,
  status,
  isRunning,
}) => {
  const currentStatus = isRunning ? 'RUNNING' : telemetry?.status || status || 'PENDING';

  const formatMemory = (bytes?: number | null) => {
    if (!bytes || bytes <= 0) return '—';
    const mb = bytes / (1024 * 1024);
    if (mb < 1) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${mb.toFixed(2)} MB`;
  };

  const getStatusBadge = () => {
    switch (currentStatus) {
      case 'RUNNING':
        return (
          <span className="flex items-center space-x-1.5 bg-sky-500/10 text-sky-400 border border-sky-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span>
            <span>RUNNING IN SANDBOX</span>
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="flex items-center space-x-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <CheckCircle2 className="w-4 h-4" />
            <span>COMPLETED</span>
          </span>
        );
      case 'TIME_LIMIT_EXCEEDED':
        return (
          <span className="flex items-center space-x-1.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <Clock className="w-4 h-4" />
            <span>TIME LIMIT EXCEEDED</span>
          </span>
        );
      case 'MEMORY_LIMIT_EXCEEDED':
        return (
          <span className="flex items-center space-x-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <Flame className="w-4 h-4" />
            <span>MEMORY LIMIT EXCEEDED</span>
          </span>
        );
      case 'OUTPUT_LIMIT_EXCEEDED':
        return (
          <span className="flex items-center space-x-1.5 bg-orange-500/10 text-orange-400 border border-orange-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <FileWarning className="w-4 h-4" />
            <span>OUTPUT LIMIT EXCEEDED</span>
          </span>
        );
      case 'RUNTIME_ERROR':
        return (
          <span className="flex items-center space-x-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <AlertTriangle className="w-4 h-4" />
            <span>RUNTIME ERROR</span>
          </span>
        );
      case 'RESOURCE_LIMIT_EXCEEDED':
        return (
          <span className="flex items-center space-x-1.5 bg-purple-500/10 text-purple-400 border border-purple-500/30 px-3 py-1 rounded-full text-xs font-semibold">
            <Shield className="w-4 h-4" />
            <span>RESOURCE LIMIT EXCEEDED</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1.5 bg-slate-800 text-slate-400 border border-slate-700 px-3 py-1 rounded-full text-xs font-semibold">
            <Clock className="w-4 h-4" />
            <span>AWAITING EXECUTION</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between">
      {/* Header & Status */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-sky-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Execution Telemetry & Sandbox Limits
          </h2>
        </div>
        {getStatusBadge()}
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
        {/* Wall Clock Time */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs mb-1">
            <Clock className="w-3.5 h-3.5 text-sky-400" />
            <span>Wall Clock</span>
          </div>
          <div className="text-base font-bold font-mono text-slate-100">
            {telemetry?.execution_time_ms != null ? `${telemetry.execution_time_ms} ms` : '—'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">Cap: 5000 ms</div>
        </div>

        {/* Peak Memory */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs mb-1">
            <HardDrive className="w-3.5 h-3.5 text-purple-400" />
            <span>Peak Memory</span>
          </div>
          <div className="text-base font-bold font-mono text-slate-100">
            {formatMemory(telemetry?.peak_memory_bytes)}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">Cap: 128 MB</div>
        </div>

        {/* Exit Code */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs mb-1">
            <Hash className="w-3.5 h-3.5 text-emerald-400" />
            <span>Exit Code</span>
          </div>
          <div
            className={`text-base font-bold font-mono ${
              telemetry?.exit_code === 0
                ? 'text-emerald-400'
                : telemetry?.exit_code != null
                ? 'text-rose-400'
                : 'text-slate-100'
            }`}
          >
            {telemetry?.exit_code != null ? telemetry.exit_code : '—'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {telemetry?.exit_code === 0
              ? 'Success'
              : telemetry?.exit_code != null
              ? 'Abnormal Exit'
              : 'N/A'}
          </div>
        </div>

        {/* Output Limit */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs mb-1">
            <FileWarning className="w-3.5 h-3.5 text-amber-400" />
            <span>Stream Cap</span>
          </div>
          <div className="text-base font-bold font-mono text-slate-100">1.0 MB</div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">Truncation Guard</div>
        </div>
      </div>

      {/* Linux Kernel Containment Architecture Specs */}
      <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 font-mono">
        <div className="flex items-center space-x-1.5">
          <Lock className="w-3 h-3 text-sky-400" />
          <span>cgroups v2: cpu.max=50000/100000 | memory.max=128M | pids.max=64</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">--net=none</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">read-only rootfs</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">16MB tmpfs</span>
        </div>
      </div>
    </div>
  );
};
