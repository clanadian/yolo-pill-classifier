// 서버(stream/server.py)가 이미 bbox+라벨을 그려 보내므로, 여기서는
// 받은 JPEG를 그대로 그리는 일과 연결이 끊겼을 때 재연결하는 일만 한다.

const img = document.getElementById("stream");
const status = document.getElementById("status");
let lastUrl = null;

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    status.textContent = "live";
  };

  ws.onmessage = (ev) => {
    const url = URL.createObjectURL(new Blob([ev.data], { type: "image/jpeg" }));
    img.src = url;
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = url;
  };

  ws.onclose = () => {
    status.textContent = "disconnected — retrying…";
    setTimeout(connect, 1500);
  };

  ws.onerror = () => {
    ws.close();
  };
}

connect();
