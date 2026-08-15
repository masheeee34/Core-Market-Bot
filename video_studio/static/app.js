let currentSourceTab = "upload";
let selectedFile = null;

function switchSourceTab(tab) {
  currentSourceTab = tab;
  document.getElementById("tabUploadBtn").classList.toggle("active", tab === "upload");
  document.getElementById("tabYtBtn").classList.toggle("active", tab === "youtube");
  document.getElementById("sourceUploadSection").style.display = tab === "upload" ? "block" : "none";
  document.getElementById("sourceYtSection").style.display = tab === "youtube" ? "block" : "none";
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    selectedFile = file;
    document.getElementById("dropzoneLabel").textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
  }
}

// Setup Drag & Drop
const dropzone = document.getElementById("dropzone");
if (dropzone) {
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      selectedFile = e.dataTransfer.files[0];
      document.getElementById("dropzoneLabel").textContent = `Selected: ${selectedFile.name} (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB)`;
    }
  });
}

function toggleModeSettings() {
  const mode = document.getElementById("renderMode").value;
  // Can adjust UI if needed
}

async function startGeneration() {
  const btn = document.getElementById("generateBtn");
  const progressContainer = document.getElementById("progressContainer");
  const progressFill = document.getElementById("progressBarFill");
  const progressText = document.getElementById("progressText");
  const progressPercent = document.getElementById("progressPercent");

  const ytUrl = document.getElementById("ytUrl").value.trim();
  if (currentSourceTab === "upload" && !selectedFile) {
    alert("Please select or drop a video file first!");
    return;
  }
  if (currentSourceTab === "youtube" && !ytUrl) {
    alert("Please enter a valid YouTube URL!");
    return;
  }

  btn.disabled = true;
  progressContainer.style.display = "flex";
  progressFill.style.width = "15%";
  progressText.textContent = "Uploading & Preparing Video...";
  progressPercent.textContent = "15%";

  const formData = new FormData();
  if (currentSourceTab === "upload") {
    formData.append("file", selectedFile);
  } else {
    formData.append("youtube_url", ytUrl);
  }

  formData.append("mode", document.getElementById("renderMode").value);
  formData.append("script", document.getElementById("voiceScript").value);
  formData.append("voice", document.getElementById("voiceSelect").value);
  formData.append("sub_style", document.getElementById("subStyleSelect").value);
  formData.append("top_banner", document.getElementById("topBannerText").value);
  formData.append("bottom_cta", document.getElementById("bottomCtaText").value);

  try {
    progressFill.style.width = "45%";
    progressText.textContent = "Processing with RTX 3050 NVENC & AI Voice...";
    progressPercent.textContent = "45%";

    const res = await fetch("/api/generate", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (data.success) {
      progressFill.style.width = "100%";
      progressText.textContent = "Generation Complete! 🎉";
      progressPercent.textContent = "100%";
      setTimeout(() => {
        progressContainer.style.display = "none";
        loadClipsGallery();
      }, 1500);
    } else {
      alert("Error: " + (data.error || "Failed to generate video."));
      progressContainer.style.display = "none";
    }
  } catch (err) {
    alert("Generation failed: " + err.message);
    progressContainer.style.display = "none";
  } finally {
    btn.disabled = false;
  }
}

async function loadClipsGallery() {
  const gallery = document.getElementById("clipsGallery");
  try {
    const res = await fetch("/api/clips");
    const clips = await res.json();

    if (!clips || clips.length === 0) {
      gallery.innerHTML = `
        <div style="color: var(--text-muted); font-size: 14px; text-align: center; grid-column: 1 / -1; padding: 40px;">
          No generated clips yet. Upload a video or enter a YouTube URL to start creating! 🎬
        </div>
      `;
      return;
    }

    gallery.innerHTML = clips.map((clip) => `
      <div class="clip-card">
        <div class="clip-video-container">
          <video controls preload="metadata" src="/output/${encodeURIComponent(clip.filename)}"></video>
        </div>
        <div class="clip-body">
          <div class="clip-title">${escapeHtml(clip.meta.title)}</div>
          
          <div class="clip-meta-box">
            <div><strong>⏰ Best Posting Time:</strong> <span style="color: var(--primary-cyan); font-weight: 600;">${escapeHtml(clip.meta.optimal_time)}</span></div>
            <div><strong>🏷️ Hashtags:</strong> ${escapeHtml(clip.meta.hashtags_string)}</div>
            <div><strong>📌 Pinned Comment:</strong> <em>"${escapeHtml(clip.meta.pinned_comment)}"</em></div>
          </div>

          <div class="clip-actions">
            <a href="/output/${encodeURIComponent(clip.filename)}" download class="btn-primary" style="flex: 1; padding: 10px; font-size: 13px; text-decoration: none;">
              📥 Download MP4
            </a>
            <button class="btn-secondary" onclick="copyToClipboard('${escapeJs(clip.meta.title + '\n\n' + clip.meta.hashtags_string)}')">
              📋 Copy Post
            </button>
            <button class="btn-secondary" onclick="copyToClipboard('${escapeJs(clip.meta.pinned_comment)}')">
              📌 Copy Comment
            </button>
          </div>
        </div>
      </div>
    `).join("");
  } catch (e) {
    console.error("Error loading gallery:", e);
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escapeJs(text) {
  if (!text) return "";
  return text.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\n/g, "\\n");
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert("Copied to clipboard! 📋");
  });
}

// Initial load
document.addEventListener("DOMContentLoaded", () => {
  loadClipsGallery();
});
