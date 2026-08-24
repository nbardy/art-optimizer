async function readJSON(path) {
  const response = await fetch(path);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function treatmentLabel(item) {
  return item.treatment_id === "emergent-tastes" ? "ISOLATED TREATMENT" : "T0 FAMILY";
}

async function boot() {
  const list = document.querySelector("#experiment-list");
  const runtime = document.querySelector("#runtime-label");
  try {
    const [experiments, health] = await Promise.all([
      readJSON("/api/ui-experiments"),
      readJSON("/healthz"),
    ]);
    const fragment = document.createDocumentFragment();
    for (const item of experiments) {
      const link = document.createElement("a");
      link.className = `experiment-card${item.treatment_id === "emergent-tastes" ? " featured" : ""}`;
      link.href = item.route;
      link.innerHTML = `
        <span class="treatment-label">${treatmentLabel(item)}</span>
        <h2>${item.label}</h2>
        <p>${item.description}</p>
        <span class="open-label">Open experiment →</span>
      `;
      fragment.appendChild(link);
    }
    list.replaceChildren(fragment);
    runtime.textContent = `${health.model} · ${health.renderer} · ${experiments.length} interfaces`;
  } catch (error) {
    list.innerHTML = `<p class="error">${error.message}</p>`;
    runtime.textContent = "Runtime unavailable";
  }
}

boot();
