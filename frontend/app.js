/**
 * YouTube Video Analyzer & Downloader Frontend Controller
 */

// Application state
let currentVideoData = null;
let currentTranscriptText = "";

// DOM Elements
const serverStatusDot = document.getElementById("serverStatusDot");
const serverStatusText = document.getElementById("serverStatusText");

const analyzeForm = document.getElementById("analyzeForm");
const urlInput = document.getElementById("urlInput");
const pasteBtn = document.getElementById("pasteBtn");
const clearBtn = document.getElementById("clearBtn");
const submitBtn = document.getElementById("submitBtn");
const submitSpinner = document.getElementById("submitSpinner");

const alertBox = document.getElementById("alertBox");
const alertTitle = document.getElementById("alertTitle");
const alertDesc = document.getElementById("alertDesc");
const alertCloseBtn = document.getElementById("alertCloseBtn");

const skeletonLoader = document.getElementById("skeletonLoader");
const resultSection = document.getElementById("resultSection");

// Result card elements
const videoThumb = document.getElementById("videoThumb");
const videoDuration = document.getElementById("videoDuration");
const videoTitle = document.getElementById("videoTitle");
const channelLink = document.getElementById("channelLink");
const channelName = document.getElementById("channelName");
const uploadDate = document.getElementById("uploadDate");
const viewCount = document.getElementById("viewCount");
const originalVideoLink = document.getElementById("originalVideoLink");
const copyUrlBtn = document.getElementById("copyUrlBtn");
const videoDescription = document.getElementById("videoDescription");

// Grids & tabs
const videoOptionsGrid = document.getElementById("videoOptionsGrid");
const audioOptionsGrid = document.getElementById("audioOptionsGrid");
const subtitlesContent = document.getElementById("subtitlesContent");
const formatsTableBody = document.getElementById("formatsTableBody");

// Modal elements
const transcriptModal = document.getElementById("transcriptModal");
const modalBackdrop = document.getElementById("modalBackdrop");
const modalCloseBtn = document.getElementById("modalCloseBtn");
const modalTitle = document.getElementById("modalTitle");
const modalText = document.getElementById("modalText");
const modalLoading = document.getElementById("modalLoading");
const modalCopyBtn = document.getElementById("modalCopyBtn");
const modalDownloadBtn = document.getElementById("modalDownloadBtn");

// Toast
const toast = document.getElementById("toast");

/* -------------------------------------------------------------
 * 1. Health check & Initializer
 * ------------------------------------------------------------- */
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();
    serverStatusDot.className = "status-indicator online";
    let statusMsg = "Сервер онлайн";
    if (data.ffmpeg_available) statusMsg += " (FFmpeg)";
    if (data.cookies_configured) statusMsg += " • Cookies";
    if (data.proxy_configured) statusMsg += " • Прокси";
    if (data.rss_mb > 0) statusMsg += ` • RAM: ${data.rss_mb} МБ`;
    serverStatusText.textContent = statusMsg;
  } catch (err) {
    serverStatusDot.className = "status-indicator offline";
    serverStatusText.textContent = "Сервер недоступен";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  setupEventListeners();
});

/* -------------------------------------------------------------
 * 2. Event Listeners Setup
 * ------------------------------------------------------------- */
function setupEventListeners() {
  // Input clear / paste handlers
  urlInput.addEventListener("input", () => {
    if (urlInput.value.trim().length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    clearBtn.classList.add("hidden");
    urlInput.focus();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        clearBtn.classList.remove("hidden");
        urlInput.focus();
      }
    } catch (e) {
      showToast("Не удалось прочитать буфер обмена");
    }
  });

  // Sample chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const url = chip.getAttribute("data-url");
      urlInput.value = url;
      clearBtn.classList.remove("hidden");
      analyzeForm.dispatchEvent(new Event("submit"));
    });
  });

  // Form submit
  analyzeForm.addEventListener("submit", handleAnalyzeSubmit);

  // Alert close
  alertCloseBtn.addEventListener("click", hideAlert);

  // Copy video URL
  copyUrlBtn.addEventListener("click", () => {
    if (currentVideoData && currentVideoData.original_url) {
      navigator.clipboard.writeText(currentVideoData.original_url);
      showToast("Ссылка скопирована в буфер обмена!");
    }
  });

  // Tabs switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");
    });
  });

  // Modal actions
  modalCloseBtn.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  modalCopyBtn.addEventListener("click", () => {
    if (currentTranscriptText) {
      navigator.clipboard.writeText(currentTranscriptText);
      showToast("Текст расшифровки скопирован!");
    }
  });
}

