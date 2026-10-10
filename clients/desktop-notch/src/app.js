/**
 * Ekko Desktop Notch Client Application
 * Bridges Webview to Tauri v2 IPC and coordinates Mascot micro-emotions.
 */

// IPC Gateway adapter with browser fallback for testing and preview
const isTauri = typeof window !== "undefined" && Boolean(window.__TAURI__);

async function invokeRpc(cmd, args = {}) {
  if (isTauri && window.__TAURI__.core) {
    return window.__TAURI__.core.invoke(cmd, args);
  }
  // Browser preview mock adapter
  console.log(`[Browser Preview IPC Mock] Calling: ${cmd}`, args);
  if (cmd === "ping") {
    return { status: "ok", timestamp: new Date().toISOString() };
  }
  if (cmd === "scan_inbox") {
    return [
      {
        id: "sig_mock_1",
        source_id: "arxiv_ai",
        title: "Predicting Alignment Generalization with Value Representations",
        url: "https://arxiv.org/abs/2610.12410v1",
        author: "Andy Liu",
        status: "pending",
        published_at: new Date().toISOString(),
      },
      {
        id: "sig_mock_2",
        source_id: "hn_tech",
        title: "MAMHOI: Scene-Aware Human-Object Interaction",
        url: "https://news.ycombinator.com",
        author: "Mingyuan Lei",
        status: "pending",
        published_at: new Date().toISOString(),
      },
    ];
  }
  if (cmd === "query_knowledge") {
    return [{ note: { title: "FastEmbed Intro", summary: "Lightweight CPU embeddings" }, score: 0.032 }];
  }
  return null;
}

// State variables
let isExpanded = false;
let currentEmotion = "idle";

// DOM Elements
const notchApp = document.getElementById("notch-app");
const notchCapsule = document.getElementById("notch-capsule");
const dropZone = document.getElementById("drop-zone");
const notchStatus = document.getElementById("notch-status");
const toggleBtn = document.getElementById("toggle-drawer-btn");
const mascotSvg = document.getElementById("mascot-svg");
const signalsList = document.getElementById("signals-list");
const refreshBtn = document.getElementById("refresh-signals-btn");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const ipcBadge = document.getElementById("ipc-badge");

/**
 * Update Mascot micro-emotion and visual face expression
 */
function setMascotEmotion(emotion, label = null) {
  currentEmotion = emotion;
  mascotSvg.classList.remove("emotion-idle", "emotion-ingesting", "emotion-alert");

  const faceGroup = document.getElementById("mascot-face");
  if (emotion === "ingesting") {
    mascotSvg.classList.add("emotion-ingesting");
    notchStatus.textContent = label || "Ingestion";
    faceGroup.innerHTML = `
      <circle cx="16" cy="22" r="2" fill="#ffffff" />
      <circle cx="24" cy="22" r="2" fill="#ffffff" />
      <ellipse cx="20" cy="27" rx="2.5" ry="3" fill="#ffffff" />
    `;
  } else if (emotion === "alert") {
    mascotSvg.classList.add("emotion-alert");
    notchStatus.textContent = label || "Alerte !";
    faceGroup.innerHTML = `
      <circle cx="16" cy="21" r="2.2" fill="#ffffff" />
      <circle cx="24" cy="21" r="2.2" fill="#ffffff" />
      <path d="M18 26 Q20 25 22 26" stroke="#ffffff" stroke-width="1.5" fill="none" stroke-linecap="round" />
    `;
  } else {
    mascotSvg.classList.add("emotion-idle");
    notchStatus.textContent = label || (isExpanded ? "Tiroir" : "Veille");
    faceGroup.innerHTML = `
      <circle class="eye eye-left" cx="16" cy="23" r="1.5" fill="#ffffff" />
      <circle class="eye eye-right" cx="24" cy="23" r="1.5" fill="#ffffff" />
      <path class="mouth" d="M18 27 Q20 28 22 27" stroke="#ffffff" stroke-width="1.2" fill="none" stroke-linecap="round" />
    `;
  }
}

/**
 * Toggle Drawer expansion and resize window
 */
async function toggleDrawer(forceState = null) {
  isExpanded = forceState !== null ? forceState : !isExpanded;
  if (isExpanded) {
    notchApp.classList.remove("collapsed");
    setMascotEmotion("idle", "Tiroir");
  } else {
    notchApp.classList.add("collapsed");
    setMascotEmotion("idle", "Veille");
  }

  try {
    await invokeRpc("set_notch_expanded", { expanded: isExpanded });
  } catch (err) {
    console.debug("Resize window notification handled:", err);
  }
}

/**
 * Setup Universal Drop & Forget Zone
 */
