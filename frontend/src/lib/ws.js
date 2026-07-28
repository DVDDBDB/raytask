// Lightweight WebSocket client with auto-reconnect and JSON events.
export function connectWS({ onMessage, onOpen, onClose } = {}) {
  const token = localStorage.getItem("raybotix_token");
  if (!token) return { close: () => {} };
  const base = process.env.REACT_APP_BACKEND_URL || "";
  const scheme = base.startsWith("https") ? "wss" : "ws";
  const host = base.replace(/^https?:\/\//, "");
  const url = `${scheme}://${host}/api/ws?token=${encodeURIComponent(token)}`;

  let ws;
  let closed = false;
  let pingIv = null;
  let reconnectTimer = null;

  const open = () => {
    ws = new WebSocket(url);
    ws.onopen = () => {
      onOpen && onOpen();
      pingIv = setInterval(() => { try { ws.send("ping"); } catch {} }, 25000);
    };
    ws.onmessage = (e) => {
      if (e.data === "pong") return;
      try {
        const data = JSON.parse(e.data);
        onMessage && onMessage(data);
      } catch {}
    };
    ws.onclose = () => {
      clearInterval(pingIv);
      onClose && onClose();
      if (!closed) reconnectTimer = setTimeout(open, 2000);
    };
    ws.onerror = () => { try { ws.close(); } catch {} };
  };
  open();

  return {
    close: () => {
      closed = true;
      clearTimeout(reconnectTimer);
      clearInterval(pingIv);
      try { ws?.close(); } catch {}
    },
  };
}
