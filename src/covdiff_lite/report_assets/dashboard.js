/* All data and assets are local. DOM text APIs preserve source as evidence, never HTML. */
"use strict";
(() => {
  const data = JSON.parse(document.getElementById("report-data").textContent);
  const $ = id => document.getElementById(id);
  const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  const clear = id => $(id).replaceChildren();
  const pretty = v => JSON.stringify(v, null, 2);
  const words = v => String(v || "").replaceAll("_", " ");
  const names = {complete_agreement:"Complete agreement",known_convention_difference:"Known convention",unresolved_disagreement:"Unresolved",probable_incorrect_coverage_report:"Probable incorrect report",unstable_or_non_reproducible:"Unstable",pipeline_failure:"Pipeline failure"};
  const tones = {complete_agreement:"matched",known_convention_difference:"convention",unresolved_disagreement:"unresolved",probable_incorrect_coverage_report:"mismatch",unstable_or_non_reproducible:"unresolved",pipeline_failure:"mismatch"};
  const tools = ["gcov", "llvm-cov"];
  let suite = data.suites[0], selected = null, repeatIndex = 0, findingsOnly = false, targetLine = null;
  const badge = (text, tone="neutral") => el("span", text, "badge " + tone);
  const caseHash = (id, line, suiteId=suite.id) => "#" + suiteId + "/" + id + (line ? "/" + line : "");
  const link = (text, href) => { const a = el("a", text); a.href = href; return a; };
  function observation(repeat, tool, line) {
    const report = repeat.observations[tool];
    return report === null ? null : (report[String(line)] || {state:"not_reported", count:null, covered:null});
  }
  function countText(o) { return o === null ? "Unavailable" : o.state !== "reported" ? "Not reported" : String(o.count); }
  function matches(o, expected) { return o && o.state === "reported" && (expected.comparison === "binary" ? o.covered === (expected.count > 0) : o.count === expected.count); }
  function chooseSuite(id) {
    suite = data.suites.find(s => s.id === id) || data.suites[0];
    clear("suite-tabs");
    for (const s of data.suites) {
      const b = el("button", s.label); b.append(el("span", s.cases.length.toLocaleString(), "tab-count"));
      b.setAttribute("aria-pressed", String(s.id === suite.id));
      b.addEventListener("click", () => { resetFilters(); chooseSuite(s.id); selected=null; renderList(); });
      $("suite-tabs").append(b);
    }
    $("overview-title").textContent = suite.label;
    const s = suite.summary, documented = suite.context["documented-issues.json"], layout = suite.context["layout-results.json"];
    $("overview-note").textContent = documented ? `${documented.distinct_patterns_reproduced} documented problem patterns, checked with positive fixtures and a corrective control. These fixtures are separate from the generated experiment.` : layout ? `${layout.pairs_passed} / ${layout.pairs} layout pairs passed. ${layout.compared_statement_pairs} semantic statement pairs preserve their tool observations; source mappings can still change.` : "Deterministic programs checked against a template-derived oracle. Scored statements, reporting conventions, and unresolved source mappings remain distinct.";
    clear("tool-versions");
    for (const key of ["gcov", "llvm_cov"]) $("tool-versions").append(el("div", `${key === "gcov" ? "GCC / gcov" : "Clang / llvm-cov"}  ${suite.environment.tools?.[key]?.version || "not recorded"}`));
    $("tool-versions").append(el("div", "C11 · -O0 · isolated profiles"));
    clear("metrics");
    const mismatchCount = Object.values(s.oracle_mismatches).reduce((a,b)=>a+b,0);
    const metrics = [["Programs", s.cases, "this dataset only"],["Comparable lines", s.comparable_lines,"both tools reported a scored location"],["Oracle contradictions",mismatchCount,"tool–location observations, first pass"],["Unresolved cases",s.classification_counts.unresolved_disagreement || 0,"classification retained after review"],["Stable cases",suite.cases.filter(c=>c.stable === true).length,`${s.coverage_collections} paired coverage collections`]];
    for (const [label,value,note] of metrics) { const card=el("div",undefined,"metric"); card.append(el("span",label,"label"),el("strong",value.toLocaleString()),el("div",note,"note")); $("metrics").append(card); }
    clear("status-strip");
    for (const [name, count] of Object.entries(s.classification_counts)) { const b=el("button",`${count} ${names[name] || words(name)}`,"badge " +(tones[name] || "neutral")); b.addEventListener("click",()=>{$("class-filter").value=name;renderList();}); $("status-strip").append(b); }
    for (const [id,values,placeholder] of [["family-filter",[...new Set(suite.cases.map(c=>c.family))].sort(),"All constructs"],["class-filter",Object.keys(s.classification_counts),"All classifications"]]) {
      clear(id); const first=el("option",placeholder);first.value="";$(id).append(first);
      for(const v of values) { const option=el("option",names[v] || words(v));option.value=v;$(id).append(option); }
    }
    clear("dataset-evidence");
    for (const [name,href] of Object.entries(suite.evidence)) if(href) $("dataset-evidence").append(link(name,href));
  }
  function resetFilters() { for(const id of ["search","family-filter","class-filter","tool-filter"]) $(id).value=""; }
  function renderList() {
    const search=$("search").value.trim().toLowerCase(), family=$("family-filter").value, classification=$("class-filter").value, tool=$("tool-filter").value;
    const filtered=suite.cases.filter(c=>(!family || c.family===family) && (!classification || c.classification===classification) && (!search || (c.case_id+" "+c.family+" "+c.lines.map(l=>l.source).join("\n")).toLowerCase().includes(search)) && (!tool || c.repeats.some(r=>r.findings.some(f=>f.tool===tool || f.tool==="both") || r.errors.some(e=>e.tool===tool))));
    if (!filtered.some(c=>c.case_id===selected?.case_id)) { selected=filtered[0] || null; repeatIndex=0;targetLine=null; }
    clear("case-list");$("case-counter").textContent=`${filtered.length} / ${suite.cases.length}`;
    for (const c of filtered) { const b=el("button",undefined,"case-item");b.setAttribute("aria-current",String(c===selected));b.append(el("strong",c.case_id));const meta=el("span",undefined,"item-meta");meta.append(el("span",words(c.family)),badge(names[c.classification] || words(c.classification),tones[c.classification]));b.append(meta);b.addEventListener("click",()=>{selected=c;repeatIndex=0;targetLine=null;renderList();});$("case-list").append(b); }
    $("empty-state").hidden=!!selected;$("case-content").hidden=!selected;
    if(selected){history.replaceState(null,"",caseHash(selected.case_id,targetLine));renderCase();}
  }
  function renderSource() {
    clear("source-body");const repeat=selected.repeats[repeatIndex];let shown=0;
    for (const row of selected.lines) {
      const findings=repeat.findings.filter(f=>f.line===row.line);
      if(findingsOnly && !findings.length && row.line!==targetLine) continue;
      const gc=observation(repeat,"gcov",row.line),llvm=observation(repeat,"llvm-cov",row.line);
      const priority=["probable_incorrect_coverage_report","unresolved_disagreement","known_convention_difference"];
      const assessment=findings.some(f=>f.assessment==="candidate_incorrect_report") ? "probable_incorrect_coverage_report" : priority.find(a=>findings.some(f=>f.assessment===a));
      const agree=repeat.oracle_trusted && row.expected && matches(gc,row.expected) && matches(llvm,row.expected);
      const tone=tones[assessment] || (agree ? "matched" : "neutral");
      const tr=el("tr",undefined,`line-${tone}`+(targetLine===row.line?" target-line":""));tr.id=`source-line-${row.line}`;tr.dataset.line=row.line;
      const number=el("td",undefined,"line-number");number.append(link(row.line,caseHash(selected.case_id,row.line)));
      const source=el("td",row.source,"code-cell");
      const expected=el("td",row.expected ? String(row.expected.count) : "Unscored","count-cell"+(row.expected?"":" missing-count"));
      expected.title=row.expected ? `${row.expected.statement_id || "Reviewed location"}; ${row.expected.comparison} comparison${row.expected.allow_elided ? "; missing mapping allowed when dead" : ""}` : "No universal statement-count oracle on this source line";
      tr.append(number,source,expected);
      for(const o of [gc,llvm]) { const td=el("td",countText(o),"count-cell"+(!o || o.state!=="reported"?" missing-count":""));td.title=o?.state==="reported" ? (o.covered?"Covered":"Uncovered (reported zero)") : o===null ? "Coverage report unavailable; collection failed" : "This tool did not map this source line";tr.append(td); }
      const cell=el("td",undefined,"assessment");
      cell.append(el("span",assessment === "probable_incorrect_coverage_report" ? "Oracle contradiction" : assessment ? names[assessment] : agree ? "Oracle agreement" : row.expected?.allow_elided && [gc,llvm].some(o=>o?.state!=="reported") ? "Allowed dead-body elision" : row.expected && !repeat.oracle_trusted ? "Oracle unverified" : row.expected ? "Not comparable" : "Unscored location","assessment-title"));
      for(const f of findings){const note=el("span",`${f.reason || (f.kind.startsWith("oracle_") ? `${f.tool}: expected ${f.expected}, observed ${f.actual}` : "Tool source mappings differ; no frozen convention rule applies.")}${f.rule_id ? " ["+f.rule_id+"]" : ""}`);cell.append(note);}
      tr.append(cell);$("source-body").append(tr);shown++;
    }
    $("line-counter").textContent=`${shown} / ${selected.lines.length} source lines shown · Counts refer to this collection · Unscored and missing locations are excluded from comparable-line totals.`;
    $("all-lines").setAttribute("aria-pressed",String(!findingsOnly));$("findings-only").setAttribute("aria-pressed",String(findingsOnly));
  }
  function renderPair() {
    const results=suite.context["layout-results.json"]?.results || [];
    const pair=results.find(p=>p.base_case_id===selected.case_id || p.variant_case_id===selected.case_id);
    $("pair-panel").hidden=!pair;if(!pair)return;
    $("pair-note").textContent=`${words(pair.transformation)}. ${pair.passed?"Pair passed":"Pair failed"}; parent rerun ${pair.base_reproduces_main_signature?"matches":"does not match"} the frozen main signature. Mapping differences: ${pair.mapping_differences.base} → ${pair.mapping_differences.variant}. Counts below are the recorded first collection.`;
    clear("pair-links");$("pair-links").append(link("Parent source",caseHash(pair.base_case_id)),link("Layout variant",caseHash(pair.variant_case_id)));
    if(data.suites.some(s=>s.id==="main" && s.cases.some(c=>c.case_id===pair.base_case_id))) $("pair-links").append(link("Original main case",caseHash(pair.base_case_id,null,"main")));
    clear("pair-body");
    for(const s of pair.statements) {const tr=el("tr");tr.append(el("td",s.statement_id),el("td",String(s.base.expected)));for(const side of ["base","variant"]){const td=el("td");td.append(link(`${countText(s[side].gcov)} / ${countText(s[side]["llvm-cov"])} · L${s[side].line}`,caseHash(pair[side==="base"?"base_case_id":"variant_case_id"],s[side].line)));tr.append(td);}tr.append(el("td",s.observations_equal && s.oracle_counts_correct ? "Preserved" : "Inspect"));$("pair-body").append(tr);}
  }
  function renderCase() {
    const c=selected,r=c.repeats[repeatIndex];
    $("case-family").textContent=words(c.family);$("case-title").textContent=c.case_id;
    clear("case-badges");$("case-badges").append(badge(names[c.classification] || words(c.classification),tones[c.classification]),badge(c.stable===true?`Stable · ${c.runs} collections`:c.stable===false?"Unstable":"Repeatability unconfirmed",c.stable===true?"matched":"unresolved"));
    if(c.documented_check) $("case-badges").append(badge(c.documented_check.role==="negative_control"?"Corrective control":"Documented fixture"));
    $("source-link").href=c.evidence["case.c"];
    const descriptions={complete_agreement:"Scored observations agree with the oracle and no retained differences were classified.",known_convention_difference:"Reported differences match frozen convention rules. Tool-specific source attribution is retained.",unresolved_disagreement:"Some source mappings have no frozen convention rule. They remain unresolved after review; this classification does not establish a tool bug.",probable_incorrect_coverage_report:"A stable scored observation contradicts the coverage oracle. Inspect the highlighted statement and the retained raw evidence.",unstable_or_non_reproducible:"Repeated collections differ. Select each collection to inspect the changing observations; this result is not a stable tool-bug claim.",pipeline_failure:"A compilation, execution, parsing, or validation stage failed. Missing tool reports are unavailable observations; inspect the errors before interpreting coverage."};
    $("case-explanation").textContent=descriptions[c.classification] || words(c.classification);
    clear("repeat-select");for(let i=0;i<c.runs;i++){const o=el("option",`Collection ${i+1}`);o.value=String(i);$("repeat-select").append(o);}$("repeat-select").value=String(repeatIndex);
    $("statement-score").textContent=`${c.comparable_lines} comparable lines · first pass`;
    renderSource();renderPair();
    $("repeat-status").textContent=c.stable===true?"Identical saved signatures":c.stable===false?"Saved signatures differ":"Not confirmed";
    clear("outputs");
    for(const [label,output] of [["Oracle",c.expected_output],...tools.map(t=>[t,r.outputs[t]])]){const card=el("div",undefined,"output-card");card.append(el("strong",label),el("pre",output.stdout===null?"Output unavailable":output.stdout===""?"(empty stdout)":output.stdout));const valid=output.stdout===c.expected_output.stdout && output.exit_code===c.expected_output.exit_code;card.append(el("span",`Exit: ${output.exit_code===null?"unavailable":output.exit_code}${label==="Oracle"?"":valid?" · matches oracle":" · does not match oracle"}`,"small "+(label==="Oracle"?"muted":valid?"matched":"mismatch")));$("outputs").append(card);}
    clear("repeat-history");for(let i=0;i<c.runs;i++){const b=el("button",`#${i+1} · ${c.repeats[i].signature.slice(0,14)}…`,"repeat-chip");b.title=c.repeats[i].signature;b.setAttribute("aria-pressed",String(i===repeatIndex));b.addEventListener("click",()=>{repeatIndex=i;renderCase();});$("repeat-history").append(b);}
    clear("errors");for(const error of r.errors)$("errors").append(el("pre",pretty(error),"error"));
    $("review-status").textContent=c.review ? `Evidence audited · ${words(c.review_status)}. ${c.review.decision}` : c.review_status==="pending" ? "Manual review is pending. The saved classification is provisional." : `Review: ${words(c.review_status)}. No separate review overlay supplied.`;
    clear("review-notes");for(const o of c.review?.observations || []){const box=el("div",undefined,"review-observation");box.append(link(`L${o.line}`,caseHash(c.case_id,o.line)),el("strong",words(o.pattern)));if(o.finding)box.append(el("p",typeof o.finding==="string"?o.finding:pretty(o.finding)));$("review-notes").append(box);}
    clear("issue-note");if(c.issue){$("issue-note").append(el("span",`Documented pattern: ${c.issue.id} · ${words(c.issue.role)} fixture. `));if(/^https?:\/\//.test(c.issue.url))$("issue-note").append(link("Upstream issue",c.issue.url));if(c.documented_check)$("issue-note").append(el("pre",pretty(c.documented_check),"raw-data"));}
    $("reproduction-command").value=c.reproduction_command;$("copy-status").textContent="";
    $("branch-evidence").textContent=pretty({mapping_status:data.branch_mapping,comparable_outcomes:0,oracle_semantic_outcomes:c.oracle_branches,raw_tool_evidence:r.branches});
    $("provenance-note").textContent="Frozen measurement environment shown below. Dashboard rendering does not rerun the tools or change the recorded classification. Raw reports and command logs are bundled; instrumented binaries and profiles remain in the original run archive.";
    clear("evidence-links");for(const [name,href]of Object.entries(c.evidence))if(href)$("evidence-links").append(link(name,href));for(const [key,value]of Object.entries(r.evidence)){if(typeof value==="string")$("evidence-links").append(link(`Collection ${repeatIndex+1}: ${key}`,value));else for(const [name,href]of Object.entries(value))if(href)$("evidence-links").append(link(`${key}: ${name}`,href));}
    $("provenance").textContent=pretty({source_sha256:c.source_sha256,parameters:c.parameters,oracle_validation:c.oracle_validation,oracle_trusted_this_collection:r.oracle_trusted,convention_rule_version:suite.summary.convention_rule_version,environment:suite.environment,experiment:suite.context["experiment.json"] || null});
  }
  function readHash() {
    const [suiteId,caseId,line]=location.hash.slice(1).split("/");
    if(suiteId && data.suites.some(s=>s.id===suiteId) && suite.id!==suiteId){resetFilters();chooseSuite(suiteId);}
    const found=suite.cases.find(c=>c.case_id===caseId);if(found){selected=found;repeatIndex=0;resetFilters();targetLine=/^[1-9]\d*$/.test(line || "") ? Number(line) : null;}
    renderList();if(targetLine)$("source-line-"+targetLine)?.scrollIntoView({block:"center"});
  }
  for(const id of ["search","family-filter","class-filter","tool-filter"])$(id).addEventListener(id==="search"?"input":"change",()=>{targetLine=null;renderList();});
  $("reset").addEventListener("click",()=>{resetFilters();renderList();});
  $("repeat-select").addEventListener("change",()=>{repeatIndex=Number($("repeat-select").value);renderCase();});
  $("all-lines").addEventListener("click",()=>{findingsOnly=false;renderSource();});$("findings-only").addEventListener("click",()=>{findingsOnly=true;renderSource();});
  $("copy-command").addEventListener("click",async()=>{const area=$("reproduction-command");try{await navigator.clipboard.writeText(area.value);$("copy-status").textContent="Command copied.";}catch{area.focus();area.select();$("copy-status").textContent="Command selected. Press Ctrl+C (or ⌘C) to copy.";}});
  window.addEventListener("hashchange",readHash);
  chooseSuite(suite.id);readHash();
})();
