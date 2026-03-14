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
const sectionChips = [...document.querySelectorAll(".section-chip")];
const previewTabs = [...document.querySelectorAll(".preview-tab")];
const previewPanes = [...document.querySelectorAll(".preview-pane")];
const presetButtons = [...document.querySelectorAll(".preset-button")];

const PROFILE_SECTIONS = [
  "typing",
  "badges",
  "snake",
  "about",
  "ventures",
  "opensource",
  "tech",
  "stats",
  "contrib_graph",
  "trophies",
  "quote",
  "social",
];

const PROJECT_SECTIONS = [
  "typing",
  "badges",
  "about",
  "features",
  "install",
  "usage",
  "tree",
  "tech",
  "contribute",
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

function setStatus(state, text) {
  statusPill.className = `status-pill ${state}`;
  statusPill.textContent = text;
}

function setSummary({
  mode = "Waiting",
  identity = "Paste a GitHub URL",
  languages = "Detected after fetch",
  stats = "No data yet",
  lines = "0 lines",
} = {}) {
  summaryGrid.innerHTML = `
    <article>
      <span>Mode</span>
      <strong>${mode}</strong>
    </article>
    <article>
      <span>Identity</span>
      <strong>${identity}</strong>
    </article>
    <article>
      <span>Languages</span>
      <strong>${languages}</strong>
    </article>
    <article>
      <span>Output</span>
      <strong>${lines}<br />${stats}</strong>
    </article>
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

function setActiveSegment(target, value) {
  document.querySelectorAll(`[data-target="${target}"]`).forEach((button) => {
    button.classList.toggle("active", button.dataset.value === value);
  });
}

function setActiveTheme(value) {
  document.querySelectorAll(".palette-tile").forEach((button) => {
    button.classList.toggle("active", button.dataset.color === value.toUpperCase());
  });
}

function setActivePreviewTab(tabName) {
  previewTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
  previewPanes.forEach((pane) => {
    pane.classList.toggle("is-hidden", pane.dataset.pane !== tabName);
  });
}

function setActivePreset(preset) {
  presetButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.preset === preset);
  });
}

function inferModeFromUrl(url) {
  try {
    const parsed = new URL(url.trim());
    if (!["github.com", "www.github.com"].includes(parsed.hostname)) {
      return "profile";
    }
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
  if (mode === "profile") {
    return PROFILE_SECTIONS;
  }
  if (mode === "project") {
    return PROJECT_SECTIONS;
  }
  return [...new Set([...PROFILE_SECTIONS, ...PROJECT_SECTIONS])];
}

function normalizeHex(value) {
  const normalized = value.trim().replace(/^#/, "").toUpperCase();
  return /^[0-9A-F]{6}$/.test(normalized) ? normalized : null;
}

function syncSectionVisibility(mode) {
  const effectiveMode = mode === "auto" ? resolveEffectiveMode() : mode;
  const defaults = new Set(getDefaultSections(effectiveMode));

  sectionChips.forEach((chip) => {
    const checkbox = chip.querySelector("input");
    const chipModes = chip.dataset.modes;
    const allowed = chipModes === "all" || chipModes === effectiveMode;
    chip.classList.toggle("is-disabled", !allowed);
    checkbox.disabled = !allowed;
    if (!allowed) {
      checkbox.checked = false;
      return;
    }
    if (!checkbox.dataset.userTouched) {
      checkbox.checked = defaults.has(checkbox.value);
    }
  });
}

function getSelectedSections() {
  return sectionChips
    .map((chip) => chip.querySelector("input"))
    .filter((checkbox) => checkbox.checked && !checkbox.disabled)
    .map((checkbox) => checkbox.value);
}

function applySectionPreset(preset) {
  const effectiveMode = resolveEffectiveMode();
  const presetValues = new Set(SECTION_PRESETS[effectiveMode]?.[preset] || getDefaultSections(effectiveMode));

  sectionChips.forEach((chip) => {
    const checkbox = chip.querySelector("input");
    const chipModes = chip.dataset.modes;
    const allowed = chipModes === "all" || chipModes === effectiveMode;
    checkbox.dataset.userTouched = "true";
    checkbox.disabled = !allowed;
    chip.classList.toggle("is-disabled", !allowed);
    checkbox.checked = allowed && presetValues.has(checkbox.value);
  });

  setActivePreset(preset);
  updateSelectionBoard();
}

function updateSelectionBoard() {
  const sections = getSelectedSections();
  const preset = document.querySelector(".preset-button.active")?.dataset.preset || "showcase";
  const chips = [
    `Mode: ${resolveEffectiveMode()}`,
    `Provider: ${providerInput.value}`,
    `Preset: ${preset}`,
    `Density: ${outputLengthInput.value}`,
    `Tone: ${toneInput.options[toneInput.selectedIndex].text}`,
    `Header: ${headerTypeInput.value}`,
    `Accent: #${colorInput.value}`,
    `Sections: ${sections.length}`,
  ];
  selectionBoard.innerHTML = chips.map((label) => `<span class="selection-pill">${label}</span>`).join("");
}

function getPayload() {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.sections = getSelectedSections();
  if (!payload.icons || !payload.icons.trim()) {
    delete payload.icons;
  }
  return payload;
}

