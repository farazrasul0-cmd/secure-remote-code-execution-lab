import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { Terminal as TerminalIcon, Trash2, Copy, Check, Radio } from 'lucide-react';
import { StreamChunk, WebSocketState } from '../types';

interface TerminalViewProps {
  chunks: StreamChunk[];
  streamState: WebSocketState;
  onClear?: () => void;
}

export const TerminalView: React.FC<TerminalViewProps> = ({
  chunks,
  streamState,
  onClear,
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
    fitAddon.fit();

    xtermInstance.current = term;
    fitAddonRef.current = fitAddon;

    // Welcome banner
    term.writeln('\x1b[1;36m+----------------------------------------------------------+\x1b[0m');
    term.writeln('\x1b[1;36m¦\x1b[0m \x1b[1;37mSecure Remote Code Execution Lab - Virtual Terminal\x1b[0m      \x1b[1;36m¦\x1b[0m');
    term.writeln('\x1b[1;36m¦\x1b[0m \x1b[90mLinux Micro-Sandbox (cgroups v2, Seccomp, tmpfs)\x1b[0m          \x1b[1;36m¦\x1b[0m');
    term.writeln('\x1b[1;36m+----------------------------------------------------------+\x1b[0m');
    term.writeln('\x1b[90mReady for submission execution. Press "Run Code" to execute.\x1b[0m\r\n');

    // ResizeObserver for dynamic fit
    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
      } catch {
        // ignore resize race during DOM detachment
      }
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
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

    for (let i = lastRenderedIndex.current; i < chunks.length; i++) {
      const chunk = chunks[i];
      if (chunk.data) {
        if (chunk.type === 'stderr') {
          // Format stderr in red ANSI
          term.write(`\x1b[31m${chunk.data}\x1b[0m`);
        } else if (chunk.type === 'system') {
          // Format system events in cyan/italic
          term.write(`\x1b[36m${chunk.data}\x1b[0m`);
        } else {
          // Standard stdout
          term.write(chunk.data);
        }
      }
    }
    lastRenderedIndex.current = chunks.length;
  }, [chunks]);

  const handleClear = () => {
    const term = xtermInstance.current;
    if (term) {
      term.clear();
      lastRenderedIndex.current = 0;
    }
    onClear?.();
  };

  const handleCopy = () => {
    const term = xtermInstance.current;
    if (!term) return;

    // Extract visible buffer lines
    const buffer = term.buffer.active;
    const lines: string[] = [];
    for (let i = 0; i < buffer.length; i++) {
      const line = buffer.getLine(i);
      if (line) {
        lines.push(line.translateToString(true));
      }
    }
    const fullText = lines.join('\n').trim();
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStateBadge = () => {
    switch (streamState) {
      case 'STREAMING':
        return (
          <span className="flex items-center space-x-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono">
            <Radio className="w-3 h-3 animate-pulse" />
            <span>LIVE STREAM</span>
          </span>
        );
      case 'CONNECTING':
        return (
          <span className="flex items-center space-x-1 text-xs text-sky-400 bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 rounded-full font-mono">
            <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span>
            <span>CONNECTING</span>
          </span>
        );
      case 'FINISHED':
        return (
          <span className="text-xs text-slate-400 bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full font-mono">
            STREAM CLOSED
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
          <span className="text-xs text-slate-300 font-semibold">Virtual Terminal (VT100)</span>
          {getStateBadge()}
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 text-slate-400 hover:text-slate-200 px-2.5 py-1 rounded-md text-xs hover:bg-slate-700/60 transition-colors"
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
            className="flex items-center space-x-1 text-slate-400 hover:text-rose-400 px-2.5 py-1 rounded-md text-xs hover:bg-slate-700/60 transition-colors"
            title="Clear terminal buffer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* xterm.js DOM Mount Point */}
      <div className="flex-1 p-2 bg-[#0b0f19] overflow-hidden min-h-[250px]" ref={terminalRef} />
    </div>
  );
};