/* -------------------------------------------------------------
 * 3. Video Analysis API
 * ------------------------------------------------------------- */
async function handleAnalyzeSubmit(e) {
  e.preventDefault();
  const rawUrl = urlInput.value.trim();
  if (!rawUrl) return;

  hideAlert();
  setLoading(true);
  resultSection.classList.add("hidden");
  skeletonLoader.classList.remove("hidden");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: rawUrl }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Произошла ошибка при анализе видео.");
    }

    currentVideoData = data;
    renderResults(data);
    resultSection.classList.remove("hidden");
  } catch (err) {
    showAlert("Ошибка анализа", err.message);
  } finally {
    setLoading(false);
    skeletonLoader.classList.add("hidden");
  }
}

/* -------------------------------------------------------------
 * 4. Render Results View
 * ------------------------------------------------------------- */
function renderResults(data) {
  // Video thumbnail & duration
  videoThumb.src = data.thumbnail || "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>";
  videoThumb.alt = data.title;
  videoDuration.textContent = data.duration_str;

  // Title & Channel
  videoTitle.textContent = data.title;
  channelName.textContent = data.channel;
  if (data.channel_url) {
    channelLink.href = data.channel_url;
    channelLink.style.display = "inline-flex";
  } else {
    channelLink.style.display = "none";
  }

  // Publish date & views
  uploadDate.textContent = data.upload_date ? `Опубликовано: ${data.upload_date}` : "Дата неизвестна";
  viewCount.textContent = data.view_count ? `${data.view_count.toLocaleString("ru-RU")} просмотров` : "— просмотров";

  // Original Link
  originalVideoLink.href = data.original_url;

  // Description
  videoDescription.textContent = data.description || "Описание отсутствует.";

  // 1. Render Video Options
  renderVideoOptions(data.video_options, data.original_url);

  // 2. Render Audio Options
  renderAudioOptions(data.audio_options, data.original_url);

  // 3. Render Subtitles Options
  renderSubtitlesOptions(data.subtitle_options, data.original_url);

  // 4. Render Raw Formats Table
  renderRawFormatsTable(data.all_formats);
}

function renderVideoOptions(options, url) {
  videoOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    videoOptionsGrid.innerHTML = `<p class="empty-msg">Варианты видео не найдены.</p>`;
    return;
  }

  options.forEach((opt) => {
    const card = document.createElement("div");
    card.className = "download-card";
    card.innerHTML = `
      <div class="download-card-header">
        <span class="card-quality-badge">${escapeHtml(opt.quality.toUpperCase())}</span>
        <span class="card-format-tag">${escapeHtml(opt.ext)}</span>
      </div>
      <div class="card-details">
        <span>${escapeHtml(opt.label)}</span>
        <span class="card-size">${escapeHtml(opt.filesize_str)}</span>
      </div>
      <button type="button" class="download-action-btn" data-url="${escapeHtml(opt.download_url)}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        <span>Скачать видео</span>
      </button>
    `;

    const btn = card.querySelector(".download-action-btn");
    btn.addEventListener("click", () => triggerDownload(btn, opt.download_url));

    videoOptionsGrid.appendChild(card);
  });
}

