import React, { useState, useRef, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { CodeEditor, DEFAULT_PYTHON_CODE } from './components/CodeEditor';
import { TerminalView } from './components/TerminalView';
import { TelemetryPanel } from './components/TelemetryPanel';
import { SubmissionHistory } from './components/SubmissionHistory';
import { AuthModal } from './components/AuthModal';
import { ProblemPanel } from './components/ProblemPanel';
import { GradingScorecard } from './components/GradingScorecard';
import { CollaborativeRoomsModal } from './components/CollaborativeRoomsModal';
import { useExecutionStream } from './hooks/useExecutionStream';
import { useCollaborativeRoom } from './hooks/useCollaborativeRoom';
import { api } from './services/api';
import {
  CollaborativeRoom,
  GradingScorecard as IGradingScorecard,
  Submission,
  SupportedLanguage,
} from './types';
import { Copy, Check, LogOut } from 'lucide-react';

const MainWorkspace: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [selectedLanguage, setSelectedLanguage] = useState<SupportedLanguage>('python');
  const [code, setCode] = useState<string>(DEFAULT_PYTHON_CODE);
  const [stdinData, setStdinData] = useState<string>('');
  const [isStdinOpen, setIsStdinOpen] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [isRoomsModalOpen, setIsRoomsModalOpen] = useState<boolean>(false);
  const [copiedRoomId, setCopiedRoomId] = useState<boolean>(false);
  const [refreshHistoryTrigger, setRefreshHistoryTrigger] = useState<number>(0);
  const [activeScorecard, setActiveScorecard] = useState<IGradingScorecard | null>(null);
  const [isScorecardOpen, setIsScorecardOpen] = useState<boolean>(false);
  const [isGrading, setIsGrading] = useState<boolean>(false);

  const isRemoteUpdateRef = useRef<boolean>(false);

  const collab = useCollaborativeRoom({
    currentUser: user,
    onRemoteCodeChange: (newCode: string) => {
      isRemoteUpdateRef.current = true;
      setCode(newCode);
      setTimeout(() => {
        isRemoteUpdateRef.current = false;
      }, 50);
    },
  });

  const stream = useExecutionStream({
    onFinish: () => {
      setRefreshHistoryTrigger((prev) => prev + 1);
    },
    onError: (err) => {
      console.error('Execution stream error:', err);
    },
  });

  const handleCodeChange = (newCode: string) => {
    setCode(newCode);
    if (collab.activeRoom && !isRemoteUpdateRef.current) {
      collab.sendCodeDelta(newCode);
    }
  };

  const handleCursorChange = (line: number, column: number) => {
    if (collab.activeRoom) {
      collab.sendCursorMove(line, column);
    }
  };

  const handleSelectRoom = (room: CollaborativeRoom) => {
    collab.connectToRoom(room);
    if (room.current_code) {
      setCode(room.current_code);
    }
    if (room.language && ['python', 'c', 'cpp', 'rust', 'go', 'javascript'].includes(room.language)) {
      setSelectedLanguage(room.language as SupportedLanguage);
    }
  };

  // Auto-restore collaborative room session across page refreshes or shared URLs
  useEffect(() => {
    if (!isAuthenticated) return;
    const params = new URLSearchParams(window.location.search);
    const savedRoomId = params.get('room') || localStorage.getItem('rce_active_room_id');
    if (!savedRoomId) return;

    let isMounted = true;
    api
      .getRoom(savedRoomId)
      .then((room) => {
        if (!isMounted) return;
        if (room && room.is_active) {
          collab.connectToRoom(room);
          if (room.current_code) {
            setCode(room.current_code);
          }
          if (room.language && ['python', 'c', 'cpp', 'rust', 'go', 'javascript'].includes(room.language)) {
            setSelectedLanguage(room.language as SupportedLanguage);
          }
        } else {
          localStorage.removeItem('rce_active_room_id');
          const url = new URL(window.location.href);
          url.searchParams.delete('room');
          window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
        }
      })
      .catch((err) => {
        console.warn('Could not restore room session:', err);
        localStorage.removeItem('rce_active_room_id');
        const url = new URL(window.location.href);
        url.searchParams.delete('room');
        window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
      });

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, collab.connectToRoom]);

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
        timeout_seconds: 30,
      });

      stream.connect(submission.id);
      setRefreshHistoryTrigger((prev) => prev + 1);
    } catch (err: any) {
      alert(`Submission failed: ${err.message || 'Unknown network error'}`);
    }
  };

  const handleSubmitForGrading = async (problemSlug: string) => {
    if (!isAuthenticated) {
      setIsAuthModalOpen(true);
      return;
    }

    try {
      setIsGrading(true);
      setIsScorecardOpen(true);
      const scorecard = await api.submitProblemForGrading(problemSlug, {
        language: selectedLanguage,
        source_code: code,
      });
      setActiveScorecard(scorecard);
      setRefreshHistoryTrigger((prev) => prev + 1);
    } catch (err: any) {
      alert(`Grading submission failed: ${err.message || 'Unknown network error'}`);
      setIsScorecardOpen(false);
    } finally {
      setIsGrading(false);
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
      <Navbar
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenRooms={() => setIsRoomsModalOpen(true)}
        activeRoom={collab.activeRoom}
        activeMemberCount={collab.members.length + 1}
        onLeaveRoom={collab.leaveRoom}
      />

      <main className="flex-1 max-w-[1700px] w-full mx-auto p-4 sm:p-6 flex flex-col gap-4">
        {/* Top Problem & Autograding Header Panel */}
        <ProblemPanel
          onSubmitForGrading={handleSubmitForGrading}
          isGrading={isGrading}
        />

        {/* Collaborative Room Status Banner */}
        {collab.activeRoom && (
          <div className="bg-slate-900/90 border border-emerald-500/40 rounded-xl p-3 px-4 flex flex-wrap items-center justify-between gap-3 shadow-lg shadow-emerald-950/20 animate-in fade-in duration-200">
            <div className="flex items-center space-x-3">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-white tracking-wide">
                    {collab.activeRoom.name}
                  </span>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700/60">
                    {collab.activeRoom.language}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 flex items-center space-x-2">
                  <span>Live Synchronized Session</span>
                  <span>•</span>
                  <span className="text-emerald-400 font-medium">
                    {collab.members.length + 1} online ({user?.email}
                    {collab.members.length > 0 && ` + ${collab.members.map((m) => m.email).join(', ')}`})
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  const inviteUrl = `${window.location.origin}${window.location.pathname}?room=${collab.activeRoom?.id || ''}`;
                  navigator.clipboard.writeText(inviteUrl);
                  setCopiedRoomId(true);
                  setTimeout(() => setCopiedRoomId(false), 2000);
                }}
                className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-lg transition-colors"
                title="Copy shareable invite link for peers"
              >
                {copiedRoomId ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span>{copiedRoomId ? 'Copied Link' : 'Copy Invite Link'}</span>
              </button>

              <button
                onClick={collab.leaveRoom}
                className="flex items-center space-x-1.5 text-xs text-rose-300 hover:text-rose-200 bg-rose-950/40 hover:bg-rose-900/50 border border-rose-800/60 px-3 py-1.5 rounded-lg transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Leave Room</span>
              </button>
            </div>
          </div>
        )}

        {/* Split Workstation Pane */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 items-stretch">
          {/* Left Column: Monaco Code Editor */}
          <div className="lg:col-span-7 flex flex-col min-h-[500px] lg:min-h-[620px]">
            <CodeEditor
              code={code}
              onChange={handleCodeChange}
              onRun={handleRunCode}
              isRunning={stream.isStreaming}
              onToggleStdin={() => setIsStdinOpen(!isStdinOpen)}
              isStdinOpen={isStdinOpen}
              hasStdinContent={!!stdinData.trim()}
              stdinValue={stdinData}
              onStdinChange={setStdinData}
              selectedLanguage={selectedLanguage}
              onSelectLanguage={setSelectedLanguage}
              peerCursor={collab.lastPeerCursor}
              onCursorChange={handleCursorChange}
            />
          </div>

          {/* Right Column: Virtual Terminal + Telemetry */}
          <div className="lg:col-span-5 flex flex-col gap-4 min-h-[500px] lg:min-h-[620px]">
            <div className="flex-1 min-h-[350px]">
              <TerminalView
                chunks={stream.chunks}
                streamState={stream.state}
                onData={stream.sendInput}
                onResize={stream.sendResize}
                onSignal={stream.sendSignal}
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

      {/* Collaborative Rooms Modal */}
      <CollaborativeRoomsModal
        isOpen={isRoomsModalOpen}
        onClose={() => setIsRoomsModalOpen(false)}
        onSelectRoom={handleSelectRoom}
        onOpenAuth={() => {
          setIsRoomsModalOpen(false);
          setIsAuthModalOpen(true);
        }}
        currentRoomId={collab.activeRoom?.id}
      />

      {/* Autograding Scorecard Modal */}
      <GradingScorecard
        scorecard={activeScorecard}
        isOpen={isScorecardOpen}
        onClose={() => setIsScorecardOpen(false)}
        isSubmitting={isGrading}
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
