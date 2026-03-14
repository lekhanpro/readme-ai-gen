/* ===== DOM REFS ===== */
const form = document.getElementById("generator-form");
const output = document.getElementById("markdown-output");
const previewSurface = document.getElementById("preview-surface");
const statusPill = document.getElementById("status-pill");
const errorBox = document.getElementById("error-box");
const summaryGrid = document.getElementById("summary-grid");
const selectionBoard = document.getElementById("selection-board");
const providerHealth = document.getElementById("provider-health");
const copyButton = document.getElementById("copy-button");
const downloadButton = document.getElementById("download-button");
const submitButton = document.getElementById("submit-button");
const colorInput = document.getElementById("color");
const customColorInput = document.getElementById("custom-color");
const modeInput = document.getElementById("mode");
const providerInput = document.getElementById("llm");
const repoUrlInput = document.getElementById("repo-url");
const toneInput = document.getElementById("tone");
const outputLengthInput = document.getElementById("output_length");
const headerTypeInput = document.getElementById("header_type");
const lineCountEl = document.getElementById("line-count");
const outputPanes = document.getElementById("output-panes");

const sectionChips = [...document.querySelectorAll(".section-chip")];
const previewTabs = [...document.querySelectorAll(".otab")];
const previewPanes = [...document.querySelectorAll(".output-pane")];
const presetButtons = [...document.querySelectorAll(".preset-button")];
const settingsTabs = [...document.querySelectorAll(".stab")];
const settingsPanes = [...document.querySelectorAll(".stab-pane")];

/* ===== CONSTANTS ===== */
const PROFILE_SECTIONS = [
  "typing", "badges", "snake", "about", "ventures", "opensource",
  "tech", "stats", "contrib_graph", "trophies", "quote", "social",
];

const PROJECT_SECTIONS = [
  "typing", "badges", "about", "features", "install", "usage",
  "tree", "tech", "contribute",
];

const SECTION_PRESETS = {
  profile: {
    minimal: ["typing", "badges", "about", "tech", "social"],
    showcase: ["typing", "badges", "snake", "about", "tech", "stats", "trophies", "social"],
    full: PROFILE_SECTIONS,
  },
  project: {
    minimal: ["typing", "badges", "about", "install", "usage", "tech"],
    showcase: ["typing", "badges", "about", "features", "install", "usage", "tech", "tree"],
    full: PROJECT_SECTIONS,
  },
};

let latestMarkdown = "";
let currentViewMode = "markdown";

/* ===== SETTINGS TABS ===== */
settingsTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    settingsTabs.forEach((t) => t.classList.toggle("active", t === tab));
    settingsPanes.forEach((p) => {
      p.classList.toggle("is-hidden", p.dataset.stabPane !== tab.dataset.stab);
    });
  });
});

/* ===== HELPERS ===== */
function setStatus(state, text) {
  statusPill.className = `status-pill ${state}`;
  statusPill.textContent = text;
}

function setSummary(data = {}) {
  if (!summaryGrid) return;
  const { mode = "Waiting", identity = "—", languages = "—", stats = "—", lines = "0 lines" } = data;
  summaryGrid.innerHTML = `
    <article><span>Mode</span><strong>${mode}</strong></article>
    <article><span>Identity</span><strong>${identity}</strong></article>
    <article><span>Languages</span><strong>${languages}</strong></article>
    <article><span>Output</span><strong>${lines}<br/>${stats}</strong></article>
  `;
}

function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function enableActions(enabled) {
  copyButton.disabled = !enabled;
  downloadButton.disabled = !enabled;
}

function updateLineCount() {
  const lines = latestMarkdown ? latestMarkdown.split("\n").length : 0;
  const words = latestMarkdown ? latestMarkdown.trim().split(/\s+/).filter(Boolean).length : 0;
  lineCountEl.textContent = `${lines} lines · ${words} words`;
}

function setSubmitLoading(loading) {
  const label = submitButton.querySelector(".btn-label");
  const spinner = submitButton.querySelector(".btn-spinner");
  if (loading) {
    label.textContent = "Generating...";
    spinner.hidden = false;
    submitButton.disabled = true;
  } else {
    label.textContent = "Generate";
    spinner.hidden = true;
    submitButton.disabled = false;
  }
}

/* ===== SEGMENTED CONTROLS ===== */
function setActiveSegment(target, value) {
  document.querySelectorAll(`[data-target="${target}"]`).forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.value === value);
  });
}

function setActiveTheme(value) {
  document.querySelectorAll(".color-dot").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.color === value.toUpperCase());
  });
}

/* ===== OUTPUT VIEW SWITCHING ===== */
function setOutputView(mode) {
  currentViewMode = mode;
  previewTabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === mode));

  if (mode === "split") {
    outputPanes.classList.add("split-mode");
    previewPanes.forEach((p) => p.classList.remove("is-hidden"));
  } else {
    outputPanes.classList.remove("split-mode");
    previewPanes.forEach((p) => {
      p.classList.toggle("is-hidden", p.dataset.pane !== mode);
    });
  }
}

