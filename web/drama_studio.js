import { app } from "../../scripts/app.js";

const API = "/drama_studio";

const state = {
  projects: [],
  project: null,
  episodeId: null,
  selectedShots: new Set(),
};

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

async function api(path, options = {}) {
  const opts = { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } };
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function currentEpisode() {
  return state.project?.episodes?.find(e => e.episode_id === state.episodeId) || state.project?.episodes?.[0] || null;
}

async function refreshProjects() {
  const data = await api("/projects");
  state.projects = data.projects || [];
  render();
}

async function loadProject(id) {
  state.project = await api(`/projects/${encodeURIComponent(id)}`);
  state.episodeId = state.project.episodes?.[0]?.episode_id || null;
  state.selectedShots.clear();
  render();
}

function field(label, value = "", type = "text") {
  const wrap = el("label", "ds-field");
  wrap.appendChild(el("span", "ds-label", label));
  const input = el("input", "ds-input");
  input.type = type;
  input.value = value;
  wrap.appendChild(input);
  return { wrap, input };
}

function button(text, cls = "") {
  return el("button", `ds-btn ${cls}`.trim(), text);
}

function card(title) {
  const c = el("section", "ds-card");
  c.appendChild(el("h3", "ds-card-title", title));
  return c;
}

async function createProject() {
  const name = prompt("Drama project name:", "The Last Contract");
  if (!name) return;
  const synopsis = prompt("One-line synopsis (optional):", "A woman discovers her husband is hiding a dangerous secret.") || "";
  const p = await api("/projects", { method: "POST", body: JSON.stringify({ name, synopsis, episode_count: 10, episode_duration_seconds: 90 }) });
  await loadProject(p.project_id);
  await refreshProjects();
}

async function addCharacter() {
  if (!state.project) return;
  const name = prompt("Character name:", "Meera");
  if (!name) return;
  const role = prompt("Role:", "Protagonist") || "";
  const personality = prompt("Personality:", "Intelligent, guarded, emotionally controlled") || "";
  await api(`/projects/${state.project.project_id}/characters`, {
    method: "POST",
    body: JSON.stringify({ name, role, personality }),
  });
  await loadProject(state.project.project_id);
}

async function addShot() {
  const ep = currentEpisode();
  if (!state.project || !ep) return;
  const title = prompt("Shot title:", `Shot ${(ep.shots?.length || 0) + 1}`);
  if (!title) return;
  const duration = Number(prompt("Duration in seconds:", "8") || 8);
  await api(`/projects/${state.project.project_id}/episodes/${ep.episode_id}/shots`, {
    method: "POST",
    body: JSON.stringify({ title, duration_seconds: duration, reference_strategy: "previous_frame" }),
  });
  await loadProject(state.project.project_id);
}

async function regenerateSelected() {
  const ep = currentEpisode();
  const ids = [...state.selectedShots];
  if (!state.project || !ep || !ids.length) return alert("Select at least one shot.");
  const reason = prompt("Regeneration reason:", "character inconsistency") || "general";
  const notes = prompt("Notes for the new version (optional):", "") || "";
  await api(`/projects/${state.project.project_id}/episodes/${ep.episode_id}/shots/regenerate`, {
    method: "POST",
    body: JSON.stringify({ shot_ids: ids, reason, notes }),
  });
  await loadProject(state.project.project_id);
  alert(`Queued ${ids.length} selected shot(s) for a new version. Other shots were not modified.`);
}

async function approveSelected() {
  const ep = currentEpisode();
  const ids = [...state.selectedShots];
  if (!state.project || !ep || !ids.length) return alert("Select at least one shot.");
  await api(`/projects/${state.project.project_id}/episodes/${ep.episode_id}/shots/approve`, {
    method: "POST",
    body: JSON.stringify({ shot_ids: ids }),
  });
  await loadProject(state.project.project_id);
}

async function rebuildSlate() {
  const ep = currentEpisode();
  if (!state.project || !ep) return;
  await api(`/projects/${state.project.project_id}/episodes/${ep.episode_id}/slate/rebuild`, { method: "POST", body: "{}" });
  await loadProject(state.project.project_id);
  alert("Episode slate manifest rebuilt from approved/current shot versions.");
}

