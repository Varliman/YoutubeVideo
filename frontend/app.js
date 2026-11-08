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
 * 1. Health check & Keep-Alive Initializer (Render Free Spin-Down Guard)
 * ------------------------------------------------------------- */
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();
    serverStatusDot.className = "status-indicator online";
    let statusMsg = "Сервер онлайн";
    if (data.ffmpeg_available) statusMsg += " (FFmpeg";
    if (data.nodejs_available && data.ffmpeg_available) statusMsg += "+JS)";
    else if (data.ffmpeg_available) statusMsg += ")";
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
  // Periodic health check every 4 minutes while tab is open to prevent Render Free spin-down
  setInterval(checkHealth, 240000);
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
    } catch (err) {
      showToast("Не удалось прочитать буфер обмена");
    }
  });

  // Alert close
  alertCloseBtn.addEventListener("click", hideAlert);

  // Form submission
  analyzeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;
    await performAnalysis(url);
  });

  // Tabs switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");
    });
  });

  // Modal actions
  modalCloseBtn.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !transcriptModal.classList.contains("hidden")) {
      closeModal();
    }
  });

  modalCopyBtn.addEventListener("click", () => {
    if (currentTranscriptText) {
      navigator.clipboard.writeText(currentTranscriptText);
      showToast("Текст расшифровки скопирован в буфер обмена!");
    }
  });

  // Copy video URL button
  copyUrlBtn.addEventListener("click", () => {
    if (currentVideoData && currentVideoData.original_url) {
      navigator.clipboard.writeText(currentVideoData.original_url);
      showToast("Ссылка на видео скопирована в буфер!");
    }
  });
}

/* -------------------------------------------------------------
 * 3. Main Video Analysis
 * ------------------------------------------------------------- */
async function performAnalysis(url) {
  hideAlert();
  setLoading(true);
  resultSection.classList.add("hidden");
  skeletonLoader.classList.remove("hidden");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      let errorMsg = "Не удалось проанализировать видео";
      try {
        const errorData = await res.json();
        errorMsg = errorData.detail || errorMsg;
      } catch (e) {
        errorMsg = `Ошибка сервера (${res.status} ${res.statusText})`;
      }
      showAlert("Ошибка анализа", errorMsg);
      return;
    }

    const data = await res.json();
    currentVideoData = data;
    renderResults(data);
    checkHealth();
  } catch (err) {
    showAlert("Ошибка сети", `Не удалось связаться с сервером: ${err.message}`);
  } finally {
    setLoading(false);
    skeletonLoader.classList.add("hidden");
  }
}

/* -------------------------------------------------------------
 * 4. Render UI Components
 * ------------------------------------------------------------- */
function renderResults(data) {
  // Populate video details
  videoThumb.src = data.thumbnail || "";
  videoThumb.alt = data.title;
  videoDuration.textContent = data.duration_str;
  videoTitle.textContent = data.title;

  channelName.textContent = data.channel;
  if (data.channel_url) {
    channelLink.href = data.channel_url;
    channelLink.classList.remove("hidden");
  } else {
    channelLink.classList.add("hidden");
  }

  uploadDate.textContent = data.upload_date || "Не указана";
  viewCount.textContent =
    data.view_count !== null && data.view_count !== undefined
      ? data.view_count.toLocaleString("ru-RU")
      : "Скрыто";
  originalVideoLink.href = data.original_url;
  videoDescription.textContent = data.description || "Описание отсутствует.";

  // Render tabs
  renderVideoOptions(data.video_options);
  renderAudioOptions(data.audio_options);
  renderSubtitles(data.subtitle_options);
  renderFormatsTable(data.all_formats);

  // Reveal result
  resultSection.classList.remove("hidden");
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderVideoOptions(options) {
  videoOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    videoOptionsGrid.innerHTML = "<p class='text-muted'>Доступные видеопотоки не найдены.</p>";
    return;
  }

  options.forEach((opt) => {
    const isAvailable = opt.available !== false;
    const card = document.createElement("div");
    card.className = "option-card";
    card.innerHTML = `
      <div class="option-header">
        <span class="option-badge">${escapeHtml(opt.quality)}</span>
        <span class="option-size">${isAvailable ? "~" : ""}${escapeHtml(opt.filesize_str)}</span>
      </div>
      <div class="option-title">${escapeHtml(opt.label)}</div>
      <button type="button" class="download-stream-btn" data-url="${escapeHtml(opt.download_url)}" ${!isAvailable ? "disabled" : ""}>
        <span>${isAvailable ? "Скачать MP4" : "Недоступно"}</span>
      </button>
    `;

    if (isAvailable) {
      card.querySelector(".download-stream-btn").addEventListener("click", function () {
        triggerDownload(this, opt.download_url);
      });
    }

    videoOptionsGrid.appendChild(card);
  });
}

function renderAudioOptions(options) {
  audioOptionsGrid.innerHTML = "";
  if (!options || options.length === 0) {
    audioOptionsGrid.innerHTML = "<p class='text-muted'>Доступные аудиопотоки не найдены.</p>";
    return;
  }

  options.forEach((opt) => {
    const isAvailable = opt.available !== false;
    const card = document.createElement("div");
    card.className = "option-card";
    card.innerHTML = `
      <div class="option-header">
        <span class="option-badge">${escapeHtml(opt.format.toUpperCase())}</span>
        <span class="option-size">~${escapeHtml(opt.filesize_str)}</span>
      </div>
      <div class="option-title">${escapeHtml(opt.label)}</div>
      <button type="button" class="download-stream-btn" data-url="${escapeHtml(opt.download_url)}" ${!isAvailable ? "disabled" : ""}>
        <span>${isAvailable ? "Скачать " + escapeHtml(opt.format.toUpperCase()) : "Требуется FFmpeg"}</span>
      </button>
    `;

    if (isAvailable) {
      card.querySelector(".download-stream-btn").addEventListener("click", function () {
        triggerDownload(this, opt.download_url);
      });
    }

    audioOptionsGrid.appendChild(card);
  });
}