function setActivePreset(preset) {
  presetButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.preset === preset);
  });
}

/* ===== MODE / URL INFERENCE ===== */
function inferModeFromUrl(url) {
  try {
    const parsed = new URL(url.trim());
    if (!["github.com", "www.github.com"].includes(parsed.hostname)) return "profile";
    const parts = parsed.pathname.split("/").filter(Boolean);
    return parts.length >= 2 ? "project" : "profile";
  } catch {
    return "profile";
  }
}

function resolveEffectiveMode() {
  return modeInput.value === "auto" ? inferModeFromUrl(repoUrlInput.value) : modeInput.value;
}

function getDefaultSections(mode) {
  if (mode === "profile") return PROFILE_SECTIONS;
  if (mode === "project") return PROJECT_SECTIONS;
  return [...new Set([...PROFILE_SECTIONS, ...PROJECT_SECTIONS])];
}

function normalizeHex(value) {
  const n = value.trim().replace(/^#/, "").toUpperCase();
  return /^[0-9A-F]{6}$/.test(n) ? n : null;
}

/* ===== SECTIONS ===== */
function syncSectionVisibility(mode) {
  const eff = mode === "auto" ? resolveEffectiveMode() : mode;
  const defaults = new Set(getDefaultSections(eff));

  sectionChips.forEach((chip) => {
    const cb = chip.querySelector("input");
    const allowed = chip.dataset.modes === "all" || chip.dataset.modes === eff;
    chip.classList.toggle("is-disabled", !allowed);
    cb.disabled = !allowed;
    if (!allowed) { cb.checked = false; return; }
    if (!cb.dataset.userTouched) cb.checked = defaults.has(cb.value);
  });
}

function getSelectedSections() {
  return sectionChips
    .map((c) => c.querySelector("input"))
    .filter((cb) => cb.checked && !cb.disabled)
    .map((cb) => cb.value);
}

function applySectionPreset(preset) {
  const eff = resolveEffectiveMode();
  const vals = new Set(SECTION_PRESETS[eff]?.[preset] || getDefaultSections(eff));

  sectionChips.forEach((chip) => {
    const cb = chip.querySelector("input");
    const allowed = chip.dataset.modes === "all" || chip.dataset.modes === eff;
    cb.dataset.userTouched = "true";
    cb.disabled = !allowed;
    chip.classList.toggle("is-disabled", !allowed);
    cb.checked = allowed && vals.has(cb.value);
  });

  setActivePreset(preset);
  updateSelectionBoard();
}

function updateSelectionBoard() {
  if (!selectionBoard) return;
  const sections = getSelectedSections();
  const preset = document.querySelector(".preset-button.active")?.dataset.preset || "showcase";
  selectionBoard.innerHTML = [
    `Mode: ${resolveEffectiveMode()}`, `Provider: ${providerInput.value}`,
    `Preset: ${preset}`, `Density: ${outputLengthInput.value}`,
    `Tone: ${toneInput.options[toneInput.selectedIndex].text}`,
    `Header: ${headerTypeInput.value}`, `Accent: #${colorInput.value}`,
    `Sections: ${sections.length}`,
  ].map((l) => `<span>${l}</span>`).join("");
}

/* ===== PAYLOAD ===== */
function getPayload() {
  const fd = new FormData(form);
  const payload = Object.fromEntries(fd.entries());
  payload.sections = getSelectedSections();
  if (!payload.icons || !payload.icons.trim()) delete payload.icons;
  return payload;
}

/* ===== RENDER PREVIEW ===== */
function renderPreview(markdown) {
  if (!markdown || !markdown.trim()) {
    previewSurface.innerHTML = '<p style="color:var(--text-dim);">Generate a README to see the preview.</p>';
    return;
  }

  if (window.marked) {
    const raw = window.marked.parse(markdown, { breaks: true, gfm: true });
    previewSurface.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(raw) : raw;
  } else {
    previewSurface.innerHTML = `<pre>${markdown.replace(/[&<>]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}</pre>`;
  }
}

/* ===== PROVIDER HEALTH ===== */
async function loadProviderHealth() {
  try {
    const res = await fetch("/api/generate");
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error();

    const providers = data.providers || {};
    providerHealth.innerHTML = ["nvidia", "groq", "gemini", "openai"]
      .map((n) => {
        const on = Boolean(providers[n]);
        return `<span class="health-chip ${on ? "online" : "offline"}">${n} ${on ? "ready" : "—"}</span>`;
      }).join("");
  } catch {
    providerHealth.innerHTML = '<span class="health-chip offline">Providers unavailable</span>';
  }
}

/* ===== GENERATE ===== */
async function generateReadme(event) {
  event.preventDefault();
  clearError();
  setStatus("loading", "Generating...");
  setSubmitLoading(true);
  enableActions(false);

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getPayload()),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || "Generation failed.");

    latestMarkdown = data.markdown;
    output.value = latestMarkdown;
    renderPreview(latestMarkdown);
    updateLineCount();

    setSummary({
      mode: data.mode === "project" ? "Project README" : "Profile README",
      identity: data.repo ? `${data.displayName} / ${data.repo}` : `${data.displayName} (@${data.username})`,
      languages: data.summary.languages.length ? data.summary.languages.join(", ") : "—",
      stats: `repos ${data.summary.repos} | followers ${data.summary.followers} | stars ${data.summary.stars}`,
      lines: `${data.lineCount} lines`,
    });

    setStatus("success", "Done");
    enableActions(true);

    // Auto-switch to split view after generation
    setOutputView("split");
  } catch (err) {
    setStatus("error", "Failed");
    showError(err.message || "Something went wrong.");
  } finally {
    setSubmitLoading(false);
  }
}