function render() {
  let root = document.getElementById("drama-studio-panel");
  if (!root) {
    root = el("div");
    root.id = "drama-studio-panel";
    document.body.appendChild(root);
  }
  root.innerHTML = "";

  const shell = el("div", "ds-shell");
  const header = el("div", "ds-header");
  const titleWrap = el("div");
  titleWrap.appendChild(el("div", "ds-title", "Drama Studio"));
  titleWrap.appendChild(el("div", "ds-subtitle", "Microdrama production control room • V0.1"));
  header.appendChild(titleWrap);
  const close = button("×", "ds-close");
  close.onclick = () => shell.classList.remove("ds-open");
  header.appendChild(close);
  shell.appendChild(header);

  const body = el("div", "ds-body");

  const projectCard = card("1 · Project");
  const controls = el("div", "ds-row");
  const newBtn = button("New Project", "ds-primary");
  newBtn.onclick = createProject;
  controls.appendChild(newBtn);
  const refresh = button("Refresh");
  refresh.onclick = refreshProjects;
  controls.appendChild(refresh);
  projectCard.appendChild(controls);

  if (!state.projects.length) {
    projectCard.appendChild(el("p", "ds-muted", "No projects yet. Create the first drama project."));
  } else {
    const select = el("select", "ds-input");
    const empty = el("option");
    empty.value = "";
    empty.textContent = "Select project…";
    select.appendChild(empty);
    state.projects.forEach(p => {
      const o = el("option");
      o.value = p.project_id;
      o.textContent = `${p.name} · ${p.project_id}`;
      if (state.project?.project_id === p.project_id) o.selected = true;
      select.appendChild(o);
    });
    select.onchange = () => select.value && loadProject(select.value);
    projectCard.appendChild(select);
  }
  body.appendChild(projectCard);

  if (state.project) {
    const status = card("2 · Pipeline State");
    const pipeline = [
      ["Bible", !!state.project.bible],
      ["Characters", state.project.characters?.length > 0],
      ["Locations", state.project.locations?.length > 0],
      ["Season", state.project.episodes?.length > 0],
      ["Storyboard", currentEpisode()?.storyboard?.length > 0],
      ["Shots", currentEpisode()?.shots?.length > 0],
      ["Render", currentEpisode()?.shots?.some(s => s.status === "approved")],
      ["Slate", !!currentEpisode()?.slate],
    ];
    pipeline.forEach(([name, ok]) => {
      const r = el("div", "ds-stage");
      r.appendChild(el("span", ok ? "ds-dot ds-ok" : "ds-dot ds-pending", ""));
      r.appendChild(el("span", "", name));
      status.appendChild(r);
    });
    body.appendChild(status);

    const chars = card(`3 · Characters (${state.project.characters?.length || 0})`);
    const charRow = el("div", "ds-row");
    const addCharBtn = button("Add Character");
    addCharBtn.onclick = addCharacter;
    charRow.appendChild(addCharBtn);
    chars.appendChild(charRow);
    (state.project.characters || []).forEach(c => {
      const r = el("div", "ds-item");
      r.innerHTML = `<strong>${c.character_id}</strong> · ${c.name}<span>${c.role || ""}</span>`;
      chars.appendChild(r);
    });
    body.appendChild(chars);

    const epCard = card("4 · Episode / Shots");
    const epSelect = el("select", "ds-input");
    (state.project.episodes || []).forEach(ep => {
      const o = el("option");
      o.value = ep.episode_id;
      o.textContent = `${ep.episode_id} · ${ep.title}`;
      if (ep.episode_id === state.episodeId) o.selected = true;
      epSelect.appendChild(o);
    });
    epSelect.onchange = () => { state.episodeId = epSelect.value; state.selectedShots.clear(); render(); };
    epCard.appendChild(epSelect);

    const tools = el("div", "ds-row ds-wrap");
    const addShotBtn = button("Add Shot");
    addShotBtn.onclick = addShot;
    tools.appendChild(addShotBtn);
    const regenBtn = button("Regenerate Selected", "ds-danger");
    regenBtn.onclick = regenerateSelected;
    tools.appendChild(regenBtn);
    const approveBtn = button("Approve Selected", "ds-primary");
    approveBtn.onclick = approveSelected;
    tools.appendChild(approveBtn);
    const slateBtn = button("Rebuild Slate");
    slateBtn.onclick = rebuildSlate;
    tools.appendChild(slateBtn);
    epCard.appendChild(tools);

    const ep = currentEpisode();
    (ep?.shots || []).forEach(shot => {
      const row = el("div", "ds-shot");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = state.selectedShots.has(shot.shot_id);
      checkbox.onchange = () => checkbox.checked ? state.selectedShots.add(shot.shot_id) : state.selectedShots.delete(shot.shot_id);
      row.appendChild(checkbox);
      const meta = el("div", "ds-shot-meta");
      const top = el("div", "ds-shot-top");
      top.appendChild(el("strong", "", shot.shot_id));
      top.appendChild(el("span", `ds-status ds-${shot.status}`, shot.status));
      meta.appendChild(top);
      meta.appendChild(el("div", "ds-shot-title", shot.title));
      const version = shot.current_version || 0;
      meta.appendChild(el("div", "ds-muted", `v${version} · ${shot.duration_seconds}s · ${shot.issue || "no issue"}`));
      row.appendChild(meta);
      epCard.appendChild(row);
    });
    body.appendChild(epCard);

    const info = card("5 · Next build step");
    info.appendChild(el("p", "ds-muted", "V0.1 currently manages the show state, characters, shot versions, selective regeneration, approvals, and slate manifests. The next adapter layer connects these shot records to your MiniMax H3 Ref2VA workflows, Qwen image workflows, Qwen3-TTS, MuseTalk, and FFmpeg."));
    body.appendChild(info);
  }

  shell.appendChild(body);
  root.appendChild(shell);

  // Keep the panel closed until the user launches it, except on first load.
  if (!root.dataset.initialized) {
    root.dataset.initialized = "1";
    shell.classList.add("ds-open");
    refreshProjects().catch(err => console.warn("Drama Studio", err));
  }
}

function addLauncher() {
  if (document.getElementById("drama-studio-launcher")) return;
  const btn = el("button", "ds-launcher", "Drama Studio");
  btn.id = "drama-studio-launcher";
  btn.onclick = () => document.querySelector("#drama-studio-panel .ds-shell")?.classList.toggle("ds-open");
  document.body.appendChild(btn);
}

app.registerExtension({
  name: "DramaStudio",
  async setup() {
    if (!document.getElementById("drama-studio-style")) {
      const link = document.createElement("link");
      link.id = "drama-studio-style";
      link.rel = "stylesheet";
      link.href = "/extensions/DramaStudio/drama_studio.css";
      document.head.appendChild(link);
    }
    addLauncher();
    render();
  },
});
