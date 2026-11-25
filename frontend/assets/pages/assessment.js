(async function () {
  const { api, esc, loading, errorBox, toast } = SCM;
  const root = document.getElementById("root");
  root.innerHTML = loading("Loading…");
  const inp = "w-full bg-surface-container-lowest text-on-surface font-body-md px-3 py-2.5 rounded-lg border border-border-subtle placeholder:text-text-muted focus:outline-none focus:border-primary-container focus:ring-2 focus:ring-primary-container/15 transition-colors";
  const field = (id, label, hint, el) => `<label class="block font-label-md text-label-md text-on-surface" for="${id}">${label}${hint ? `<span class="block font-body-sm text-text-muted font-normal">${hint}</span>` : ""}<div class="mt-1.5">${el}</div></label>`;
  try {
    await SCM.requireAuth();
    const prev = (await api("GET", "/api/assessment")).assessment || {};
    const list = (a) => (a || []).map((x) => (typeof x === "string" ? x : x.name)).join(", ");
    const skillsText = (a) => (a || []).map((x) => (typeof x === "string" ? x : `${x.name}:${x.level}`)).join(", ");
    const v = (k) => esc(prev[k] || "");
    root.innerHTML = `<form id="form" class="px-space-md pt-space-md flex flex-col gap-space-md" novalidate>
<div><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-semibold tracking-tight">Career Assessment</h1><p class="font-body-md text-on-surface-variant">Tell us about yourself. Your answers drive an explainable match against ${9} career paths.</p></div>
<section class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-sm"><h2 class="font-headline-sm text-label-md font-semibold">Education</h2>
${field("degree", "Degree", "", `<input id="degree" class="${inp}" placeholder="e.g. BSc (Hons)" value="${v("degree")}">`)}
${field("specialization", "Specialization", "", `<input id="specialization" class="${inp}" placeholder="e.g. Computer Science" value="${v("specialization")}">`)}
${field("education", "Institution / year", "", `<input id="education" class="${inp}" placeholder="e.g. Utkal University, 2026" value="${v("education")}">`)}</section>
<section class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-sm"><h2 class="font-headline-sm text-label-md font-semibold">Skills</h2>
${field("skills", "Technical skills", "Comma separated. Add a level with a colon: <code>Python:advanced, SQL:beginner</code> (beginner / intermediate / advanced; default intermediate).", `<textarea id="skills" rows="3" class="${inp}" placeholder="Python:advanced, React, SQL:beginner, Git">${esc(skillsText(prev.skills))}</textarea>`)}
${field("languages", "Programming languages", "Same format.", `<input id="languages" class="${inp}" placeholder="JavaScript:advanced, Java" value="${esc(skillsText(prev.languages))}">`)}
${field("strengths", "Strengths", "", `<input id="strengths" class="${inp}" placeholder="problem solving, design sense" value="${esc(list(prev.strengths))}">`)}
${field("weaknesses", "Weaknesses", "", `<input id="weaknesses" class="${inp}" placeholder="system design, public speaking" value="${esc(list(prev.weaknesses))}">`)}</section>
<section class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-sm"><h2 class="font-headline-sm text-label-md font-semibold">Interests &amp; goals</h2>
${field("interests", "Interests", "e.g. web, apis, ai, design, data, security, cloud", `<input id="interests" class="${inp}" placeholder="web, backend, startups" value="${esc(list(prev.interests))}">`)}
${field("preferred_roles", "Preferred job roles", "", `<input id="preferred_roles" class="${inp}" placeholder="Full Stack Developer, Backend Developer" value="${esc(list(prev.preferred_roles))}">`)}
${field("career_goals", "Career goals", "", `<textarea id="career_goals" rows="2" class="${inp}" placeholder="What do you want to be doing in 2 years?">${v("career_goals")}</textarea>`)}</section>
<section class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex flex-col gap-space-sm"><h2 class="font-headline-sm text-label-md font-semibold">Experience</h2>
${field("projects", "Projects", "One per line or comma separated", `<textarea id="projects" rows="2" class="${inp}" placeholder="Task manager app, Portfolio website">${esc(list(prev.projects))}</textarea>`)}
${field("experience", "Work experience / internships", "", `<textarea id="experience" rows="2" class="${inp}" placeholder="Web development intern, 3 months">${v("experience")}</textarea>`)}</section>
<p id="err" class="hidden font-body-sm text-error flex items-center gap-1"></p>
<button id="submit" class="w-full h-11 bg-primary-container hover:bg-primary text-on-primary font-label-md rounded-lg transition-all shadow-sm">${prev.updated_at ? "Update &amp; Recalculate" : "Get My Recommendations"}</button></form>`;
    const parseSkills = (s) => s.split(/[,\n;]/).map((x) => x.trim()).filter(Boolean).map((x) => { const [name, level] = x.split(":").map((p) => p.trim()); return { name, level: (level || "intermediate").toLowerCase() }; });
    document.getElementById("form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const g = (id) => document.getElementById(id).value;
      const body = { degree: g("degree"), specialization: g("specialization"), education: g("education"), skills: parseSkills(g("skills")), languages: parseSkills(g("languages")),
        strengths: g("strengths"), weaknesses: g("weaknesses"), interests: g("interests"), preferred_roles: g("preferred_roles"), career_goals: g("career_goals"), projects: g("projects"), experience: g("experience") };
      const err = document.getElementById("err"), btn = document.getElementById("submit");
      err.classList.add("hidden"); btn.disabled = true; btn.textContent = "Calculating…";
      try { await api("POST", "/api/assessment", body); toast("Assessment saved."); location.href = "career-recommendations.html"; }
      catch (ex) { err.textContent = ex.message; err.classList.remove("hidden"); btn.disabled = false; btn.textContent = "Get My Recommendations"; }
    });
  } catch (e) { if (e.status !== 401) root.innerHTML = errorBox(e.message); }
})();
