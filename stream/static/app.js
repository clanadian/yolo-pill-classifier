// 서버(stream/server.py)가 이미 bbox+라벨을 그려 보내므로, 여기서는
// 받은 JPEG를 그대로 그리는 일, 조합 배너/복용 타이밍/복용량 안내(JSON
// 텍스트 메시지) 갱신, 연결이 끊겼을 때 재연결하는 일만 한다.

const img = document.getElementById("stream");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const banner = document.getElementById("combo-banner");
const bannerIcon = document.getElementById("combo-icon");
const bannerMessage = document.getElementById("combo-message");
const timingCard = document.getElementById("timing-card");
const timingList = document.getElementById("timing-list");
const dosageCard = document.getElementById("dosage-card");
const dosageList = document.getElementById("dosage-list");
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

// 클래스별 안내 목록(복용 타이밍, 복용량)을 같은 형식의 카드에 렌더링한다.
function updateInfoList(card, list, items) {
  list.replaceChildren();
  if (!items || items.length === 0) {
    card.hidden = true;
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "info-row";

    const name = document.createElement("span");
    name.className = "info-name";
    name.textContent = item.class;

    const message = document.createElement("span");
    message.className = "info-message";
    message.textContent = item.message;

    row.append(name, message);
    list.append(row);
  }
  card.hidden = false;
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
      updateInfoList(timingCard, timingList, payload.timings);
      updateInfoList(dosageCard, dosageList, payload.dosage);
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
    updateInfoList(timingCard, timingList, null);
    updateInfoList(dosageCard, dosageList, null);
    setTimeout(connect, 1500);
  };

  ws.onerror = () => {
    ws.close();
  };
}

connect();
