export function connectIncidentStream(onMessage, onError) {
  const api = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const wsBase = api.replace(/^http/, "ws");
  const socket = new WebSocket(`${wsBase}/ws/incidents`);
  socket.onmessage = event => { try { onMessage(JSON.parse(event.data)); } catch (e) { onError?.(e); } };
  socket.onerror = event => onError?.(event);
  return () => socket.close();
}
