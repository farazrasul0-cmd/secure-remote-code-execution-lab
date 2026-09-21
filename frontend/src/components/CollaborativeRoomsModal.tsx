import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Plus,
  RefreshCw,
  X,
  Globe,
  Loader2,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  LogIn,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { CollaborativeRoom, SupportedLanguage } from '../types';
import { BOILERPLATES } from './CodeEditor';

interface CollaborativeRoomsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectRoom: (room: CollaborativeRoom) => void;
  onOpenAuth?: () => void;
  currentRoomId?: string | null;
}

export const CollaborativeRoomsModal: React.FC<CollaborativeRoomsModalProps> = ({
  isOpen,
  onClose,
  onSelectRoom,
  onOpenAuth,
  currentRoomId,
}) => {
  const { isAuthenticated } = useAuth();
  const [tab, setTab] = useState<'browse' | 'create'>('browse');
  const [rooms, setRooms] = useState<CollaborativeRoom[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [roomName, setRoomName] = useState<string>('');
  const [language, setLanguage] = useState<SupportedLanguage>('python');
  const [maxMembers, setMaxMembers] = useState<number>(10);
  const [initialCode, setInitialCode] = useState<string>(BOILERPLATES.python.code);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [joiningRoomId, setJoiningRoomId] = useState<string | null>(null);

  const fetchRooms = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listRooms(1, 50);
      setRooms(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch collaborative rooms');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchRooms();
    }
  }, [isOpen, fetchRooms]);

  const handleLanguageSelect = (newLang: SupportedLanguage) => {
    setLanguage(newLang);
    setInitialCode(BOILERPLATES[newLang]?.code || '');
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      if (onOpenAuth) {
        onOpenAuth();
      } else {
        setError('Authentication required. Please sign in to create a room.');
      }
      return;
    }

    if (!roomName.trim() || roomName.trim().length < 3) {
      setError('Room name must be at least 3 characters long.');
      return;
    }

    setIsCreating(true);
    setError(null);
    try {
      const newRoom = await api.createRoom({
        name: roomName.trim(),
        language,
        initial_code: initialCode,
        max_members: Number(maxMembers),
      });

      // Automatically join newly created room
      onSelectRoom(newRoom);
      onClose();
      setRoomName('');
    } catch (err: any) {
      setError(err.message || 'Failed to create room. Please ensure you are logged in.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleJoin = async (room: CollaborativeRoom) => {
    if (!isAuthenticated) {
      if (onOpenAuth) {
        onOpenAuth();
      } else {
        setError('Authentication required. Please sign in to join a room.');
      }
      return;
    }

    setJoiningRoomId(room.id);
    setError(null);
    try {
      await api.joinRoom(room.id);
      onSelectRoom(room);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to join room. Please ensure you are logged in.');
    } finally {
      setJoiningRoomId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[88vh]"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="px-6 py-4 bg-slate-800/80 border-b border-slate-700/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Collaborative Coding Rooms
                <span className="text-[11px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-mono border border-emerald-500/30 font-normal">
                  Live Sync
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Co-code with peers in real-time with full-duplex OT/deltas & presence.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="px-6 pt-3 pb-0 bg-slate-850 border-b border-slate-800 flex items-center space-x-2">
          <button
            onClick={() => setTab('browse')}
            className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition-all ${
              tab === 'browse'
                ? 'border-sky-500 text-sky-400 bg-slate-800/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Active Rooms ({rooms.length})</span>
          </button>
          <button
            onClick={() => setTab('create')}
            className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg border-b-2 transition-all ${
              tab === 'create'
                ? 'border-sky-500 text-sky-400 bg-slate-800/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create New Room</span>
          </button>
        </div>

        {/* Guest Warning Banner */}
        {!isAuthenticated && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs flex items-center justify-between gap-3 shadow-md animate-in fade-in duration-150">
            <div className="flex items-center space-x-2">
              <LogIn className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                You are currently in guest mode. <strong>Sign in</strong> to enter or create rooms.
              </span>
            </div>
            {onOpenAuth && (
              <button
                onClick={onOpenAuth}
                className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-xs transition-all shrink-0 active:scale-95 shadow-sm"
              >
                Sign In / Register
              </button>
            )}
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs flex items-center justify-between gap-2">
            <span className="flex-1">{error}</span>
            {(!isAuthenticated || error.toLowerCase().includes('authenticated') || error.toLowerCase().includes('login')) && onOpenAuth && (
              <button
                onClick={onOpenAuth}
                className="px-2.5 py-1 bg-rose-900/80 hover:bg-rose-800 text-rose-100 rounded text-[11px] font-semibold transition-colors shrink-0"
              >
                Sign In
              </button>
            )}
            <button
              onClick={() => setError(null)}
              className="text-rose-400 hover:text-rose-200 ml-2 font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {/* Tab Content */}
        <div className="p-6 overflow-y-auto flex-1 custom-scrollbar">
          {tab === 'browse' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  Select a room to enter collaborative sandbox session:
                </p>
                <button
                  onClick={fetchRooms}
                  disabled={loading}
                  className="flex items-center space-x-1 text-xs text-sky-400 hover:text-sky-300 bg-slate-800/80 px-2.5 py-1 rounded border border-slate-700 hover:border-slate-600 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>

              {loading && rooms.length === 0 ? (
                <div className="py-12 flex flex-col items-center justify-center text-slate-400">
                  <Loader2 className="w-8 h-8 animate-spin text-sky-400 mb-3" />
                  <p className="text-xs">Loading active rooms...</p>
                </div>
              ) : rooms.length === 0 ? (
                <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl p-8 bg-slate-900/40">
                  <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-400">
                    <Users className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-1">
                    No Collaborative Rooms Active
                  </h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
                    Be the first to launch a room! Other peers can join instantly with one click.
                  </p>
                  <button
                    onClick={() => setTab('create')}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Create First Room</span>
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {rooms.map((room) => {
                    const isCurrent = currentRoomId === room.id;
                    const isJoining = joiningRoomId === room.id;
                    return (
                      <div
                        key={room.id}
                        className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
                          isCurrent
                            ? 'bg-emerald-950/20 border-emerald-500/50 shadow-sm shadow-emerald-500/10'
                            : 'bg-slate-800/60 border-slate-700/80 hover:border-slate-600 hover:bg-slate-800'
                        }`}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h4 className="text-sm font-bold text-white truncate" title={room.name}>
                              {room.name}
                            </h4>
                            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-sky-950/60 text-sky-300 border border-sky-800/60 shrink-0">
                              {room.language}
                            </span>
                          </div>

                          <div className="flex items-center space-x-3 text-[11px] text-slate-400 mb-4 font-mono">
                            <span className="flex items-center space-x-1">
                              <Users className="w-3 h-3 text-slate-500" />
                              <span>Max: {room.max_members}</span>
                            </span>
                            <span>•</span>
                            <span className="truncate">
                              ID: {room.id.slice(0, 8)}...
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between pt-2 border-t border-slate-700/60">
                          {isCurrent ? (
                            <span className="text-xs font-semibold text-emerald-400 flex items-center space-x-1">
                              <ShieldCheck className="w-4 h-4" />
                              <span>Current Session</span>
                            </span>
                          ) : (
                            <button
                              onClick={() => handleJoin(room)}
                              disabled={isJoining}
                              className="w-full flex items-center justify-center space-x-1.5 py-1.5 px-3 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
                            >
                              {isJoining ? (
                                <>
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  <span>Entering...</span>
                                </>
                              ) : (
                                <>
                                  <span>Enter Room</span>
                                  <ArrowRight className="w-3.5 h-3.5" />
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {tab === 'create' && (
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Room Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  minLength={3}
                  maxLength={120}
                  placeholder="e.g. Distributed Algorithms Study Hall"
                  value={roomName}
                  onChange={(e) => setRoomName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Programming Runtime <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={language}
                    onChange={(e) => handleLanguageSelect(e.target.value as SupportedLanguage)}
                    className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="python">Python 3.12 (Isolated Sandbox)</option>
                    <option value="c">C17 (GCC 14)</option>
                    <option value="cpp">C++20 (G++ 14)</option>
                    <option value="rust">Rust (rustc)</option>
                    <option value="go">Go (1.22+)</option>
                    <option value="javascript">JavaScript (Node 20)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Max Concurrent Members (2 - 50)
                  </label>
                  <input
                    type="number"
                    min={2}
                    max={50}
                    value={maxMembers}
                    onChange={(e) => setMaxMembers(Math.max(2, Math.min(50, Number(e.target.value))))}
                    className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center justify-between">
                  <span>Initial Source Code</span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    Starter code synced to all joining peers
                  </span>
                </label>
                <textarea
                  rows={8}
                  value={initialCode}
                  onChange={(e) => setInitialCode(e.target.value)}
                  className="w-full font-mono text-xs px-3.5 py-2 bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500 resize-none leading-relaxed"
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setTab('browse')}
                  className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || !roomName.trim()}
                  className="flex items-center space-x-2 px-5 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-sky-600/20 active:scale-95 disabled:opacity-50"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Creating Room...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Create & Launch Room</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
