import React, { useEffect, useState } from 'react';
import { Terminal, LogOut, LogIn, Activity, Users, LogOut as LeaveIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { CollaborativeRoom } from '../types';

interface NavbarProps {
  onOpenAuth: () => void;
  onOpenRooms: () => void;
  activeRoom?: CollaborativeRoom | null;
  activeMemberCount?: number;
  onLeaveRoom?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenAuth,
  onOpenRooms,
  activeRoom,
  activeMemberCount = 1,
  onLeaveRoom,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [clusterHealthy, setClusterHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    const checkCluster = async () => {
      try {
        const res = await api.checkHealth();
        setClusterHealthy(res.status === 'healthy');
      } catch {
        setClusterHealthy(false);
      }
    };
    checkCluster();
    const interval = setInterval(checkCluster, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-3 flex items-center justify-between shadow-md">
      {/* Brand & Platform Identity */}
      <div className="flex items-center space-x-3">
        <div className="bg-sky-500/10 border border-sky-500/30 p-2 rounded-lg text-sky-400">
          <Terminal className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold tracking-tight text-white">
              Secure RCE Platform
            </h1>
            <span className="text-xs bg-sky-500/20 text-sky-300 px-2 py-0.5 rounded font-mono border border-sky-500/30">
              v1.0-prod
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Isolated Micro-Sandbox Lab & Real-Time Stream Engine
          </p>
        </div>
      </div>

      {/* Cluster Health & Auth Controls */}
      <div className="flex items-center space-x-4">
        {/* Cluster Status Pill */}
        <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
          <Activity
            className={`w-3.5 h-3.5 ${
              clusterHealthy === true
                ? 'text-emerald-400 animate-pulse'
                : clusterHealthy === false
                ? 'text-rose-400'
                : 'text-amber-400'
            }`}
          />
          <span>
            {clusterHealthy === true
              ? 'Cluster Online'
              : clusterHealthy === false
              ? 'Cluster Offline'
              : 'Checking cluster...'}
          </span>
        </div>

        {/* Collaborative Rooms Control */}
        {activeRoom ? (
          <div className="flex items-center space-x-2 bg-emerald-950/50 border border-emerald-500/50 rounded-lg px-2.5 py-1.5 shadow-sm shadow-emerald-900/20">
            <button
              onClick={onOpenRooms}
              className="flex items-center space-x-2 text-xs text-emerald-300 hover:text-emerald-200 transition-colors"
              title="View Room Details / Switch Room"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="font-semibold truncate max-w-[110px] sm:max-w-[150px]">
                {activeRoom.name}
              </span>
              <span className="text-[10px] bg-emerald-900/80 px-1.5 py-0.5 rounded-full border border-emerald-700/60 font-mono">
                {activeMemberCount} online
              </span>
            </button>
            {onLeaveRoom && (
              <button
                onClick={onLeaveRoom}
                title="Leave Room"
                className="text-slate-400 hover:text-rose-400 p-0.5 rounded hover:bg-slate-800 transition-colors"
              >
                <LeaveIcon className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ) : (
          <button
            onClick={onOpenRooms}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 hover:border-slate-600 transition-all shadow-sm active:scale-95"
            title="Browse or create collaborative rooms"
          >
            <Users className="w-3.5 h-3.5 text-sky-400" />
            <span className="hidden sm:inline">Collaborative Rooms</span>
            <span className="sm:hidden">Rooms</span>
          </button>
        )}

        {/* User Authentication Display */}
        {isAuthenticated && user ? (
          <div className="flex items-center space-x-3 bg-slate-800/60 border border-slate-700/80 rounded-lg px-3 py-1.5">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-full bg-sky-600 flex items-center justify-center text-xs font-bold text-white uppercase">
                {user.username.slice(0, 1)}
              </div>
              <div className="text-left hidden md:block">
                <p className="text-xs font-medium text-slate-200">{user.username}</p>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                  {user.role}
                </p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="text-slate-400 hover:text-rose-400 transition-colors p-1 rounded hover:bg-slate-700"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="flex items-center space-x-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-sm shadow-sky-600/20 active:scale-95"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In / Register</span>
          </button>
        )}
      </div>
    </header>
  );
};
