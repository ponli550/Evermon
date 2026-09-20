import { FIELDS, FIELD_LABELS, compare, type Field } from "./lib/compare.ts";

interface AttachmentRecord {
  path: string;
  docType?: string;
  text?: string;
  fields?: Record<string, string>;
  blankFields?: string[];
  error?: string;
}

interface EmailRecord {
  id: string;
  from: string;
  subject: string;
  body: string;
  category: string;
  status: string;
  reviewReason: string | null;
  defectFields: string[];
  note: string;
  si: AttachmentRecord | null;
  bl: AttachmentRecord | null;
  attachmentCount: number;
}

const CATEGORY_ORDER = ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"];
const OUTCOME_ORDER = ["OK", "MISMATCH", "NEEDS_REVIEW"] as const;
const CAT_COLOR: Record<string, string> = {
  BL_COMPARISON: "var(--cat-1)",
  SI_REQUEST: "var(--cat-2)",
  INVOICE_QUERY: "var(--cat-3)",
  GENERAL: "var(--cat-4)",
  SPAM: "var(--cat-5)",
};
const STATUS_COLOR: Record<string, string> = {
  OK: "var(--status-good)",
  MISMATCH: "var(--status-critical)",
  NEEDS_REVIEW: "var(--status-warning)",
};

let emails: EmailRecord[] = [];

async function main(): Promise<void> {
  const res = await fetch("data/emails.json");
  emails = (await res.json()) as EmailRecord[];
  renderDashboard();
  wireControls();
  populatePlayground(pickFirstComparable());
}

function pickFirstComparable(): EmailRecord {
  return (
    emails.find((e) => e.status === "MISMATCH" && e.si?.fields && e.bl?.fields) ?? emails[0]
  );
}

// ── dashboard ────────────────────────────────────────────────────────────

function renderDashboard(): void {
  const categoryCounts = new Map<string, number>();
  const outcomeCounts = new Map<string, number>();
  for (const e of emails) {
    categoryCounts.set(e.category, (categoryCounts.get(e.category) ?? 0) + 1);
    if (e.category === "BL_COMPARISON" && OUTCOME_ORDER.includes(e.status as never)) {
      outcomeCounts.set(e.status, (outcomeCounts.get(e.status) ?? 0) + 1);
    }
  }

  const catEl = document.getElementById("categoryChart")!;
  const peak = Math.max(...CATEGORY_ORDER.map((c) => categoryCounts.get(c) ?? 0), 1);
  catEl.innerHTML = CATEGORY_ORDER.map((cat) => {
    const n = categoryCounts.get(cat) ?? 0;
    const pct = Math.round((n / peak) * 100);
    return `
      <div class="bar-row">
        <span class="label">${cat}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${pct}%;background:${CAT_COLOR[cat]}"></span></span>
        <span class="count">${n}</span>
      </div>`;
  }).join("");

  const outEl = document.getElementById("outcomeChart")!;
  const total = [...outcomeCounts.values()].reduce((a, b) => a + b, 0) || 1;
  const segs = OUTCOME_ORDER.map((status) => {
    const n = outcomeCounts.get(status) ?? 0;
    const pct = (n / total) * 100;
    return `<span class="seg" style="width:${pct}%;background:${STATUS_COLOR[status]}" title="${status}: ${n}"></span>`;
  }).join("");
  const legend = OUTCOME_ORDER.map((status) => {
    const n = outcomeCounts.get(status) ?? 0;
    const pct = Math.round((n / total) * 100);
    return `<span class="item"><span class="swatch" style="background:${STATUS_COLOR[status]}"></span>${status} ${n} (${pct}%)</span>`;
  }).join("");
  outEl.innerHTML = `<div class="stack">${segs}</div><div class="legend">${legend}</div>`;
}

// ── feed / landing card ──────────────────────────────────────────────────

function matchesFilters(e: EmailRecord, category: string, query: string): boolean {
  if (category && e.category !== category) return false;
  if (!query) return true;
  const q = query.toLowerCase();
  return (
    e.id.toLowerCase().includes(q) ||
    e.subject.toLowerCase().includes(q) ||
    e.body.toLowerCase().includes(q) ||
    e.status.toLowerCase().includes(q) ||
    (e.reviewReason ?? "").toLowerCase().includes(q)
  );
}

function currentFilters(): { category: string; query: string } {
  const category = (document.getElementById("categoryFilter") as HTMLSelectElement).value;
  const query = (document.getElementById("search") as HTMLInputElement).value.trim();
  return { category, query };
}

async function feedRandom(): Promise<void> {
  const { category, query } = currentFilters();
  const pool = emails.filter((e) => matchesFilters(e, category, query));
  if (pool.length === 0) {
    setStageStatus("no email matches that filter");
    return;
  }
  const email = pool[Math.floor(Math.random() * pool.length)];
  await animateAndShow(email);
}

function setStageStatus(text: string): void {
  document.getElementById("stageStatus")!.textContent = text;
}

