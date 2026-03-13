const form = document.getElementById("generator-form");
const output = document.getElementById("markdown-output");
const statusPill = document.getElementById("status-pill");
const errorBox = document.getElementById("error-box");
const summaryGrid = document.getElementById("summary-grid");
const copyButton = document.getElementById("copy-button");
const downloadButton = document.getElementById("download-button");
const submitButton = document.getElementById("submit-button");
const colorInput = document.getElementById("color");

let latestMarkdown = "";

function setStatus(state, text) {
  statusPill.className = `status-pill ${state}`;
  statusPill.textContent = text;
}

function setSummary({ mode = "Waiting", identity = "Paste a URL", languages = "Detected after fetch", lines = "0" }) {
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
      <span>Lines</span>
      <strong>${lines}</strong>
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

function getPayload() {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  if (!payload.sections) {
    delete payload.sections;
  }
  return payload;
}

function enableActions(enabled) {
  copyButton.disabled = !enabled;
  downloadButton.disabled = !enabled;
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
    setSummary({
      mode: payload.mode,
      identity: payload.repo ? `${payload.displayName} / ${payload.repo}` : `${payload.displayName} (@${payload.username})`,
      languages: payload.summary.languages.length ? payload.summary.languages.join(", ") : "No language data",
      lines: String(payload.lineCount),
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

document.querySelectorAll(".swatch").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".swatch").forEach((swatch) => swatch.classList.remove("active"));
    button.classList.add("active");
    colorInput.value = button.dataset.color;
  });
});

document.querySelectorAll(".sample-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.getElementById("repo-url").value = button.dataset.sample;
  });
});

copyButton.addEventListener("click", async () => {
  if (!latestMarkdown) return;
  await navigator.clipboard.writeText(latestMarkdown);
  setStatus("success", "Copied");
});

downloadButton.addEventListener("click", () => {
  if (!latestMarkdown) return;
  const blob = new Blob([latestMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "README.md";
  anchor.click();
  URL.revokeObjectURL(url);
});

setSummary({});
setStatus("idle", "Idle");
