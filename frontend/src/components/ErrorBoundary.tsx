import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught component error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-slate-900 border border-rose-900/50 rounded-xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center space-x-3 text-rose-400">
              <AlertTriangle className="w-6 h-6" />
              <h2 className="text-lg font-bold">Application Render Error</h2>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              A UI component encountered an unexpected runtime error:
            </p>
            <pre className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-rose-300 overflow-x-auto border border-slate-800">
              {this.state.error?.message || 'Unknown error'}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="w-full flex items-center justify-center space-x-2 py-2 px-4 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Reload Workspace</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