function renderAudioOptions(options, url) {
  audioOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    audioOptionsGrid.innerHTML = `<p class="empty-msg">Варианты аудио не найдены.</p>`;
    return;
  }

  options.forEach((opt) => {
    const card = document.createElement("div");
    card.className = "download-card";
    card.innerHTML = `
      <div class="download-card-header">
        <span class="card-quality-badge">${escapeHtml(opt.format.toUpperCase())}</span>
        <span class="card-format-tag">${opt.bitrate_kbps} kbps</span>
      </div>
      <div class="card-details">
        <span>${escapeHtml(opt.label)}</span>
        <span class="card-size">${escapeHtml(opt.filesize_str)}</span>
      </div>
      <button type="button" class="download-action-btn" data-url="${escapeHtml(opt.download_url)}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        <span>Скачать ${opt.format.toUpperCase()}</span>
      </button>
    `;

    const btn = card.querySelector(".download-action-btn");
    btn.addEventListener("click", () => triggerDownload(btn, opt.download_url));

    audioOptionsGrid.appendChild(card);
  });
}

function renderSubtitlesOptions(options, url) {
  if (!options || options.length === 0) {
    subtitlesContent.innerHTML = `
      <div class="subtitles-layout">
        <p class="empty-msg" style="color: var(--text-muted); padding: 12px 0;">
          ⚠️ Субтитры или автоматические расшифровки для этого видео отсутствуют на YouTube.
        </p>
      </div>
    `;
    return;
  }

  let selectOptions = options
    .map((sub, idx) => `<option value="${idx}">${escapeHtml(sub.name)} (${sub.lang})</option>`)
    .join("");

  subtitlesContent.innerHTML = `
    <div class="subtitles-layout">
      <div class="subtitles-controls">
        <div class="form-group" style="flex: 1; min-width: 220px;">
          <label class="form-label" for="subLangSelect">Языковая дорожка</label>
          <select id="subLangSelect" class="select-control">
            ${selectOptions}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Формат файла</label>
          <div class="format-radios">
            <label class="radio-chip">
              <input type="radio" name="subFormat" value="txt" checked>
              <span>Чистый текст (.txt)</span>
            </label>
            <label class="radio-chip">
              <input type="radio" name="subFormat" value="srt">
              <span>Субтитры с таймкодами (.srt)</span>
            </label>
          </div>
        </div>
      </div>

      <div class="subtitles-actions">
        <button type="button" id="downloadSubBtn" class="btn btn-primary">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Скачать файл
        </button>
        <button type="button" id="previewSubBtn" class="btn btn-secondary">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          Быстрый просмотр текста
        </button>
      </div>
    </div>
  `;

  const subSelect = document.getElementById("subLangSelect");
  const downloadSubBtn = document.getElementById("downloadSubBtn");
  const previewSubBtn = document.getElementById("previewSubBtn");

  downloadSubBtn.addEventListener("click", () => {
    const selectedIdx = parseInt(subSelect.value, 10);
    const sub = options[selectedIdx];
    const fmt = document.querySelector('input[name="subFormat"]:checked').value;
    const downloadUrl = fmt === "txt" ? sub.txt_url : sub.srt_url;
    triggerDownload(downloadSubBtn, downloadUrl);
  });

  previewSubBtn.addEventListener("click", () => {
    const selectedIdx = parseInt(subSelect.value, 10);
    const sub = options[selectedIdx];
    openTranscriptModal(sub);
  });
}

