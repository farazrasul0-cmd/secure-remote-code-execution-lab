import React, { useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { Play, RotateCcw, FileCode, SlidersHorizontal, Loader2 } from 'lucide-react';

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  onRun: () => void;
  isRunning: boolean;
  onToggleStdin: () => void;
  isStdinOpen: boolean;
  hasStdinContent: boolean;
}

export const DEFAULT_PYTHON_CODE = `# Secure Real-Time Remote Code Execution Lab
# Python 3.11 Runtime (Isolated Micro-Sandbox: cgroups v2, Seccomp, Read-Only rootfs, tmpfs)

import sys
import time

def main():
    print("=== Execution Environment Initialized ===")
    print(f"Python: {sys.version.split()[0]} on Linux Sandbox")
    
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        print(f"Standard Input (stdin): {stdin_data}")
    else:
        print("Standard Input: (None provided)")

    print("\\nExecuting computation pipeline...")
    for step in range(1, 6):
        print(f"-> [Worker Thread] Step {step}/5 processing telemetry...")
        time.sleep(0.15)

    print("\\n[SUCCESS] Execution pipeline completed cleanly.")

if __name__ == "__main__":
    main()
`;

export const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  onChange,
  onRun,
  isRunning,
  onToggleStdin,
  isStdinOpen,
  hasStdinContent,
}) => {
  const editorRef = useRef<any>(null);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Register Ctrl+Enter or Cmd+Enter to execute code immediately
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (!isRunning) {
        onRun();
      }
    });
  };

  const handleReset = () => {
    onChange(DEFAULT_PYTHON_CODE);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      {/* Editor Header Toolbar */}
      <div className="bg-slate-800/80 border-b border-slate-700/80 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-xs text-slate-300 font-semibold">
            <FileCode className="w-4 h-4 text-sky-400" />
            <span>main.py</span>
          </div>
          <span className="text-[11px] bg-slate-700/80 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-600/50">
            Python 3.11
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Stdin Toggle */}
          <button
            onClick={onToggleStdin}
            className={`flex items-center space-x-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-all ${
              isStdinOpen
                ? 'bg-slate-700 border-sky-500/50 text-sky-300'
                : hasStdinContent
                ? 'bg-slate-800 border-amber-500/50 text-amber-300'
                : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="Configure custom standard input (stdin)"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>stdin</span>
            {hasStdinContent && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            )}
          </button>

          {/* Reset Code */}
          <button
            onClick={handleReset}
            disabled={isRunning}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-700/60 disabled:opacity-40 transition-colors"
            title="Reset code template"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Run Code Button */}
          <button
            onClick={onRun}
            disabled={isRunning}
            className={`flex items-center space-x-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold text-white transition-all shadow-md active:scale-95 ${
              isRunning
                ? 'bg-slate-700 cursor-not-allowed opacity-80'
                : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30'
            }`}
          >
            {isRunning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Code</span>
                <span className="hidden sm:inline text-[10px] opacity-70 ml-1 font-mono font-normal">
                  (Ctrl+?)
                </span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Monaco Editor Container */}
      <div className="flex-1 min-h-[300px] relative">
        <Editor
          height="100%"
          language="python"
          theme="vs-dark"
          value={code}
          onChange={(val) => onChange(val || '')}
          onMount={handleEditorDidMount}
          options={{
            readOnly: isRunning,
            minimap: { enabled: false },
            fontSize: 13,
            lineHeight: 20,
            fontFamily: '"Fira Code", Consolas, Monaco, monospace',
            fontLigatures: true,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            insertSpaces: true,
            wordWrap: 'on',
            renderLineHighlight: 'all',
            cursorBlinking: 'smooth',
            scrollbar: {
              verticalScrollbarSize: 8,
              horizontalScrollbarSize: 8,
            },
          }}
        />
      </div>
    </div>
  );
};
