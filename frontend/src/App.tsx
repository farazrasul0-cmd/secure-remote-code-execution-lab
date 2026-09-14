import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { CodeEditor, DEFAULT_PYTHON_CODE } from './components/CodeEditor';
import { TerminalView } from './components/TerminalView';
import { TelemetryPanel } from './components/TelemetryPanel';
import { StdinDrawer } from './components/StdinDrawer';
import { SubmissionHistory } from './components/SubmissionHistory';
import { AuthModal } from './components/AuthModal';
import { useExecutionStream } from './hooks/useExecutionStream';
import { api } from './services/api';
import { Submission, SupportedLanguage } from './types';

const MainWorkspace: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [selectedLanguage, setSelectedLanguage] = useState<SupportedLanguage>('python');
  const [code, setCode] = useState<string>(DEFAULT_PYTHON_CODE);
  const [stdinData, setStdinData] = useState<string>('');
  const [isStdinOpen, setIsStdinOpen] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [refreshHistoryTrigger, setRefreshHistoryTrigger] = useState<number>(0);

  const stream = useExecutionStream({
    onFinish: () => {
      setRefreshHistoryTrigger((prev) => prev + 1);
    },
    onError: (err) => {
      console.error('Execution stream error:', err);
    },
  });

  const handleRunCode = async () => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }

    if (stream.isStreaming) return;

    try {
      const submission = await api.createSubmission({
        language: selectedLanguage,
        source_code: code,
        stdin_data: stdinData.trim() ? stdinData : null,
      });

      stream.connect(submission.id);
      setRefreshHistoryTrigger((prev) => prev + 1);
    } catch (err: any) {
      alert(`Submission failed: ${err.message || 'Unknown network error'}`);
    }
  };

  const handleSelectHistoricalSubmission = (submission: Submission) => {
    setCode(submission.source_code);
    if (submission.language && ['python', 'c', 'cpp', 'rust', 'go', 'javascript'].includes(submission.language)) {
      setSelectedLanguage(submission.language as SupportedLanguage);
    }
    if (submission.stdin_data) {
      setStdinData(submission.stdin_data);
      setIsStdinOpen(true);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans antialiased">
      <Navbar onOpenAuth={() => setIsAuthModalOpen(true)} />

      <main className="flex-1 max-w-[1700px] w-full mx-auto p-4 sm:p-6 flex flex-col gap-4">
        {/* Split Workstation Pane */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 items-stretch">
          {/* Left Column: Monaco Code Editor */}
          <div className="lg:col-span-7 flex flex-col min-h-[500px] lg:min-h-[620px]">
            <CodeEditor
              code={code}
              onChange={setCode}
              onRun={handleRunCode}
              isRunning={stream.isStreaming}
              onToggleStdin={() => setIsStdinOpen(!isStdinOpen)}
              isStdinOpen={isStdinOpen}
              hasStdinContent={!!stdinData.trim()}
              selectedLanguage={selectedLanguage}
              onSelectLanguage={setSelectedLanguage}
            />
            <StdinDrawer
              isOpen={isStdinOpen}
              value={stdinData}
              onChange={setStdinData}
              onClose={() => setIsStdinOpen(false)}
              disabled={stream.isStreaming}
            />
          </div>

          {/* Right Column: Virtual Terminal + Telemetry */}
          <div className="lg:col-span-5 flex flex-col gap-4 min-h-[500px] lg:min-h-[620px]">
            <div className="flex-1 min-h-[350px]">
              <TerminalView
                chunks={stream.chunks}
                streamState={stream.state}
              />
            </div>
            <div>
              <TelemetryPanel
                telemetry={stream.telemetry}
                status={stream.status}
                isRunning={stream.isStreaming}
              />
            </div>
          </div>
        </div>

        {/* Bottom Panel: Submission History & Audit Log */}
        <SubmissionHistory
          onSelectSubmission={handleSelectHistoricalSubmission}
          refreshTrigger={refreshHistoryTrigger}
        />
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <MainWorkspace />
    </AuthProvider>
  );
}
