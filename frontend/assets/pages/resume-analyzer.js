(async function () {
  const { api, esc, skillLabel, loading, errorBox, toast, ago } = SCM;
  const root = document.getElementById("root");
  root.innerHTML = loading("Loading…");
  let careers = [];
  const verdict = (s) => (s >= 80 ? "Strong for this role" : s >= 60 ? "Competitive, with room to improve" : "Needs work");
  const LABELS = { skills: "Skills Relevance", keywords: "Keyword Coverage", experience: "Experience & Impact", projects: "Project Quality", education: "Education", structure: "Resume Structure", readability: "Readability" };
  const COLORS = ["bg-status-success", "bg-primary-container", "bg-secondary", "bg-status-warning"];

  function results(r) {
    const a = r.analysis, x = a.extracted;
    return `
<div class="px-space-md mt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm">
<div class="flex items-start justify-between pb-space-sm"><div><span class="font-label-sm text-label-sm text-text-muted uppercase tracking-wider">ATS-style compatibility estimate</span><div class="flex items-baseline gap-1 mt-0.5"><span class="font-metric-display text-headline-xl-mobile text-primary-container tracking-tight">${a.overall_score}</span><span class="font-metric-inline text-label-md text-text-muted">/100</span></div></div>
<div class="flex flex-col items-end"><span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm"><span class="material-symbols-outlined text-[14px]">verified</span>${verdict(a.overall_score)}</span><span class="font-body-sm text-[11px] text-text-muted mt-1 text-right">Target: ${esc(a.target_career)}</span></div></div>
<div class="mt-space-md space-y-3">${Object.entries(a.category_scores).map(([k, v], i) => `<div class="flex flex-col gap-1"><div class="flex items-center justify-between font-label-md text-label-sm"><span class="text-on-surface flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full ${COLORS[i % 4]}"></span>${LABELS[k]} <span class="text-text-muted">(${Math.round(a.weights[k] * 100)}%)</span></span><span class="font-metric-inline text-metric-inline text-on-surface">${v}%</span></div><div class="w-full h-2 rounded-full bg-surface-container overflow-hidden"><div class="h-full rounded-full ${COLORS[i % 4]} transition-all duration-700" style="width:${v}%"></div></div></div>`).join("")}</div>
<p class="mt-space-md font-body-sm text-[12px] text-text-muted flex gap-1.5"><span class="material-symbols-outlined text-[16px]">info</span>${esc(a.disclaimer)}</p></div></div>
<div class="px-space-md mt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm"><h3 class="font-headline-sm text-label-md font-semibold text-on-surface flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-primary">hub</span>Keyword coverage for ${esc(a.target_career)}</h3>
<p class="font-label-sm text-text-muted mt-2">Found (${a.keywords_present.length})</p><div class="flex flex-wrap gap-1.5 mt-1">${a.keywords_present.map((k) => `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-secondary-container text-on-secondary-container font-label-sm"><span class="material-symbols-outlined text-[14px]">check</span>${esc(skillLabel(k))}</span>`).join("") || '<span class="font-body-sm text-text-muted">None found</span>'}</div>
<p class="font-label-sm text-text-muted mt-3">Missing (${a.missing_keywords.length}) — add only what you genuinely know</p><div class="flex flex-wrap gap-1.5 mt-1">${a.missing_keywords.map((k) => `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-label-sm"><span class="material-symbols-outlined text-[14px] text-status-warning">add</span>${esc(skillLabel(k))}</span>`).join("") || '<span class="font-body-sm text-text-muted">Nothing missing</span>'}</div></div></div>
<div class="px-space-md mt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm"><h3 class="font-headline-sm text-label-md font-semibold text-on-surface flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-primary">rule</span>What to improve</h3>
${a.weak_sections.length ? `<p class="font-label-sm text-text-muted mt-2">Weak sections: ${a.weak_sections.map(esc).join(", ")}</p>` : ""}
<ul class="mt-2 space-y-2">${a.suggestions.map((s) => `<li class="flex gap-2 font-body-md text-on-surface-variant"><span class="material-symbols-outlined text-[18px] text-status-warning shrink-0 mt-0.5">tips_and_updates</span><span>${esc(s)}</span></li>`).join("") || '<li class="font-body-md text-on-surface-variant">No major issues found.</li>'}</ul></div></div>
${a.improvement_examples.length ? `<div class="px-space-md mt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm"><h3 class="font-headline-sm text-label-md font-semibold text-on-surface flex items-center gap-1.5"><span class="material-symbols-outlined text-[18px] text-primary">compare_arrows</span>Bullet improvements</h3><p class="font-body-sm text-text-muted mt-1">Original bullets from your resume, with what to add. We don't invent numbers for you.</p>${a.improvement_examples.map((e) => `<div class="mt-space-sm"><div class="p-space-sm rounded-lg bg-surface-bg"><p class="font-label-sm text-text-muted flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">remove</span>Original</p><p class="font-body-md text-on-surface-variant">“${esc(e.original)}”</p></div><div class="p-space-sm rounded-lg bg-secondary-container/40 mt-1"><p class="font-label-sm text-on-secondary-container flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">add</span>Suggested change</p><p class="font-body-md text-on-surface">${esc(e.tip)}</p></div></div>`).join("")}</div></div>` : ""}
<div class="px-space-md mt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm"><h3 class="font-headline-sm text-label-md font-semibold text-on-surface">What we extracted</h3><dl class="mt-2 grid grid-cols-2 gap-y-1 font-body-sm"><dt class="text-text-muted">Email</dt><dd class="text-on-surface truncate">${esc(x.email || "not found")}</dd><dt class="text-text-muted">Links</dt><dd class="text-on-surface truncate">${esc(x.links.join(", ") || "none")}</dd><dt class="text-text-muted">Sections</dt><dd class="text-on-surface">${x.sections_found.map(esc).join(", ")}</dd><dt class="text-text-muted">Words / bullets</dt><dd class="text-on-surface">${x.word_count} / ${x.bullet_count}</dd><dt class="text-text-muted">Quantified bullets</dt><dd class="text-on-surface">${x.quantified_bullets}</dd></dl></div></div>`;
  }

  async function show(r) { document.getElementById("results").innerHTML = results(r); }

  try {
    await SCM.requireAuth();
    [careers] = await Promise.all([api("GET", "/api/careers/available").then((d) => d.careers)]);
    const hist = (await api("GET", "/api/resume/history")).resumes;
    root.innerHTML = `
<section class="px-space-md pt-space-md"><div class="bg-surface-container-lowest rounded-xl p-space-md shadow-sm flex flex-col gap-space-sm">
<div class="flex items-center gap-space-sm"><span class="material-symbols-outlined text-[28px] text-primary">upload_file</span><div class="min-w-0"><h1 class="font-headline-sm text-headline-sm font-semibold text-on-surface">Analyze your resume</h1><p class="font-body-sm text-text-muted">PDF or DOCX, max 5 MB. Analysis runs on our server only; your file is not shared with third parties and only the extracted text is stored, privately.</p></div></div>
<label class="font-label-md text-on-surface">Target role<select id="career" class="mt-1 w-full bg-surface-container-lowest text-on-surface rounded-lg border border-border-subtle px-3 py-2.5 focus:outline-none focus:border-primary-container"><option value="">Best fit (auto-detect)</option>${careers.map((c) => `<option value="${esc(c.id)}">${esc(c.title)}</option>`).join("")}</select></label>
<input id="file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" class="block w-full font-body-sm text-on-surface-variant file:mr-3 file:px-3 file:h-9 file:rounded-lg file:border-0 file:bg-surface-container file:text-primary file:font-label-md">
<button id="analyze" class="h-11 bg-primary-container hover:bg-primary text-on-primary font-label-md rounded-lg transition-all flex items-center justify-center gap-2 shadow-sm"><span class="material-symbols-outlined text-[18px]">bolt</span><span id="analyzeText">Upload &amp; Analyze</span></button></div></section>
${hist.length ? `<section class="px-space-md mt-space-md"><h2 class="font-label-sm text-text-muted uppercase tracking-wider mb-1">Previous analyses</h2><div class="flex flex-col gap-1">${hist.map((h) => `<button data-id="${h.id}" class="text-left bg-surface-container-lowest rounded-lg px-space-md py-2 shadow-sm flex items-center justify-between hover:bg-surface-bg"><span class="truncate font-body-sm text-on-surface">${esc(h.filename)} <span class="text-text-muted">· ${ago(h.uploaded_at)}</span></span><span class="font-metric-inline text-primary">${h.overall_score}</span></button>`).join("")}</div></section>` : ""}
<div id="results"></div>`;
    document.getElementById("analyze").addEventListener("click", async () => {
      const f = document.getElementById("file").files[0];
      if (!f) return toast("Choose a PDF or DOCX file first.", "error");
      if (f.size > 5 * 1024 * 1024) return toast("File is too large (max 5 MB).", "error");
      const btn = document.getElementById("analyze"), txt = document.getElementById("analyzeText");
      btn.disabled = true; txt.textContent = "Analyzing…";
      const fd = new FormData(); fd.append("resume", f); const c = document.getElementById("career").value; if (c) fd.append("career_id", c);
      try { const { resume } = await api("POST", "/api/resume/upload", fd); await show(resume); toast("Analysis complete."); document.getElementById("results").scrollIntoView({ behavior: "smooth" }); }
      catch (e) { toast(e.message, "error"); }
      btn.disabled = false; txt.textContent = "Upload & Analyze";
    });
    root.querySelectorAll("[data-id]").forEach((b) => b.addEventListener("click", async () => {
      try { await show((await api("GET", "/api/resume/" + b.dataset.id)).resume); } catch (e) { toast(e.message, "error"); }
    }));
    if (hist.length) await show((await api("GET", "/api/resume/" + hist[0].id)).resume);
  } catch (e) { if (e.status !== 401) root.innerHTML = errorBox(e.message); }
})();