/* ===== EVENT LISTENERS ===== */
form.addEventListener("submit", generateReadme);

// Ctrl+Enter to generate
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    if (!submitButton.disabled) form.requestSubmit();
  }
});

// Segmented buttons
[...document.querySelectorAll(".seg[data-target]")].forEach((btn) => {
  btn.addEventListener("click", () => {
    const { target, value } = btn.dataset;
    document.getElementById(target).value = value;
    setActiveSegment(target, value);
    if (target === "mode") {
      syncSectionVisibility(value);
      applySectionPreset(document.querySelector(".preset-button.active")?.dataset.preset || "showcase");
    }
    updateSelectionBoard();
  });
});

// Color dots
[...document.querySelectorAll(".color-dot")].forEach((dot) => {
  dot.addEventListener("click", () => {
    colorInput.value = dot.dataset.color;
    customColorInput.value = `#${dot.dataset.color}`;
    setActiveTheme(dot.dataset.color);
    updateSelectionBoard();
  });
});

customColorInput.addEventListener("input", () => {
  const hex = normalizeHex(customColorInput.value);
  if (!hex) return;
  colorInput.value = hex;
  setActiveTheme(hex);
  updateSelectionBoard();
});

repoUrlInput.addEventListener("input", () => {
  if (modeInput.value === "auto") {
    syncSectionVisibility("auto");
    applySectionPreset(document.querySelector(".preset-button.active")?.dataset.preset || "showcase");
  }
  updateSelectionBoard();
});

sectionChips.forEach((chip) => {
  chip.querySelector("input").addEventListener("change", function () {
    this.dataset.userTouched = "true";
    updateSelectionBoard();
  });
});

presetButtons.forEach((btn) => {
  btn.addEventListener("click", () => applySectionPreset(btn.dataset.preset));
});

// Sample buttons
[...document.querySelectorAll(".sample-button")].forEach((btn) => {
  btn.addEventListener("click", () => {
    repoUrlInput.value = btn.dataset.sample;
    if (btn.dataset.mode) {
      modeInput.value = btn.dataset.mode;
      setActiveSegment("mode", btn.dataset.mode);
    }
    syncSectionVisibility(modeInput.value);
    applySectionPreset(document.querySelector(".preset-button.active")?.dataset.preset || "showcase");
    updateSelectionBoard();
    repoUrlInput.focus();
  });
});

[toneInput, outputLengthInput, headerTypeInput].forEach((el) => {
  el.addEventListener("change", updateSelectionBoard);
});

// Output tabs (markdown / preview / split)
previewTabs.forEach((tab) => {
  tab.addEventListener("click", () => setOutputView(tab.dataset.tab));
});

// Live edit → re-render
output.addEventListener("input", () => {
  latestMarkdown = output.value;
  renderPreview(latestMarkdown);
  updateLineCount();
});

// Copy
copyButton.addEventListener("click", async () => {
  if (!latestMarkdown) return;
  try {
    await navigator.clipboard.writeText(latestMarkdown);
    const orig = copyButton.innerHTML;
    copyButton.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
    setStatus("success", "Copied");
    setTimeout(() => { copyButton.innerHTML = orig; }, 2000);
  } catch {
    setStatus("error", "Copy failed");
  }
});

// Download
downloadButton.addEventListener("click", () => {
  if (!latestMarkdown) return;
  const blob = new Blob([latestMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "README.md";
  a.click();
  URL.revokeObjectURL(url);
});

/* ===== INIT ===== */
latestMarkdown = [
  "# README Preview",
  "",
  "Paste a GitHub profile or repository URL above and hit **Generate** (or press `Ctrl+Enter`).",
  "",
  "- Switch between **Markdown**, **Preview**, and **Split** view",
  "- Apply minimal, showcase, or full section presets",
  "- Customize colors, headers, animations, badges, and more",
].join("\n");

output.value = latestMarkdown;
customColorInput.value = `#${colorInput.value}`;
renderPreview(latestMarkdown);
updateLineCount();
setSummary();
setStatus("idle", "Idle");
setActiveTheme(colorInput.value);
setActiveSegment("mode", modeInput.value);
setActiveSegment("llm", providerInput.value);
setOutputView("markdown");
syncSectionVisibility(modeInput.value);
applySectionPreset("showcase");
updateSelectionBoard();
loadProviderHealth();