function renderRawFormatsTable(formats) {
  formatsTableBody.innerHTML = "";
  if (!formats || formats.length === 0) {
    formatsTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center;">Форматы не найдены</td></tr>`;
    return;
  }

  formats.forEach((f) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${escapeHtml(f.format_id)}</code></td>
      <td><strong>${escapeHtml(f.ext)}</strong></td>
      <td>${escapeHtml(f.resolution)}</td>
      <td>${f.fps ? f.fps : "—"}</td>
      <td>${escapeHtml(f.filesize_str)}</td>
      <td><code>${escapeHtml(f.vcodec || "none")}</code></td>
      <td><code>${escapeHtml(f.acodec || "none")}</code></td>
      <td>${escapeHtml(f.note || "—")}</td>
    `;
    formatsTableBody.appendChild(tr);
  });
}

/* -------------------------------------------------------------
 * 5. Download Streaming Handler
 * ------------------------------------------------------------- */
async function triggerDownload(btn, url) {
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `
    <div class="spinner" style="width:14px;height:14px;"></div>
    <span>Проверка...</span>
  `;

  try {
    // 1. Parse target download URL parameters for pre-flight check
    const urlObj = new URL(url, window.location.origin);
    const ytUrl = urlObj.searchParams.get("url");
    let kind = "video";
    if (url.includes("/api/download/audio")) kind = "audio";
    else if (url.includes("/api/download/transcript")) kind = "transcript";

    const checkParams = new URLSearchParams({ url: ytUrl, kind });
    const quality = urlObj.searchParams.get("quality");
    const format = urlObj.searchParams.get("format");
    const lang = urlObj.searchParams.get("lang");
    if (quality) checkParams.set("quality", quality);
    if (format) checkParams.set("format", format);
    if (lang) checkParams.set("lang", lang);

    // 2. Perform pre-check on backend (concurrency, limits, ffmpeg, video availability)
    const checkRes = await fetch("/api/check-download?" + checkParams.toString());
    if (!checkRes.ok) {
      let errorDetail = "Ошибка при проверке возможности скачивания";
      try {
        const errJson = await checkRes.json();
        errorDetail = errJson.detail || errorDetail;
      } catch (e) {
        errorDetail = `Ошибка сервера (${checkRes.status})`;
      }
      showAlert("Невозможно начать скачивание", errorDetail);
      return;
    }

    let downloadFilename = "download";
    try {
      const checkData = await checkRes.json();
      if (checkData.title) {
        const ext = kind === "audio" ? (format || "mp3") : (kind === "transcript" ? (lang ? `${lang}.${format || "txt"}` : (format || "txt")) : "mp4");
        downloadFilename = `${checkData.title}.${ext}`;
      }
    } catch (e) {
      // ignore JSON parse if empty
    }

    // 3. Pre-check succeeded: trigger native direct streaming download via <a> tag.
    // Avoids buffering multi-hundred MB into browser V8 JS heap (prevents browser tab OOM crashes).
    showToast("Сервер готовит поток. Файл сохраняется напрямую браузером...");
    const a = document.createElement("a");
    a.href = url;
    a.setAttribute("download", downloadFilename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (err) {
    showAlert("Ошибка сети", `Не удалось выполнить проверку или начать загрузку: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

/* -------------------------------------------------------------
 * 6. Transcript Preview Modal
 * ------------------------------------------------------------- */
async function openTranscriptModal(subOption) {
  transcriptModal.classList.remove("hidden");
  modalTitle.textContent = `Транскрипт: ${subOption.name}`;
  modalText.textContent = "";
  modalLoading.classList.remove("hidden");
  currentTranscriptText = "";

  try {
    const res = await fetch(subOption.txt_url);
    if (!res.ok) throw new Error("Не удалось загрузить текст субтитров");
    const text = await res.text();
    currentTranscriptText = text;
    modalText.textContent = text || "(Субтитры пусты)";
  } catch (err) {
    modalText.textContent = `Ошибка: ${err.message}`;
  } finally {
    modalLoading.classList.add("hidden");
  }

  modalDownloadBtn.onclick = () => {
    triggerDownload(modalDownloadBtn, subOption.txt_url);
  };
}

function closeModal() {
  transcriptModal.classList.add("hidden");
}

/* -------------------------------------------------------------
 * 7. Helpers & UI Feedback
 * ------------------------------------------------------------- */
function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  urlInput.disabled = isLoading;
  const btnText = submitBtn.querySelector(".btn-text");
  if (isLoading) {
    btnText.textContent = "Анализирую...";
    submitSpinner.classList.remove("hidden");
  } else {
    btnText.textContent = "Анализировать";
    submitSpinner.classList.add("hidden");
  }
}

function showAlert(title, desc) {
  alertTitle.textContent = title;
  alertDesc.textContent = desc;
  alertBox.classList.remove("hidden");
  alertBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function hideAlert() {
  alertBox.classList.add("hidden");
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
