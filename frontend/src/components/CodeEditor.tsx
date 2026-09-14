import React, { useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { Play, RotateCcw, FileCode, SlidersHorizontal, Loader2, ChevronDown } from 'lucide-react';
import { SupportedLanguage } from '../types';

export const BOILERPLATES: Record<
  SupportedLanguage,
  {
    name: string;
    filename: string;
    monacoLang: string;
    tag: string;
    code: string;
  }
> = {
  python: {
    name: 'Python 3.12',
    filename: 'main.py',
    monacoLang: 'python',
    tag: 'Interpreted',
    code: `# Secure Real-Time Remote Code Execution Lab
# Language: Python 3.12 (Isolated Sandbox: cgroups v2, Seccomp, no-net)

import sys
import time

def main():
    print("=== Execution Environment Initialized ===")
    print(f"Python: {sys.version.split()[0]} on Linux Sandbox")
    
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        print(f"Standard Input: {stdin_data}")
        
    print("\\nExecuting algorithmic computation...")
    for step in range(1, 6):
        print(f"-> [Worker Thread] Step {step}/5 processing telemetry...")
        time.sleep(0.1)

    print("\\n[SUCCESS] Computation pipeline completed.")

if __name__ == "__main__":
    main()
`,
  },
  c: {
    name: 'C17 (GCC 14)',
    filename: 'main.c',
    monacoLang: 'c',
    tag: 'AOT Compiled',
    code: `// Secure Real-Time Remote Code Execution Lab
// Language: C17 (Hardened GCC: Stack Canaries, Full RELRO, ASLR)

#include <stdio.h>
#include <stdlib.h>

int main(void) {
    printf("=== C17 Hardened Execution Environment ===\\n");
    printf("Compiled with: gcc -std=c17 -O2 -fstack-protector-strong\\n\\n");
    
    char buffer[256];
    if (fgets(buffer, sizeof(buffer), stdin)) {
        printf("Standard Input: %s", buffer);
    }
    
    printf("Executing memory-efficient computation...\\n");
    int sum = 0;
    for (int i = 1; i <= 100; i++) {
        sum += i;
    }
    printf("Sum(1..100) = %d\\n", sum);
    
    printf("\\n[SUCCESS] C binary completed execution with exit code 0.\\n");
    return 0;
}
`,
  },
  cpp: {
    name: 'C++20 (G++ 14)',
    filename: 'main.cpp',
    monacoLang: 'cpp',
    tag: 'AOT Compiled',
    code: `// Secure Real-Time Remote Code Execution Lab
// Language: C++20 (Hardened G++: Template Caps, Stack Canaries, ASLR)

#include <iostream>
#include <vector>
#include <numeric>
#include <string>

int main() {
    std::cout << "=== C++20 Hardened Execution Environment ===" << std::endl;
    std::cout << "Compiled with: g++ -std=c++20 -O2 -fstack-protector-strong" << std::endl << std::endl;
    
    std::string input_line;
    if (std::getline(std::cin, input_line) && !input_line.empty()) {
        std::cout << "Standard Input: " << input_line << std::endl;
    }
    
    std::vector<int> numbers(100);
    std::iota(numbers.begin(), numbers.end(), 1);
    long long total = std::accumulate(numbers.begin(), numbers.end(), 0LL);
    
    std::cout << "Vector elements: " << numbers.size() << std::endl;
    std::cout << "Calculated sum: " << total << std::endl;
    std::cout << "\\n[SUCCESS] C++ binary completed cleanly." << std::endl;
    return 0;
}
`,
  },
  rust: {
    name: 'Rust (rustc 1.79+)',
    filename: 'main.rs',
    monacoLang: 'rust',
    tag: 'AOT Compiled',
    code: `// Secure Real-Time Remote Code Execution Lab
// Language: Rust 2021 Edition (Memory-Safe Native Binary)

use std::io::{self, Read};

fn main() {
    println!("=== Rust Hardened Execution Environment ===");
    println!("Compiled with: rustc -O --crate-type bin");
    
    let mut stdin_input = String::new();
    if let Ok(_) = io::stdin().read_to_string(&mut stdin_input) {
        if !stdin_input.trim().is_empty() {
            println!("Standard Input: {}", stdin_input.trim());
        }
    }
    
    let numbers: Vec<i64> = (1..=100).collect();
    let sum: i64 = numbers.iter().sum();
    println!("Calculated sum from vector: {}", sum);
    
    println!("\\n[SUCCESS] Rust memory-safe binary completed with exit code 0.");
}
`,
  },
  go: {
    name: 'Go (1.22+)',
    filename: 'main.go',
    monacoLang: 'go',
    tag: 'AOT Compiled',
    code: `// Secure Real-Time Remote Code Execution Lab
// Language: Go 1.22+ (Stripped Binary, Goroutine Scheduler)

package main

import (
	"bufio"
	"fmt"
	"os"
)

func main() {
	fmt.Println("=== Go 1.22+ Hardened Execution Environment ===")
	fmt.Println("Compiled with: go build -ldflags \"-s -w\"")

	scanner := bufio.NewScanner(os.Stdin)
	if scanner.Scan() {
		text := scanner.Text()
		if len(text) > 0 {
			fmt.Printf("Standard Input: %s\\n", text)
		}
	}

	sum := 0
	for i := 1; i <= 100; i++ {
		sum += i
	}
	fmt.Printf("Calculated sum(1..100): %d\\n", sum)
	fmt.Println("\\n[SUCCESS] Go application completed with exit code 0.")
}
`,
  },
  javascript: {
    name: 'JavaScript (Node 20)',
    filename: 'main.js',
    monacoLang: 'javascript',
    tag: 'JIT / Runtime',
    code: `// Secure Real-Time Remote Code Execution Lab
// Language: JavaScript (Node.js 20 LTS, Bounded V8 Heap)

const fs = require('fs');

function main() {
    console.log("=== Node.js 20 Execution Environment ===");
    console.log(\`Node.js: \${process.version} with 128MB V8 heap limit\`);
    
    try {
        const stdinData = fs.readFileSync(0, 'utf-8').trim();
        if (stdinData) {
            console.log("Standard Input:", stdinData);
        }
    } catch (_) {}

    const numbers = Array.from({ length: 100 }, (_, i) => i + 1);
    const sum = numbers.reduce((acc, curr) => acc + curr, 0);
    console.log("Calculated sum from array:", sum);
    
    console.log("\\n[SUCCESS] Node.js script executed cleanly.");
}

main();
`,
  },
};

export const DEFAULT_PYTHON_CODE = BOILERPLATES.python.code;

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  onRun: () => void;
  isRunning: boolean;
  onToggleStdin: () => void;
  isStdinOpen: boolean;
  hasStdinContent: boolean;
  selectedLanguage: SupportedLanguage;
  onSelectLanguage: (lang: SupportedLanguage) => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  onChange,
  onRun,
  isRunning,
  onToggleStdin,
  isStdinOpen,
  hasStdinContent,
  selectedLanguage,
  onSelectLanguage,
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

  const currentLangConfig = BOILERPLATES[selectedLanguage] || BOILERPLATES.python;

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLang = e.target.value as SupportedLanguage;
    onSelectLanguage(newLang);
    onChange(BOILERPLATES[newLang].code);
  };

  const handleReset = () => {
    onChange(currentLangConfig.code);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      {/* Editor Header Toolbar */}
      <div className="bg-slate-800/80 border-b border-slate-700/80 px-4 py-2.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-xs text-slate-300 font-semibold">
            <FileCode className="w-4 h-4 text-sky-400" />
            <span>{currentLangConfig.filename}</span>
          </div>

          {/* Polyglot Language Selector */}
          <div className="relative inline-block">
            <select
              value={selectedLanguage}
              onChange={handleLanguageChange}
              disabled={isRunning}
              className="appearance-none bg-slate-700/90 text-slate-200 text-xs font-medium pl-2.5 pr-7 py-1 rounded-md border border-slate-600/80 hover:border-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer disabled:opacity-50"
            >
              <option value="python">Python 3.12</option>
              <option value="c">C17 (GCC 14)</option>
              <option value="cpp">C++20 (G++ 14)</option>
              <option value="rust">Rust (rustc)</option>
              <option value="go">Go (1.22+)</option>
              <option value="javascript">JavaScript (Node 20)</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <span className="hidden sm:inline-block text-[10px] bg-sky-950/60 text-sky-300 px-2 py-0.5 rounded font-mono border border-sky-800/50">
            {currentLangConfig.tag}
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
            title="Reset to language starter boilerplate"
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
                <span>Executing...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run</span>
                <span className="hidden sm:inline text-[10px] opacity-70 ml-1 font-mono font-normal">
                  (Ctrl+Enter)
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
          language={currentLangConfig.monacoLang}
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
