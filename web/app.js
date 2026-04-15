const state = {
  playlist: null,
  currentClip: null,
};

const queryInput = document.getElementById("queryInput");
const generateBtn = document.getElementById("generateBtn");
const prepareBtn = document.getElementById("prepareBtn");
const playlistTitle = document.getElementById("playlistTitle");
const playlistMeta = document.getElementById("playlistMeta");
const playlistItems = document.getElementById("playlistItems");
const nowPlayingTitle = document.getElementById("nowPlayingTitle");
const nowPlayingSummary = document.getElementById("nowPlayingSummary");
const statusText = document.getElementById("statusText");
const healthText = document.getElementById("healthText");
const commandOutput = document.getElementById("commandOutput");
const audioPlayer = document.getElementById("audioPlayer");

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function setStatus(message) {
  statusText.textContent = message;
}

function secondsToMinutes(seconds) {
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${min}:${String(sec).padStart(2, "0")}`;
}

function renderPlaylist() {
  if (!state.playlist) {
    playlistItems.className = "playlist-items empty";
    playlistItems.textContent = "Generate a playlist to see clips here.";
    return;
  }

  playlistItems.className = "playlist-items";
  playlistTitle.textContent = `${state.playlist.theme.toUpperCase()} • ${state.playlist.subtopic}`;
  playlistMeta.textContent = `${state.playlist.items.length} clips • target ${secondsToMinutes(
    state.playlist.duration_target_sec
  )} • actual ${secondsToMinutes(state.playlist.duration_actual_sec)}`;

  playlistItems.innerHTML = "";
  state.playlist.items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "clip-card";
    card.innerHTML = `
      <div class="clip-top">
        <div>
          <div class="clip-title">${item.position}. ${item.episode_title}</div>
          <div class="clip-meta">${item.guest || "Lenny's Podcast"} • ${secondsToMinutes(
            item.duration_sec
          )}</div>
        </div>
        <span class="pill">${item.audio_status.replaceAll("_", " ")}</span>
      </div>
      <div class="clip-summary">${item.summary_short}</div>
      <div class="clip-actions">
        <button data-play="${item.clip_id}" ${item.audio_url ? "" : "disabled"}>Play</button>
        <button data-excerpt="${item.clip_id}">Show excerpt</button>
      </div>
    `;

    card.querySelector(`[data-excerpt="${item.clip_id}"]`).addEventListener("click", () => {
      commandOutput.textContent = item.transcript_excerpt;
    });

    const playButton = card.querySelector(`[data-play="${item.clip_id}"]`);
    if (playButton) {
      playButton.addEventListener("click", () => playClip(item.clip_id));
    }
    playlistItems.appendChild(card);
  });
}

function playClip(clipId) {
  if (!state.playlist) return;
  const clip = state.playlist.items.find((item) => item.clip_id === clipId);
  if (!clip || !clip.audio_url) return;
  state.currentClip = clip;
  nowPlayingTitle.textContent = clip.episode_title;
  nowPlayingSummary.textContent = clip.summary_short;
  audioPlayer.src = clip.audio_url;
  audioPlayer.play().catch(() => {});
}

async function fetchHealth() {
  try {
    const data = await request("/api/health", { method: "GET" });
    healthText.textContent = `Healthy • ${data.episode_count} episodes • ${data.audio_episode_count} audio mappings`;
  } catch (error) {
    healthText.textContent = `Health check failed: ${error.message}`;
  }
}

async function generatePlaylist() {
  try {
    setStatus("Generating playlist...");
    const playlist = await request("/api/playlists", {
      method: "POST",
      body: JSON.stringify({ query: queryInput.value }),
    });
    state.playlist = playlist;
    prepareBtn.disabled = false;
    renderPlaylist();
    commandOutput.textContent = playlist.intro_text;
    setStatus("Playlist ready. Prepare audio to make clips playable.");
  } catch (error) {
    setStatus(error.message);
  }
}

async function prepareAudio() {
  try {
    setStatus("Downloading source audio and rendering clips...");
    prepareBtn.disabled = true;
    const result = await request("/api/playlists/prepare", { method: "POST" });
    state.playlist = result.playlist;
    renderPlaylist();
    setStatus(`Prepared ${result.prepared} clips. ${result.skipped} skipped.`);
    if (result.errors.length) {
      commandOutput.textContent = JSON.stringify(result.errors, null, 2);
    } else {
      commandOutput.textContent = "Playable audio is ready. Click any Play button.";
    }
  } catch (error) {
    setStatus(error.message);
    prepareBtn.disabled = false;
  }
}

async function sendCommand(command) {
  try {
    const result = await request("/api/commands", {
      method: "POST",
      body: JSON.stringify({ command }),
    });
    commandOutput.textContent = result.message;
  } catch (error) {
    commandOutput.textContent = error.message;
  }
}

generateBtn.addEventListener("click", generatePlaylist);
prepareBtn.addEventListener("click", prepareAudio);
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    queryInput.value = chip.dataset.query;
    generatePlaylist();
  });
});
document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => sendCommand(button.dataset.command));
});

fetchHealth();