async function animateAndShow(email: EmailRecord): Promise<void> {
  const plane = document.getElementById("plane")!;
  const bin = document.getElementById("bin")!;
  const card = document.getElementById("card")!;
  card.hidden = true;

  plane.classList.remove("flying");
  // Force reflow so re-triggering the animation on the same element works.
  void plane.offsetWidth;
  plane.classList.add("flying");
  setStageStatus(`${email.id} arriving…`);

  await sleep(900);
  bin.classList.add("processing");
  setStageStatus("classifying…");
  await sleep(500);

  if (email.category === "BL_COMPARISON") {
    setStageStatus("comparing SI against draft BL…");
    await sleep(500);
  }
  bin.classList.remove("processing");
  setStageStatus(describeOutcome(email));
  renderCard(email);
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function describeOutcome(e: EmailRecord): string {
  if (e.category !== "BL_COMPARISON") return `classified ${e.category}`;
  if (e.status === "NEEDS_REVIEW") return `escalated — ${e.reviewReason}`;
  if (e.status === "MISMATCH") return `mismatch on ${e.defectFields.join(", ")}`;
  return "no mismatch detected";
}

function renderCard(e: EmailRecord): void {
  const card = document.getElementById("card")!;
  card.hidden = false;

  const pills = [`<span class="pill cat-${e.category}">${e.category}</span>`];
  if (e.category === "BL_COMPARISON") {
    pills.push(`<span class="pill status-${e.status}">${e.status}</span>`);
  }

  let detail = "";
  if (e.status === "NEEDS_REVIEW") {
    detail = `<div class="escalation-note"><strong>why:</strong> ${escapeHtml(e.note)}</div>`;
  } else if (e.si?.fields && e.bl?.fields) {
    detail = compareTableHtml(e.si.fields, e.bl.fields, e.defectFields);
  }

  card.innerHTML = `
    <div class="meta">
      <div>
        <div class="id">${e.id} · from ${escapeHtml(e.from)}</div>
        <div class="subject">${escapeHtml(e.subject)}</div>
      </div>
      <div>${pills.join(" ")}</div>
    </div>
    <div class="body-preview">${escapeHtml(e.body)}</div>
    ${detail}
  `;
}

function compareTableHtml(
  si: Record<string, string>,
  bl: Record<string, string>,
  defectFields: string[],
): string {
  const defects = new Set(defectFields);
  const rows = FIELDS.filter((f) => si[f] != null && bl[f] != null)
    .map((f) => {
      const isDefect = defects.has(f);
      return `
      <tr class="${isDefect ? "mismatch" : ""}">
        <td>${FIELD_LABELS[f]}</td>
        <td class="value">${escapeHtml(si[f])}</td>
        <td class="value">${escapeHtml(bl[f])}${isDefect ? '<span class="mismatch-tag">← MISMATCH</span>' : ""}</td>
      </tr>`;
    })
    .join("");
  return `
    <table class="compare-table">
      <thead><tr><th>field</th><th>SI</th><th>BL</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// ── browse list ──────────────────────────────────────────────────────────

function renderList(): void {
  const { category, query } = currentFilters();
  const listEl = document.getElementById("emailList")!;
  if (!query && !category) {
    listEl.hidden = true;
    listEl.innerHTML = "";
    return;
  }
  const pool = emails.filter((e) => matchesFilters(e, category, query)).slice(0, 50);
  listEl.hidden = false;
  listEl.innerHTML = pool
    .map(
      (e) => `
      <div class="email-row" data-id="${e.id}">
        <span>${e.id}</span>
        <span class="subj">${escapeHtml(e.subject)}</span>
        <span class="pill cat-${e.category}" style="font-size:.68rem;">${e.category === "BL_COMPARISON" ? e.status : e.category}</span>
      </div>`,
    )
    .join("");
  listEl.querySelectorAll<HTMLElement>(".email-row").forEach((row) => {
    row.addEventListener("click", () => {
      const email = emails.find((e) => e.id === row.dataset.id);
      if (email) void animateAndShow(email);
    });
  });
}

function wireControls(): void {
  document.getElementById("feedRandom")!.addEventListener("click", () => void feedRandom());
  document.getElementById("categoryFilter")!.addEventListener("change", renderList);
  document.getElementById("search")!.addEventListener("input", renderList);
  document.getElementById("runCompare")!.addEventListener("click", runPlayground);
}

// ── playground ───────────────────────────────────────────────────────────

function populatePlayground(example: EmailRecord): void {
  const siEl = document.getElementById("siFields")!;
  const blEl = document.getElementById("blFields")!;
  siEl.innerHTML = FIELDS.map((f) => fieldInputHtml("si", f, example.si?.fields?.[f] ?? "")).join("");
  blEl.innerHTML = FIELDS.map((f) => fieldInputHtml("bl", f, example.bl?.fields?.[f] ?? "")).join("");
}

function fieldInputHtml(side: "si" | "bl", field: Field, value: string): string {
  return `
    <div class="field-group">
      <label for="${side}-${field}">${FIELD_LABELS[field]}</label>
      <input id="${side}-${field}" value="${escapeHtml(value)}" />
    </div>`;
}

function runPlayground(): void {
  const si: Partial<Record<Field, string>> = {};
  const bl: Partial<Record<Field, string>> = {};
  for (const f of FIELDS) {
    si[f] = (document.getElementById(`si-${f}`) as HTMLInputElement).value;
    bl[f] = (document.getElementById(`bl-${f}`) as HTMLInputElement).value;
  }
  const result = compare(si, bl);
  const resultEl = document.getElementById("playgroundResult")!;
  const pill = `<span class="pill status-${result.status}">${result.status}</span>`;
  resultEl.innerHTML = `<p>${pill} ${result.status === "OK" ? "No mismatch detected" : `mismatch on ${result.defectFields.join(", ")}`}</p>${compareTableHtml(si as Record<Field, string>, bl as Record<Field, string>, result.defectFields)}`;
}

main().catch((err) => {
  console.error(err);
  setStageStatus("failed to load the dataset — see console");
});