function renderSubtitles(subtitles) {
  subtitlesContent.innerHTML = "";
  if (!subtitles || subtitles.length === 0) {
    subtitlesContent.innerHTML = `
      <div class="alert-box" style="margin-top:0;">
        <span class="alert-icon">ℹ️</span>
        <div class="alert-content">
          <p class="alert-desc">Для данного видео не найдено ручных или автоматически сгенерированных субтитров.</p>
        </div>
      </div>
    `;
    return;
  }

  subtitles.forEach((sub) => {
    const item = document.createElement("div");
    item.className = "subtitle-item";
    item.innerHTML = `
      <div class="subtitle-lang-info">
        <span class="option-badge">${escapeHtml(sub.lang)}</span>
        <span><strong>${escapeHtml(sub.name)}</strong></span>
      </div>
      <div class="subtitle-actions">
        <button type="button" class="btn btn-secondary preview-sub-btn">
          <span>Предпросмотр</span>
        </button>
        <button type="button" class="btn btn-primary download-txt-btn">
          <span>Скачать .txt</span>
        </button>
        <button type="button" class="btn btn-secondary download-srt-btn">
          <span>Скачать .srt</span>
        </button>
      </div>
    `;

    item.querySelector(".preview-sub-btn").addEventListener("click", () => {
      openTranscriptModal(sub);
    });

    item.querySelector(".download-txt-btn").addEventListener("click", function () {
      triggerDownload(this, sub.txt_url);
    });

    item.querySelector(".download-srt-btn").addEventListener("click", function () {
      triggerDownload(this, sub.srt_url);
    });

    subtitlesContent.appendChild(item);
  });
}

function renderFormatsTable(formats) {
  formatsTableBody.innerHTML = "";
  if (!formats || formats.length === 0) {
    formatsTableBody.innerHTML = "<tr><td colspan='8'>Информация о форматах отсутствует</td></tr>";
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
 * 5. Two-Phase Download Streaming Handler (Zero Browser Error Pages)
 * ------------------------------------------------------------- */
async function triggerDownload(btn, url) {
  hideAlert();
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `
    <div class="spinner" style="width:14px;height:14px;"></div>
    <span>Готовим файл...</span>
  `;

  try {
    // 1. Parse target download URL parameters
    const urlObj = new URL(url, window.location.origin);
    const ytUrl = urlObj.searchParams.get("url");
    let kind = "video";
    if (url.includes("/api/download/audio")) kind = "audio";
    else if (url.includes("/api/download/transcript")) kind = "transcript";

    const prepParams = new URLSearchParams({ url: ytUrl, kind });
    const quality = urlObj.searchParams.get("quality");
    const format = urlObj.searchParams.get("format");
    const lang = urlObj.searchParams.get("lang");
    if (quality) prepParams.set("quality", quality);
    if (format) prepParams.set("format", format);
    if (lang) prepParams.set("lang", lang);

    // 2. Prepare file on server via fetch() so any YouTube/yt-dlp errors are caught
    // cleanly as JSON and shown in the UI AlertBox instead of crashing Firefox into a 400/404 page.
    const prepRes = await fetch("/api/prepare-download?" + prepParams.toString());
    if (!prepRes.ok) {
      let errorDetail = "Ошибка при подготовке файла на сервере";
      try {
        const errJson = await prepRes.json();
        errorDetail = errJson.detail || errorDetail;
      } catch (e) {
        errorDetail = `Ошибка сервера (${prepRes.status})`;
      }
      showAlert("Не удалось скачать файл", errorDetail);
      return;
    }

    const prepData = await prepRes.json();
    const streamUrl = prepData.stream_url;
    const downloadFilename = prepData.filename || "download";

    // 3. File is guaranteed ready on disk: trigger native browser download via <a href="/api/stream/{token}">.
    // Avoids buffering large files in browser JS heap while guaranteeing zero 400/404 navigation errors.
    showToast("Файл готов! Начинается сохранение в браузере...");
    const a = document.createElement("a");
    a.href = streamUrl;
    a.setAttribute("download", downloadFilename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    checkHealth();
  } catch (err) {
    showAlert("Ошибка сети", `Не удалось подготовить или начать загрузку: ${err.message}`);
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
  modalText.value = "";
  modalLoading.classList.remove("hidden");
  currentTranscriptText = "";

  try {
    const res = await fetch(subOption.txt_url);
    if (!res.ok) {
      let detail = "Не удалось загрузить текст субтитров";
      try {
        const errData = await res.json();
        detail = errData.detail || detail;
      } catch (e) {
        detail = `Ошибка сервера (${res.status})`;
      }
      throw new Error(detail);
    }
    const text = await res.text();
    currentTranscriptText = text;
    modalText.value = text || "(Субтитры пусты)";
  } catch (err) {
    modalText.value = `Ошибка: ${err.message}`;
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
