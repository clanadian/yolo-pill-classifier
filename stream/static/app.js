// 서버(stream/server.py)가 이미 bbox+라벨을 그려 보내므로, 여기서는
// 받은 JPEG를 그대로 그리는 일, 조합 배너/복용 타이밍 안내(JSON 텍스트
// 메시지) 갱신, 연결이 끊겼을 때 재연결하는 일만 한다.

const img = document.getElementById("stream");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const banner = document.getElementById("combo-banner");
const bannerIcon = document.getElementById("combo-icon");
const bannerMessage = document.getElementById("combo-message");
const timingCard = document.getElementById("timing-card");
const timingList = document.getElementById("timing-list");
let lastUrl = null;

function setStatus(state, text) {
  statusEl.className = `status ${state}`;
  statusText.textContent = text;
}

function updateBanner(combo) {
  if (!combo) {
    banner.hidden = true;
    banner.classList.remove("good", "caution");
    return;
  }
  bannerIcon.textContent = combo.type === "caution" ? "⚠" : "✓";
  bannerMessage.textContent = combo.message || "";
  banner.classList.remove("good", "caution");
  banner.classList.add(combo.type === "caution" ? "caution" : "good");
  banner.hidden = false;
}

function updateTimings(timings) {
  timingList.replaceChildren();
  if (!timings || timings.length === 0) {
    timingCard.hidden = true;
    return;
  }
  for (const t of timings) {
    const row = document.createElement("div");
    row.className = "timing-row";

    const name = document.createElement("span");
    name.className = "timing-name";
    name.textContent = t.class;

    const message = document.createElement("span");
    message.className = "timing-message";
    message.textContent = t.message;

    row.append(name, message);
    timingList.append(row);
  }
  timingCard.hidden = false;
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    setStatus("live", "live");
  };

  ws.onmessage = (ev) => {
    if (typeof ev.data === "string") {
      const payload = JSON.parse(ev.data);
      updateBanner(payload.combo);
      updateTimings(payload.timings);
      return;
    }
    const url = URL.createObjectURL(new Blob([ev.data], { type: "image/jpeg" }));
    img.src = url;
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = url;
  };

  ws.onclose = () => {
    setStatus("retrying", "disconnected — retrying…");
    updateBanner(null);
    updateTimings(null);
    setTimeout(connect, 1500);
  };

  ws.onerror = () => {
    ws.close();
  };
}

connect();
