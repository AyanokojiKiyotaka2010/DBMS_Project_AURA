import { useEffect, useRef } from "react";
import { BACKEND_URL } from "./campus";

// Convert https:// -> wss:// and http:// -> ws://
function wsUrl(path) {
  if (!BACKEND_URL) return "";
  const isHttps = BACKEND_URL.startsWith("https://");
  const scheme = isHttps ? "wss://" : "ws://";
  const host = BACKEND_URL.replace(/^https?:\/\//, "");
  return `${scheme}${host}${path}`;
}

/**
 * Subscribes to /api/ws and calls `onMessage(parsedEvent)` for every server push.
 * Handlers are read from a ref, so callers don't need to memoise them.
 * Auto-reconnects with backoff. Cookies carry auth (HTTP-only access_token).
 */
export function useCampusSocket(onMessage) {
  const handlerRef = useRef(onMessage);
  useEffect(() => { handlerRef.current = onMessage; }, [onMessage]);

  useEffect(() => {
    let socket = null;
    let closed = false;
    let backoff = 1500;
    let pingTimer = null;

    const connect = () => {
      if (closed) return;
      try {
        socket = new WebSocket(wsUrl("/api/ws"));
      } catch {
        return;
      }
      socket.onopen = () => {
        backoff = 1500;
        // 30s ping to keep proxies from timing out
        pingTimer = setInterval(() => {
          try { socket && socket.readyState === 1 && socket.send("ping"); } catch {}
        }, 30_000);
      };
      socket.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (handlerRef.current) handlerRef.current(data);
        } catch {}
      };
      socket.onclose = () => {
        if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
        if (closed) return;
        setTimeout(connect, backoff);
        backoff = Math.min(backoff * 1.7, 20_000);
      };
      socket.onerror = () => {
        try { socket && socket.close(); } catch {}
      };
    };

    connect();
    return () => {
      closed = true;
      if (pingTimer) clearInterval(pingTimer);
      try { socket && socket.close(); } catch {}
    };
  }, []);
}
