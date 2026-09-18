import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import { CollaborativeRoom, RoomPresenceEvent, RoomCodeDeltaEvent, RoomCursorMoveEvent } from '../types';

interface Member {
  userId: string;
  email: string;
}

interface UseCollaborativeRoomOptions {
  currentUser?: import('../types').User | null;
  onRemoteCodeChange?: (newCode: string) => void;
  onRemoteCursor?: (cursor: { email: string; line: number; column: number }) => void;
  onNotification?: (msg: string) => void;
}

export function useCollaborativeRoom(options: UseCollaborativeRoomOptions = {}) {
  const [activeRoom, setActiveRoom] = useState<CollaborativeRoom | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [members, setMembers] = useState<Member[]>([]);
  const [lastPeerCursor, setLastPeerCursor] = useState<{ email: string; line: number; column: number } | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const disconnectSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
  }, []);

  const leaveRoom = useCallback(() => {
    disconnectSocket();
    setActiveRoom(null);
    setIsConnected(false);
    setMembers([]);
    setLastPeerCursor(null);
    localStorage.removeItem('rce_active_room_id');
    try {
      const url = new URL(window.location.href);
      if (url.searchParams.has('room')) {
        url.searchParams.delete('room');
        window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
      }
    } catch {
      // ignore
    }
  }, [disconnectSocket]);

  const connectToRoom = useCallback((room: CollaborativeRoom) => {
    disconnectSocket();

    const token = api.getToken();
    if (!token) {
      alert('Authentication required to join a collaborative room.');
      return;
    }

    // Persist active room across page reloads and update URL
    localStorage.setItem('rce_active_room_id', room.id);
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('room', room.id);
      window.history.replaceState({}, '', url.toString());
    } catch {
      // ignore
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/v1/rooms/${room.id}?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    setActiveRoom(room);

    ws.onopen = () => {
      setIsConnected(true);
      optionsRef.current.onNotification?.(`Connected to room: "${room.name}"`);
    };

    ws.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        const myUser = optionsRef.current.currentUser;

        if (frame.type === 'presence') {
          const presence = frame as RoomPresenceEvent;
          const isSelf = myUser && (presence.user_id === myUser.id || presence.email === myUser.email);
          if (isSelf) return;

          if (presence.action === 'joined') {
            setMembers((prev) => {
              if (prev.some((m) => m.userId === presence.user_id)) return prev;
              return [...prev, { userId: presence.user_id, email: presence.email }];
            });
            optionsRef.current.onNotification?.(`${presence.email} joined the room.`);
          } else if (presence.action === 'left') {
            setMembers((prev) => prev.filter((m) => m.userId !== presence.user_id));
            optionsRef.current.onNotification?.(`${presence.email} left the room.`);
          }
        } else if (frame.type === 'code_delta') {
          const codeDelta = frame as RoomCodeDeltaEvent;
          const isSelf = myUser && (codeDelta.sender_id === myUser.id || codeDelta.sender_email === myUser.email);
          if (isSelf) return;

          optionsRef.current.onRemoteCodeChange?.(codeDelta.delta);
        } else if (frame.type === 'cursor_move') {
          const cursor = frame as RoomCursorMoveEvent;
          const isSelf = myUser && (cursor.sender_id === myUser.id || cursor.sender_email === myUser.email);
          if (isSelf) return;

          const peer = {
            email: cursor.sender_email || 'Peer',
            line: cursor.line,
            column: cursor.column,
          };
          setLastPeerCursor(peer);
          optionsRef.current.onRemoteCursor?.(peer);
        }
      } catch (err) {
        console.error('Failed to parse collaborative room event:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
    };

    ws.onerror = (err) => {
      console.error('Collaborative room WebSocket error:', err);
    };
  }, [leaveRoom]);

  const sendCodeDelta = useCallback((newCode: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'code_delta',
          delta: newCode,
          version: 1,
        })
      );
    }
  }, []);

  const sendCursorMove = useCallback((line: number, column: number) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'cursor_move',
          line,
          column,
        })
      );
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnectSocket();
    };
  }, [disconnectSocket]);

  return {
    activeRoom,
    isConnected,
    members,
    lastPeerCursor,
    connectToRoom,
    leaveRoom,
    sendCodeDelta,
    sendCursorMove,
  };
}
