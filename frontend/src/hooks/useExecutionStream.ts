import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { ExecutionStatus, ExecutionTelemetry, StreamChunk, WebSocketState } from '../types';

interface UseExecutionStreamOptions {
  onChunk?: (chunk: StreamChunk) => void;
  onFinish?: (telemetry: ExecutionTelemetry) => void;
  onError?: (error: string) => void;
}

export function useExecutionStream(options: UseExecutionStreamOptions = {}) {
  const [state, setState] = useState<WebSocketState>('DISCONNECTED');
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<StreamChunk[]>([]);
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [telemetry, setTelemetry] = useState<ExecutionTelemetry | null>(null);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const highestSequenceRef = useRef<number>(-1);
  const reconnectAttemptsRef = useRef<number>(0);
  const maxReconnectAttempts = 3;
  const isTerminatedRef = useRef<boolean>(false);

  const { onChunk, onFinish, onError } = options;

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setState('DISCONNECTED');
  }, []);

  const connectToStream = useCallback((targetSubmissionId: string) => {
    disconnect();

    setSubmissionId(targetSubmissionId);
    setChunks([]);
    setStatus('RUNNING');
    setTelemetry(null);
    setError(null);
    highestSequenceRef.current = -1;
    isTerminatedRef.current = false;
    reconnectAttemptsRef.current = 0;

    const token = api.getToken();
    if (!token) {
      const authErr = 'Authentication required to stream execution.';
      setError(authErr);
      setState('ERROR');
      onError?.(authErr);
      return;
    }

    setState('CONNECTING');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/v1/submissions/${targetSubmissionId}?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setState('STREAMING');
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const chunk: StreamChunk = JSON.parse(event.data);

        // Deduplication & monotonic sequence ordering check
        if (chunk.sequence !== undefined) {
          if (chunk.sequence <= highestSequenceRef.current) {
            // Duplicate chunk from buffer replay or network duplicate
            return;
          }
          highestSequenceRef.current = chunk.sequence;
        }

        setChunks((prev) => [...prev, chunk]);
        onChunk?.(chunk);

        // Check if message conveys status / termination telemetry
        if (chunk.status && chunk.status !== 'RUNNING' && chunk.status !== 'PENDING') {
          const finalStatus = chunk.status;
          const finalTelemetry: ExecutionTelemetry = {
            status: finalStatus,
            exit_code: chunk.exit_code ?? null,
            execution_time_ms: chunk.execution_time_ms ?? null,
            peak_memory_bytes: chunk.peak_memory_bytes ?? null,
          };

          setStatus(finalStatus);
          setTelemetry(finalTelemetry);
          isTerminatedRef.current = true;
          setState('FINISHED');
          onFinish?.(finalTelemetry);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket stream chunk:', err);
      }
    };

    ws.onerror = () => {
      const socketErr = 'WebSocket connection encountered an error.';
      setError(socketErr);
      onError?.(socketErr);
    };

    ws.onclose = (event: CloseEvent) => {
      if (isTerminatedRef.current || event.code === 1000) {
        setState('FINISHED');
        return;
      }

      if (event.code === 1008) {
        const policyErr = 'WebSocket disconnected: Unauthorized (invalid or expired token).';
        setError(policyErr);
        setState('ERROR');
        onError?.(policyErr);
        return;
      }

      // If disconnected unexpectedly during active execution, attempt reconnection with backoff
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        const backoffMs = Math.pow(2, reconnectAttemptsRef.current) * 500;
        reconnectAttemptsRef.current += 1;
        setTimeout(() => {
          if (!isTerminatedRef.current) {
            connectToStream(targetSubmissionId);
          }
        }, backoffMs);
      } else {
        setState('DISCONNECTED');
      }
    };
  }, [disconnect, onChunk, onFinish, onError]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const sendInput = useCallback((data: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'stdin', data }));
    }
  }, []);

  const sendResize = useCallback((cols: number, rows: number) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
  }, []);

  const sendSignal = useCallback((sig: string = 'SIGINT') => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'signal', signal: sig }));
    }
  }, []);

  return {
    state,
    submissionId,
    chunks,
    status,
    telemetry,
    error,
    isStreaming: state === 'STREAMING' || state === 'CONNECTING',
    connect: connectToStream,
    disconnect,
    sendInput,
    sendResize,
    sendSignal,
  };
}
