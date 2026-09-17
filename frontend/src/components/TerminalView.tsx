import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { Terminal as TerminalIcon, Trash2, Copy, Check, Radio, Ban } from 'lucide-react';
import { StreamChunk, WebSocketState } from '../types';

interface TerminalViewProps {
  chunks: StreamChunk[];
  streamState: WebSocketState;
  onClear?: () => void;
  onData?: (data: string) => void;
  onResize?: (cols: number, rows: number) => void;
  onSignal?: (signal: string) => void;
}

export const TerminalView: React.FC<TerminalViewProps> = ({
  chunks,
  streamState,
  onClear,
  onData,
  onResize,
  onSignal,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermInstance = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const lastRenderedIndex = useRef<number>(0);
  const [copied, setCopied] = useState<boolean>(false);

  // Initialize xterm.js instance
  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 12.5,
      lineHeight: 1.35,
      fontFamily: '"Fira Code", Consolas, Monaco, "Courier New", monospace',
      theme: {
        background: '#0b0f19',
        foreground: '#f1f5f9',
        cursor: '#38bdf8',
        cursorAccent: '#0b0f19',
        selectionBackground: '#334155',
        black: '#0f172a',
        red: '#f43f5e',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#d946ef',
        cyan: '#06b6d4',
        white: '#f8fafc',
        brightBlack: '#475569',
        brightRed: '#fb7185',
        brightGreen: '#34d399',
        brightYellow: '#fbbf24',
        brightBlue: '#60a5fa',
        brightMagenta: '#e879f9',
        brightCyan: '#38bdf8',
        brightWhite: '#ffffff',
      },
      convertEol: true,
      scrollback: 5000,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    xtermInstance.current = term;
    fitAddonRef.current = fitAddon;

    // Listen to user keyboard inputs for interactive PTY streaming
    term.onData((data) => {
      onData?.(data);
    });

    // Listen to terminal geometry change for SIGWINCH synchronization
    term.onResize(({ cols, rows }) => {
      onResize?.(cols, rows);
    });

    // Welcome banner
    term.writeln('\x1b[1;36m+----------------------------------------------------------+\x1b[0m');
    term.writeln('\x1b[1;36m|\x1b[0m \x1b[1;37mSecure Remote Code Execution Lab - Interactive PTY\x1b[0m       \x1b[1;36m|\x1b[0m');
    term.writeln('\x1b[1;36m|\x1b[0m \x1b[90mLinux Micro-Sandbox (cgroups v2, Seccomp, PTY Full-Duplex)\x1b[0m \x1b[1;36m|\x1b[0m');
    term.writeln('\x1b[1;36m+----------------------------------------------------------+\x1b[0m');
    term.writeln('\x1b[90mFull-duplex interactive terminal ready. Type inputs or press Run.\x1b[0m\r\n');

    // Safe deferred initial fit after DOM layout calculation
    const animId = requestAnimationFrame(() => {
      try {
        if (terminalRef.current && terminalRef.current.clientWidth > 0 && terminalRef.current.clientHeight > 0) {
          fitAddon.fit();
          if (onResize) onResize(term.cols, term.rows);
        }
      } catch {}
    });

    // ResizeObserver for dynamic fit
    const resizeObserver = new ResizeObserver(() => {
      try {
        if (terminalRef.current && terminalRef.current.clientWidth > 0 && terminalRef.current.clientHeight > 0) {
          fitAddon.fit();
          if (onResize && term) {
            onResize(term.cols, term.rows);
          }
        }
      } catch {
        // ignore resize race during DOM detachment
      }
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      term.dispose();
      xtermInstance.current = null;
      fitAddonRef.current = null;
    };
  }, []);

  // Write new chunks incrementally as they arrive
  useEffect(() => {
    const term = xtermInstance.current;
    if (!term) return;

    if (chunks.length === 0) {
      lastRenderedIndex.current = 0;
      return;
    }

    // Only render new chunks arrived since last render
    for (let i = lastRenderedIndex.current; i < chunks.length; i++) {
      const chunk = chunks[i];
      if (!chunk.data) continue;

      if (chunk.type === 'stderr') {
        term.write(`\x1b[31m${chunk.data}\x1b[0m`);
      } else if (chunk.type === 'system') {
        term.write(`\x1b[90m${chunk.data}\x1b[0m`);
      } else {
        term.write(chunk.data);
      }
    }

    lastRenderedIndex.current = chunks.length;
  }, [chunks]);

  const handleClear = () => {
    xtermInstance.current?.clear();
    lastRenderedIndex.current = 0;
    onClear?.();
  };

  const handleCopy = async () => {
    const term = xtermInstance.current;
    if (!term) return;

    // Buffer dump via selection or active buffer
    term.selectAll();
    const selection = term.getSelection();
    term.clearSelection();

    if (selection) {
      await navigator.clipboard.writeText(selection);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleInterrupt = () => {
    // Send SIGINT / Ctrl+C
    onSignal?.('SIGINT');
    onData?.('\x03');
    xtermInstance.current?.write('^C\r\n');
  };

  const getStateBadge = () => {
    switch (streamState) {
      case 'STREAMING':
        return (
          <span className="flex items-center space-x-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono">
            <Radio className="w-3 h-3 animate-pulse" />
            <span>INTERACTIVE</span>
          </span>
        );
      case 'CONNECTING':
        return (
          <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full font-mono">
            CONNECTING...
          </span>
        );
      case 'FINISHED':
        return (
          <span className="text-xs text-sky-400 bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 rounded-full font-mono">
            COMPLETED
          </span>
        );
      case 'ERROR':
        return (
          <span className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded-full font-mono">
            CONNECTION ERROR
          </span>
        );
      default:
        return (
          <span className="text-xs text-slate-500 bg-slate-800/60 border border-slate-700/60 px-2 py-0.5 rounded-full font-mono">
            IDLE
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      {/* Terminal Toolbar */}
      <div className="bg-slate-800/80 border-b border-slate-700/80 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <TerminalIcon className="w-4 h-4 text-emerald-400" />
          <span className="text-xs text-slate-300 font-semibold">Interactive Terminal (PTY / xterm)</span>
          {getStateBadge()}
        </div>

        <div className="flex items-center space-x-1.5">
          {/* Ctrl+C / SIGINT Interrupt Button */}
          <button
            onClick={handleInterrupt}
            disabled={streamState !== 'STREAMING'}
            className="flex items-center space-x-1 text-slate-400 hover:text-amber-400 disabled:opacity-40 px-2 py-1 rounded-md text-xs hover:bg-slate-700/60 transition-colors"
            title="Send SIGINT (Ctrl+C) interrupt signal"
          >
            <Ban className="w-3.5 h-3.5 text-amber-400" />
            <span>Ctrl+C</span>
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 text-slate-400 hover:text-slate-200 px-2 py-1 rounded-md text-xs hover:bg-slate-700/60 transition-colors"
            title="Copy terminal buffer to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          <button
            onClick={handleClear}
            className="flex items-center space-x-1 text-slate-400 hover:text-rose-400 px-2 py-1 rounded-md text-xs hover:bg-slate-700/60 transition-colors"
            title="Clear terminal buffer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* xterm.js DOM Mount Point */}
      <div
        className="flex-1 p-2 bg-[#0b0f19] overflow-hidden min-h-[250px] cursor-text"
        ref={terminalRef}
        onClick={() => xtermInstance.current?.focus()}
      />
    </div>
  );
};