function renderPreview(markdown) {
  if (!markdown || !markdown.trim()) {
    previewSurface.innerHTML = '<div class="preview-empty">Generate a README to see the rendered preview.</div>';
    return;
  }

  if (window.marked) {
    const rawHtml = window.marked.parse(markdown, {
      breaks: true,
      gfm: true,
    });
    previewSurface.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(rawHtml) : rawHtml;
    return;
  }

  previewSurface.innerHTML = `<pre>${markdown.replace(/[&<>]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
  }[character]))}</pre>`;
}

async function loadProviderHealth() {
  try {
    const response = await fetch("/api/generate");
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error("Provider status unavailable.");
    }

    const providers = payload.providers || {};
    providerHealth.innerHTML = ["nvidia", "groq", "gemini", "openai"]
      .map((name) => {
        const online = Boolean(providers[name]);
        const stateClass = online ? "online" : "offline";
        const stateText = online ? "ready" : "not configured";
        return `<span class="health-chip ${stateClass}">${name} ${stateText}</span>`;
      })
      .join("");
  } catch {
    providerHealth.innerHTML = '<span class="health-chip offline">Provider status unavailable</span>';
  }
}

async function generateReadme(event) {
  event.preventDefault();
  clearError();
  setStatus("loading", "Generating");
  submitButton.disabled = true;
  enableActions(false);

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getPayload()),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "The generator returned an unknown error.");
    }

    latestMarkdown = payload.markdown;
    output.value = latestMarkdown;
    renderPreview(latestMarkdown);
    setSummary({
      mode: payload.mode === "project" ? "Project README" : "Profile README",
      identity: payload.repo ? `${payload.displayName} / ${payload.repo}` : `${payload.displayName} (@${payload.username})`,
      languages: payload.summary.languages.length ? payload.summary.languages.join(", ") : "No language data",
      stats: `repos ${payload.summary.repos} | followers ${payload.summary.followers} | stars ${payload.summary.stars}`,
      lines: `${payload.lineCount} lines`,
    });
    setStatus("success", "Ready");
    enableActions(true);
  } catch (error) {
    setStatus("error", "Failed");
    showError(error.message || "Something went wrong while generating the README.");
  } finally {
    submitButton.disabled = false;
  }
}

form.addEventListener("submit", generateReadme);

[...document.querySelectorAll(".segment")].forEach((button) => {
  button.addEventListener("click", () => {
    const { target, value } = button.dataset;
    document.getElementById(target).value = value;
    setActiveSegment(target, value);
    if (target === "mode") {
      syncSectionVisibility(value);
      applySectionPreset(document.querySelector(".preset-button.active")?.dataset.preset || "showcase");
    }
    updateSelectionBoard();
  });
});

[...document.querySelectorAll(".palette-tile")].forEach((button) => {
  button.addEventListener("click", () => {
    colorInput.value = button.dataset.color;
    customColorInput.value = `#${button.dataset.color}`;
    setActiveTheme(button.dataset.color);
    updateSelectionBoard();
  });
});

customColorInput.addEventListener("input", () => {
  const normalized = normalizeHex(customColorInput.value);
  if (!normalized) {
    return;
  }
  colorInput.value = normalized;
  setActiveTheme(normalized);
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
  const checkbox = chip.querySelector("input");
  checkbox.addEventListener("change", () => {
    checkbox.dataset.userTouched = "true";
    updateSelectionBoard();
  });
});

presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    applySectionPreset(button.dataset.preset);
  });
});

[...document.querySelectorAll(".sample-button")].forEach((button) => {
  button.addEventListener("click", () => {
    repoUrlInput.value = button.dataset.sample;
    if (button.dataset.mode) {
      modeInput.value = button.dataset.mode;
      setActiveSegment("mode", button.dataset.mode);
    }
    syncSectionVisibility(modeInput.value);
    applySectionPreset(document.querySelector(".preset-button.active")?.dataset.preset || "showcase");
    updateSelectionBoard();
    document.getElementById("workspace").scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

[toneInput, outputLengthInput, headerTypeInput].forEach((element) => {
  element.addEventListener("change", updateSelectionBoard);
});

previewTabs.forEach((tab) => {
  tab.addEventListener("click", () => setActivePreviewTab(tab.dataset.tab));
});

output.addEventListener("input", () => {
  latestMarkdown = output.value;
  renderPreview(latestMarkdown);
});

copyButton.addEventListener("click", async () => {
  if (!latestMarkdown) {
    return;
  }
  await navigator.clipboard.writeText(latestMarkdown);
  setStatus("success", "Copied");
});

downloadButton.addEventListener("click", () => {
  if (!latestMarkdown) {
    return;
  }
  const blob = new Blob([latestMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "README.md";
  anchor.click();
  URL.revokeObjectURL(url);
});

latestMarkdown = [
  "# README Preview",
  "",
  "Paste a GitHub profile or repository URL and generate your markdown here.",
  "",
  "- Switch between Markdown and Live preview",
  "- Apply minimal, showcase, or full section presets",
  "- Tune density, tone, accent color, and module mix",
].join("\n");

output.value = latestMarkdown;
customColorInput.value = `#${colorInput.value}`;
renderPreview(latestMarkdown);
setSummary();
setStatus("idle", "Idle");
setActiveTheme(colorInput.value);
setActiveSegment("mode", modeInput.value);
setActiveSegment("llm", providerInput.value);
setActivePreviewTab("markdown");
syncSectionVisibility(modeInput.value);
applySectionPreset("showcase");
updateSelectionBoard();
loadProviderHealth();