function setupDropZone() {
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
    setMascotEmotion("ingesting", "Drop...");
  });

  dropZone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    setMascotEmotion("idle", isExpanded ? "Tiroir" : "Veille");
  });

  dropZone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    setMascotEmotion("ingesting", "Absorption !");

    let dropSummary = "Contenu absorbé";
    if (e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      dropSummary = `Fichier : ${file.name}`;
    } else {
      const text = e.dataTransfer.getData("text/plain");
      if (text) {
        dropSummary = text.startsWith("http") ? `Lien : ${text.slice(0, 40)}...` : `Note : ${text.slice(0, 30)}...`;
      }
    }

    appendChatMessage("assistant", `📥 [Drop & Forget] ${dropSummary}. Ingestion et classement en cours.`);
    if (!isExpanded) {
      await toggleDrawer(true);
    }

    setTimeout(() => {
      setMascotEmotion("alert", "Ingéré !");
      setTimeout(() => setMascotEmotion("idle"), 2500);
    }, 1200);
  });
}

/**
 * Tab Navigation Switcher
 */
function setupTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.dataset.tab;
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }
    });
  });
}

/**
 * Load Signals into Écho Tab
 */
async function loadSignals() {
  signalsList.innerHTML = '<div class="loading-state">Interrogation de la boîte de réception...</div>';
  try {
    const signals = await invokeRpc("scan_inbox", { limit: 8 });
    if (!signals || signals.length === 0) {
      signalsList.innerHTML = '<div class="loading-state">Aucun signal brut en attente.</div>';
      return;
    }

    signalsList.innerHTML = signals
      .map(
        (s) => `
      <div class="signal-card">
        <div class="signal-title">${s.title}</div>
        <div class="signal-meta">
          <span class="signal-source-badge">${s.source_id}</span>
          <span>${s.author || "Source web"}</span>
          ${s.url ? `<a href="${s.url}" target="_blank" style="color: #60a5fa; text-decoration: none;">Voir</a>` : ""}
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    signalsList.innerHTML = `<div class="loading-state" style="color: #f87171;">Erreur IPC : ${err}</div>`;
  }
}

/**
 * Append chat message in Assistant Tab
 */
function appendChatMessage(role, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${role}`;
  msgDiv.innerHTML = `<span class="msg-bubble">${text}</span>`;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return msgDiv.querySelector(".msg-bubble");
}

/**
 * Setup Assistant interactive chat
 */
function setupChat() {
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    chatInput.value = "";
    appendChatMessage("user", text);
    setMascotEmotion("ingesting", "Réflexion...");

    const assistantBubble = appendChatMessage("assistant", "...");

    if (isTauri) {
      try {
        await invokeRpc("submit_prompt", { prompt: text, session_id: "notch_user" });
      } catch (err) {
        assistantBubble.textContent = `Erreur : ${err}`;
        setMascotEmotion("idle");
      }
    } else {
      // Mock stream preview
      setTimeout(() => {
        assistantBubble.textContent = `Je recherche dans vos connaissances pour : "${text}". Voici les informations pertinentes.`;
        setMascotEmotion("idle");
      }, 700);
    }
  });

  // Listen to Tauri stream events if available
  if (isTauri && window.__TAURI__.event) {
    window.__TAURI__.event.listen("engine-event", (event) => {
      const data = event.payload;
      const eventType = data.type || data.event;
      if (eventType === "token_chunk" && data.delta) {
        const lastBubble = chatMessages.querySelector(".chat-msg.assistant:last-child .msg-bubble");
        if (lastBubble) {
          if (lastBubble.textContent === "...") lastBubble.textContent = "";
          lastBubble.textContent += data.delta;
        }
      } else if (eventType === "turn_completed") {
        setMascotEmotion("idle");
      }
    });
  }
}

/**
 * Check IPC connection
 */
async function checkIpcStatus() {
  try {
    const res = await invokeRpc("ping");
    if (res && res.status === "ok") {
      ipcBadge.textContent = "Connecté (UNIX /tmp/ekko.sock)";
      ipcBadge.className = "badge connected";
    } else {
      throw new Error("Invalid ping response");
    }
  } catch (err) {
    ipcBadge.textContent = "Hors ligne (/tmp/ekko.sock)";
    ipcBadge.className = "badge disconnected";
  }
}

// Initialization on load
document.addEventListener("DOMContentLoaded", () => {
  notchCapsule.addEventListener("click", (e) => {
    if (e.target.closest("#toggle-drawer-btn") || e.target.closest("#drop-zone")) {
      toggleDrawer();
    }
  });

  refreshBtn.addEventListener("click", loadSignals);
  setupDropZone();
  setupTabs();
  setupChat();
  checkIpcStatus();
  loadSignals();
  setMascotEmotion("idle");
});
