(() => {
  "use strict";

  const D = window.DASHBOARD_DATA;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v)) ? "—"
    : Number(v).toLocaleString("pt-BR", {minimumFractionDigits: d, maximumFractionDigits: d});
  const pct = (v, d = 1) => v === null || v === undefined ? "—" : `${fmt(v, d)}%`;
  const signed = (v, d = 1) => v === null || v === undefined ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${fmt(Math.abs(v), d)}`;
  const pval = (p) => p === null || p === undefined ? "—" : p < 0.001 ? "< 0,001" : fmt(p, 3);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

  const FACTOR = Object.fromEntries(D.factors.map((f) => [f.code, f]));
  const EVIDENCE = Object.fromEntries(D.evidence.map((e) => [e.factor_code, e.evidence]));
  const DIM_ORDER = ["Macroeconômico", "Financeiro", "Institucional", "Tecnológico", "Tributário"];
  const corrOf = (design, code) => D.correlations.find((c) => c.design === design && c.factor_code === code);
  const hasBrazil = (design) => D.designs[design].brazil !== undefined;
  const plainName = (f) => f.name.replace(/ \(log\)$/, "").replace(", log)", ")");
  // marcas de eixo em unidades originais para fatores em logaritmo natural
  function logTicks(lo, hi) {
    const a = Math.exp(lo), b = Math.exp(hi);
    const mult = Math.log10(b / a) < 1 ? [1, 1.5, 2, 3, 5, 7] : [1, 2, 5];
    const out = [];
    for (let k = Math.floor(Math.log10(a)); k <= Math.ceil(Math.log10(b)); k++) {
      mult.forEach((m) => { const v = m * 10 ** k; if (v >= a && v <= b) out.push(Number(v.toPrecision(3))); });
    }
    return out;
  }
  const tooltip = $("#tooltip");
  const state = {design: "A1", factor: "log_tax_hours", factorDesign: "A1"};

  // ------------------------------------------------------------------ utilidades
  function showTip(evt, html) {
    tooltip.innerHTML = html;
    tooltip.style.display = "block";
    const x = evt.clientX ?? 0, y = evt.clientY ?? 0;
    tooltip.style.left = `${Math.min(x + 14, window.innerWidth - 250)}px`;
    tooltip.style.top = `${Math.max(8, y - 60)}px`;
  }
  const hideTip = () => { tooltip.style.display = "none"; };
  function bindTip(el, html) {
    el.setAttribute("tabindex", "0");
    el.addEventListener("mousemove", (e) => showTip(e, html));
    el.addEventListener("mouseleave", hideTip);
    el.addEventListener("focus", () => { const r = el.getBoundingClientRect(); showTip({clientX: r.right, clientY: r.top}, html); });
    el.addEventListener("blur", hideTip);
  }
  function svg(tag, attrs = {}, text = "") {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    if (text !== "") el.textContent = text;
    return el;
  }
  const scale = (d0, d1, r0, r1) => (v) => r0 + (v - d0) / ((d1 - d0) || 1) * (r1 - r0);
  function niceStep(span, target = 5) {
    const raw = span / target, mag = 10 ** Math.floor(Math.log10(raw));
    const n = raw / mag;
    return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
  }
  function niceDomain(min, max, target = 5) {
    const step = niceStep(max - min || 1, target);
    return [Math.floor(min / step) * step, Math.ceil(max / step) * step, step];
  }
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function hexToRgb(h) {
    const m = h.replace("#", "");
    return [0, 2, 4].map((i) => parseInt(m.slice(i, i + 2), 16));
  }
  function mix(a, b, t) {
    const A = hexToRgb(a), B = hexToRgb(b);
    return A.map((x, i) => Math.round(x + (B[i] - x) * t));
  }
  const lum = ([r, g, b]) => (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;

  // ------------------------------------------------------------------ abas
  function initTabs() {
    $$(".tab").forEach((b) => b.addEventListener("click", () => {
      $$(".tab").forEach((x) => { x.classList.toggle("is-active", x === b); x.setAttribute("aria-selected", x === b); });
      $$(".tab-panel").forEach((p) => p.classList.toggle("is-active", p.id === b.dataset.tab));
      hideTip();
      if (b.dataset.tab === "panel") renderPanel();
    }));
    let resizeTimer;
    window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if ($("#panel").classList.contains("is-active")) renderPanel(); }, 150); });
  }

  // ------------------------------------------------------------------ resumo
  function renderSummary() {
    const a1 = D.designs.A1, b = D.designs.B, m = D.meta;
    $("#stamp-main").textContent = `${m.factors_total} fatores · ${m.panel.n_countries} países`;
    $("#stamp-sub").textContent = `${m.oecd_rows.toLocaleString("pt-BR")} observações de sobrevivência (OCDE) · fatores de 2011–2016 · ${m.factors_tested} fatores com cobertura suficiente para teste`;
    $("#kpi-a1").textContent = pct(a1.brazil);
    $("#kpi-a1-sub").textContent = `${a1.brazil_rank}º de ${a1.n} · mediana OCDE ${pct(a1.oecd_median)}`;
    $("#kpi-b").textContent = pct(b.brazil);
    $("#kpi-b-sub").textContent = `${b.brazil_rank}º de ${b.n} · mediana OCDE ${pct(b.oecd_median)}`;
    const tested = new Set(D.correlations.filter((c) => c.pearson_r !== null).map((c) => c.factor_code));
    const robust = [...tested].filter((c) => EVIDENCE[c] === "Robusta");
    const sugg = [...tested].filter((c) => EVIDENCE[c] === "Sugestiva").map((c) => FACTOR[c].name.replace(/ \(log\)$/, ""));
    $("#kpi-robust").textContent = `${robust.length} de ${tested.size}`;
    $("#kpi-robust-sub").textContent = sugg.length ? `Fatores testados · ${sugg.length} sugestiva${sugg.length > 1 ? "s" : ""}: ${sugg.join(", ").toLowerCase()}` : "Fatores testados · nenhuma associação sugestiva";
    // dimensão do conjunto de testes (correlações por recorte + painel)
    const corrTests = D.correlations.filter((c) => c.pearson_r !== null);
    const panelTests = D.panel_models.filter((r) => r.pooled_beta_pp_per_sd !== null);
    const nTests = corrTests.length + panelTests.length;
    const nSig = corrTests.filter((c) => c.pearson_p < 0.05).length + panelTests.filter((r) => r.pooled_p < 0.05).length;
    const minQ = Math.min(...corrTests.map((c) => c.pearson_q_bh), ...panelTests.map((r) => r.pooled_q_bh));
    const untested = D.factors.filter((f) => !tested.has(f.code)).map((f) => f.name.toLowerCase());
    $("#factors-intro").textContent = `Os ${m.factors_total} indicadores são medidos antes do nascimento das empresas` +
      (untested.length ? `; ${tested.size} têm cobertura suficiente para teste (sem cobertura: ${untested.join(", ")}). ` : ". ") +
      "Uma associação só merece destaque se aparecer com o mesmo sinal em todos os recortes.";
    $("#tests-note").innerHTML = `<strong>Leia antes de interpretar.</strong> Foram ${nTests} testes (${tested.size} fatores em ${D.design_order.length} recortes e no painel). ` +
      `${nSig} tiveram p &lt; 0,05; só por acaso, seriam esperados cerca de ${Math.round(nTests * 0.05)}. ` +
      (minQ >= 0.1 ? `Nenhum permanece significativo após a correção de Benjamini–Hochberg (menor q = ${fmt(minQ, 2)}). ` : "") +
      "Os recortes usam os mesmos países e, em parte, os mesmos dados: não são confirmações independentes.";
    $("#kpi-panel").textContent = `${m.panel.n_obs} coortes`;
    $("#kpi-panel-sub").textContent = `${m.panel.n_countries} países · coortes ${m.panel.cohorts[0]}–${m.panel.cohorts.at(-1)}`;
    const [y, mo, d] = m.updated.split("-");
    $("#footer-date").textContent = `Dados: OCDE, IBGE e Banco Mundial · coletados em ${d}/${mo}/${y}`;
  }

  // ------------------------------------------------------------------ comparação
  function initComparison() {
    const box = $("#design-select");
    box.innerHTML = D.design_order.map((k) => `<button class="seg${k === state.design ? " is-active" : ""}" role="radio" aria-checked="${k === state.design}" data-design="${k}">${esc(D.designs[k].label)}</button>`).join("");
    box.addEventListener("click", (e) => {
      const btn = e.target.closest(".seg");
      if (!btn) return;
      state.design = btn.dataset.design;
      $$("#design-select .seg").forEach((s) => { const on = s === btn; s.classList.toggle("is-active", on); s.setAttribute("aria-checked", on); });
      renderComparison();
    });
    renderComparison();
  }

  function renderComparison() {
    const d = D.designs[state.design];
    $("#ranking-title").textContent = d.label;
    $("#ranking-sub").textContent = d.outcome;
    const max = Math.max(...d.rows.map((r) => r.survival_rate_pct));
    const medPos = d.oecd_median / max * 100;
    const chart = $("#ranking-chart");
    chart.innerHTML = d.rows.map((r) => `
      <div class="rank-row${r.country_code === "BRA" ? " is-brazil" : ""}" data-code="${r.country_code}">
        <span class="rank-number">${r.rank}</span>
        <span class="rank-country" title="${esc(r.country_name_pt)}">${esc(r.country_name_pt)}${(d.flags || []).includes(r.country_code) ? "*" : ""}</span>
        <span class="rank-track"><i class="rank-bar" style="width:${r.survival_rate_pct / max * 100}%"></i><i class="rank-median" style="left:${medPos}%"></i></span>
        <span class="rank-value">${fmt(r.survival_rate_pct)}</span>
      </div>`).join("");
    $$("#ranking-chart .rank-row").forEach((row) => {
      const r = d.rows.find((x) => x.country_code === row.dataset.code);
      bindTip(row, `<strong>${esc(r.country_name_pt)}</strong><br>${pct(r.survival_rate_pct)} · ${r.rank}º de ${d.n}<br>Mediana OCDE: ${pct(d.oecd_median)}${(d.flags || []).includes(r.country_code) ? "<br>* Valor muito baixo: possível quebra de série" : ""}`);
    });

    $("#design-n").textContent = `${d.n}`;
    $("#observed-range").textContent = `${pct(d.min)} – ${pct(d.max)}`;
    $("#design-note").textContent = d.note;
    if (d.brazil !== undefined) {
      const gap = d.brazil - d.oecd_median;
      $("#median-gap").textContent = `${signed(gap)} p.p.`;
      $("#comparison-headline").textContent = gap < 0
        ? `Brasil ${fmt(Math.abs(gap))} p.p. abaixo da mediana da OCDE`
        : `Brasil ${fmt(gap)} p.p. acima da mediana da OCDE`;
      const other = state.design === "A1" ? D.designs.B : D.designs.A1;
      const otherGap = other.brazil - other.oecd_median;
      $("#comparison-text").textContent = `${d.brazil_rank}º lugar entre ${d.n} países, com ${pct(d.brazil)}. ` +
        `No recorte “${other.label}”, o Brasil fica ${otherGap < 0 ? "abaixo" : "acima"} da mediana (${signed(otherGap)} p.p.). ` +
        "A diferença vem da fonte usada para o Brasil (veja a aba Brasil: IBGE × OCDE).";
    } else {
      $("#median-gap").textContent = "—";
      $("#comparison-headline").textContent = "O Brasil não entra neste recorte";
      $("#comparison-text").textContent = `O recorte compara ${d.n} países da OCDE. Mediana: ${pct(d.oecd_median)}. Ele serve para testar se as associações com os fatores se mantêm.`;
    }
  }

  // ------------------------------------------------------------------ fatores
  function initFactors() {
    const sel = $("#factor-select");
    const groups = DIM_ORDER.map((dim) => {
      const opts = D.factors.filter((f) => f.dimension === dim).map((f) => `<option value="${f.code}">${esc(f.name)}</option>`).join("");
      return `<optgroup label="${dim}">${opts}</optgroup>`;
    });
    sel.innerHTML = groups.join("");
    sel.value = state.factor;
    const ds = $("#factor-design");
    ds.innerHTML = D.design_order.map((k) => `<option value="${k}">${esc(D.designs[k].label)} · ${hasBrazil(k) ? "com" : "sem"} o Brasil</option>`).join("");
    sel.addEventListener("change", () => { state.factor = sel.value; renderFactor(); });
    ds.addEventListener("change", () => { state.factorDesign = ds.value; renderFactor(); });
    renderHeatmap();
    renderFactor();
  }

  function renderFactor() {
    const f = FACTOR[state.factor], d = D.designs[state.factorDesign];
    const c = corrOf(state.factorDesign, state.factor) || {};
    const fv = D.factor_windows[d.window][state.factor] || {};
    const pts = d.rows.filter((r) => fv[r.country_code] !== undefined && fv[r.country_code] !== null)
      .map((r) => ({...r, x: fv[r.country_code], y: r.survival_rate_pct}));
    const [w0, w1] = d.window.split("_");
    const isLog = f.transform === "log";
    const fName = plainName(f), fUnit = f.unit.replace(/^log /, "");
    const xVal = (x) => isLog ? `${fmt(Math.exp(x), Math.exp(x) < 10 ? 1 : 0)} ${fUnit}` : `${fmt(x, 2)} ${fUnit}`;
    $("#scatter-title").textContent = fName;
    $("#scatter-sub").textContent = `${d.outcome} × ${fName.toLowerCase()} (média ${w0}–${w1}, ${fUnit})`;
    $("#metric-pearson").textContent = c.pearson_r == null ? "—" : signed(c.pearson_r, 2);
    $("#metric-spearman").textContent = c.spearman_rho == null ? "—" : signed(c.spearman_rho, 2);
    $("#metric-spearman-p").textContent = c.spearman_p == null ? "" : `p = ${pval(c.spearman_p)}`;
    $("#metric-n").textContent = c.n ?? pts.length;
    $("#metric-p").textContent = pval(c.pearson_p);
    $("#metric-q").textContent = pval(c.pearson_q_bh);
    $("#metric-evidence").textContent = EVIDENCE[state.factor] || "—";
    $$("#heatmap tbody tr").forEach((tr) => tr.classList.toggle("is-selected", tr.dataset.code === state.factor));

    const W = 720, H = 400, M = {left: 56, right: 20, top: 16, bottom: 50};
    const root = svg("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Dispersão: ${f.name} e sobrevivência`});
    if (pts.length < 3) {
      root.append(svg("text", {x: W / 2, y: H / 2, "text-anchor": "middle", class: "axis-label"}, "Cobertura insuficiente para este fator neste recorte"));
      $("#scatter-chart").replaceChildren(root);
      $("#stability-note").textContent = `Apenas ${pts.length} países com dado. Correlações exigem pelo menos 15.`;
      return;
    }
    const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
    const xPad = (Math.max(...xs) - Math.min(...xs)) * 0.05 || 0.1;
    const [x0, x1, xs_] = isLog ? [Math.min(...xs) - xPad, Math.max(...xs) + xPad, 1] : niceDomain(Math.min(...xs), Math.max(...xs), 6);
    const [y0, y1, ys_] = niceDomain(Math.min(...ys), Math.max(...ys), 5);
    const sx = scale(x0, x1, M.left, W - M.right), sy = scale(y0, y1, H - M.bottom, M.top);
    for (let t = y0; t <= y1 + 1e-9; t += ys_) {
      root.append(svg("line", {x1: M.left, x2: W - M.right, y1: sy(t), y2: sy(t), class: "gridline"}));
      root.append(svg("text", {x: M.left - 8, y: sy(t) + 4, "text-anchor": "end", class: "tick-label"}, `${fmt(t, 0)}%`));
    }
    const xd = xs_ < 1 ? (xs_ < 0.1 ? 2 : 1) : 0;
    if (isLog) {
      logTicks(x0, x1).forEach((v) => {
        root.append(svg("line", {x1: sx(Math.log(v)), x2: sx(Math.log(v)), y1: H - M.bottom, y2: H - M.bottom + 5, class: "axis"}));
        root.append(svg("text", {x: sx(Math.log(v)), y: H - M.bottom + 18, "text-anchor": "middle", class: "tick-label"}, fmt(v, v < 10 && !Number.isInteger(v) ? 1 : 0)));
      });
    } else {
      for (let t = x0; t <= x1 + 1e-9; t += xs_) {
        root.append(svg("text", {x: sx(t), y: H - M.bottom + 18, "text-anchor": "middle", class: "tick-label"}, fmt(t, xd)));
      }
    }
    root.append(svg("line", {x1: M.left, x2: W - M.right, y1: H - M.bottom, y2: H - M.bottom, class: "axis"}));
    root.append(svg("text", {x: (M.left + W - M.right) / 2, y: H - 10, "text-anchor": "middle", class: "axis-label"}, `${fName} (${fUnit}${isLog ? ", escala logarítmica" : ""})`));
    root.append(svg("text", {x: 14, y: (H - M.bottom + M.top) / 2, transform: `rotate(-90 14 ${(H - M.bottom + M.top) / 2})`, "text-anchor": "middle", class: "axis-label"}, d.age === 2 ? "Sobrevivência em 2 anos (%)" : "Sobrevivência em 3 anos (%)"));
    // reta de mínimos quadrados
    const mx = xs.reduce((a, b) => a + b) / xs.length, my = ys.reduce((a, b) => a + b) / ys.length;
    const slope = pts.reduce((a, p) => a + (p.x - mx) * (p.y - my), 0) / pts.reduce((a, p) => a + (p.x - mx) ** 2, 0);
    // traço cheio na faixa observada nos países da OCDE; tracejado no trecho que só existe por causa do Brasil
    const xo = pts.filter((p) => p.country_code !== "BRA").map((p) => p.x);
    const xa = Math.min(...xo), xb = Math.max(...xo), fa = Math.min(...xs), fb = Math.max(...xs);
    const fit = (x) => sy(my + slope * (x - mx));
    const seg = (a, b, cls) => root.append(svg("line", {x1: sx(a), y1: fit(a), x2: sx(b), y2: fit(b), class: cls}));
    seg(xa, xb, "regression");
    if (fa < xa) seg(fa, xa, "regression regression--extra");
    if (fb > xb) seg(xb, fb, "regression regression--extra");
    const extrapolated = fa < xa || fb > xb;
    pts.sort((a, b) => (a.country_code === "BRA") - (b.country_code === "BRA")).forEach((p) => {
      const g = svg("g");
      const hit = svg("circle", {cx: sx(p.x), cy: sy(p.y), r: 12, class: "hit"});
      const dot = svg("circle", {cx: sx(p.x), cy: sy(p.y), r: p.country_code === "BRA" ? 6.5 : 5, class: `point${p.country_code === "BRA" ? " point--brazil" : ""}`});
      bindTip(hit, `<strong>${esc(p.country_name_pt)}</strong><br>${esc(fName)}: ${xVal(p.x)}<br>Sobrevivência: ${pct(p.y)}`);
      g.append(hit, dot);
      if (p.country_code === "BRA") g.append(svg("text", {x: sx(p.x) + 10, y: sy(p.y) - 9, class: "data-label"}, "Brasil"));
      root.append(g);
    });
    $("#scatter-chart").replaceChildren(root);
    const loo = c.loo_pearson_min == null ? "" : `Retirando um país por vez, r varia entre ${signed(c.loo_pearson_min, 2)} e ${signed(c.loo_pearson_max, 2)}. `;
    const bra = pts.some((p) => p.country_code === "BRA") ? "O Brasil está incluído neste recorte." : "O Brasil não entra neste recorte.";
    const trans = isLog ? " O eixo horizontal está em escala logarítmica; a correlação foi calculada com o logaritmo do indicador." : "";
    const extra = extrapolated ? " A reta usa todos os países do recorte; o trecho tracejado está fora da faixa observada na OCDE e depende só do Brasil." : "";
    const db = /Doing Business/.test(f.source) ? " Indicador do Doing Business: refere-se a uma empresa hipotética padronizada, e a série foi descontinuada em 2021." : "";
    $("#stability-note").textContent = `${loo}${bra}${extra}${trans} Sinal esperado pela literatura: ${f.expected === "?" ? "ambíguo" : f.expected === "+" ? "positivo" : "negativo"}.${db}`;
  }

  function renderHeatmap() {
    const teal = cssVar("--teal"), orange = cssVar("--orange"), neutral = cssVar("--neutral-cell");
    const cols = D.design_order;
    $("#heatmap thead").innerHTML = `<tr><th>Fator</th><th>Dimensão</th>${cols.map((k) => `<th title="${esc(D.designs[k].outcome)}">${esc(D.designs[k].short)}<small>${hasBrazil(k) ? "com Brasil" : "sem Brasil"}</small></th>`).join("")}<th class="panel-col" title="Painel país × coorte: variação da sobrevivência em 3 anos, em p.p., por 1 desvio-padrão do fator">Painel<small>p.p./DP · sem Brasil</small></th><th>Classificação</th></tr>`;
    const factors = [...D.factors].sort((a, b) => DIM_ORDER.indexOf(a.dimension) - DIM_ORDER.indexOf(b.dimension));
    const badgeClass = {"Robusta": "robusta", "Sugestiva": "sugestiva", "Mesmo sinal, sem significância": "sinal", "Inconsistente": "inconsistente"};
    $("#heatmap tbody").innerHTML = factors.map((f) => {
      const cells = cols.map((k) => {
        const c = corrOf(k, f.code);
        if (!c || c.pearson_r === null) return `<td class="cell" title="n = ${c ? c.n : 0}: cobertura insuficiente">—</td>`;
        const t = Math.min(Math.abs(c.pearson_r) / 0.5, 1);
        const rgb = mix(neutral, c.pearson_r >= 0 ? teal : orange, t * 0.9);
        const ink = lum(rgb) > 0.55 ? "#112a2a" : "#ffffff";
        const sig = c.pearson_p < 0.05;
        return `<td class="cell${sig ? " sig" : ""}" style="background:rgb(${rgb});color:${ink}" title="${esc(D.designs[k].label)} · r = ${signed(c.pearson_r, 2)} · p = ${pval(c.pearson_p)} · n = ${c.n}">${signed(c.pearson_r, 2)}${sig ? "*" : ""}</td>`;
      }).join("");
      const pm = D.panel_models.find((r) => r.factor_code === f.code);
      const pcell = (!pm || pm.pooled_beta_pp_per_sd === null) ? `<td class="cell panel-col">—</td>`
        : `<td class="cell panel-col${pm.pooled_p < 0.05 ? " sig" : ""}" title="Painel · β = ${signed(pm.pooled_beta_pp_per_sd, 2)} p.p. por DP · p = ${pval(pm.pooled_p)} · q = ${pval(pm.pooled_q_bh)} · ${pm.n_obs} obs.">${signed(pm.pooled_beta_pp_per_sd, 1)}${pm.pooled_p < 0.05 ? "*" : ""}</td>`;
      const ev = EVIDENCE[f.code];
      const nOk = D.correlations.some((c) => c.factor_code === f.code && c.pearson_r !== null);
      const badge = nOk ? `<span class="badge badge--${badgeClass[ev]}">${ev === "Mesmo sinal, sem significância" ? "Mesmo sinal" : ev}</span>` : `<span class="badge">Sem cobertura</span>`;
      return `<tr data-code="${f.code}"><td>${esc(f.name)}</td><td class="dim">${f.dimension}</td>${cells}${pcell}<td class="ev">${badge}</td></tr>`;
    }).join("");
    $$("#heatmap tbody tr").forEach((tr) => tr.addEventListener("click", () => {
      state.factor = tr.dataset.code;
      $("#factor-select").value = state.factor;
      renderFactor();
      $("#factor-select").scrollIntoView({behavior: "smooth", block: "center"});
    }));
  }

  // ------------------------------------------------------------------ painel
  function forest(container, rows, opts) {
    const W = Math.max(container.clientWidth || 720, 320);
    const labelW = Math.min(opts.labelW, Math.round(W * 0.5));
    const rowH = 27, M = {left: labelW, right: 24, top: 10, bottom: 44};
    const H = M.top + rows.length * rowH + M.bottom;
    const lim = Math.max(...rows.flatMap((r) => [Math.abs(r.lo), Math.abs(r.hi)]));
    const [d0, d1, step] = niceDomain(-lim, lim, 6);
    const sx = scale(d0, d1, M.left, W - M.right);
    const root = svg("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": opts.aria});
    for (let t = d0; t <= d1 + 1e-9; t += step) {
      root.append(svg("line", {x1: sx(t), x2: sx(t), y1: M.top, y2: H - M.bottom, class: t === 0 ? "zero-line" : "gridline"}));
      root.append(svg("text", {x: sx(t), y: H - M.bottom + 16, "text-anchor": "middle", class: "tick-label"}, signed(t, step < 1 ? 1 : 0)));
    }
    root.append(svg("text", {x: (M.left + W - M.right) / 2, y: H - 8, "text-anchor": "middle", class: "axis-label"}, "p.p. de sobrevivência em 3 anos por 1 desvio-padrão"));
    rows.forEach((r, i) => {
      const y = M.top + i * rowH + rowH / 2;
      const sig = r.p < 0.05;
      root.append(svg("text", {x: 0, y: y + 4, class: "row-label"}, r.label));
      root.append(svg("line", {x1: sx(r.lo), x2: sx(r.hi), y1: y, y2: y, class: `ci${sig ? " ci--sig" : ""}`}));
      const g = svg("g");
      const hit = svg("rect", {x: M.left, y: y - rowH / 2, width: W - M.left - M.right, height: rowH, class: "hit"});
      const dot = svg("circle", {cx: sx(r.b), cy: y, r: 5.5, class: `est${sig ? " est--sig" : ""}`});
      bindTip(hit, `<strong>${esc(r.label)}</strong>${r.dim ? ` · ${r.dim}` : ""}<br>β = ${signed(r.b, 2)} p.p. por DP<br>IC 95%: ${signed(r.lo, 2)} a ${signed(r.hi, 2)}<br>p = ${pval(r.p)}${r.extra ? `<br>${r.extra}` : ""}`);
      g.append(hit, dot);
      root.append(g);
    });
    container.replaceChildren(root);
  }

  function renderPanel() {
    const m = D.meta;
    $("#panel-intro").textContent = `${m.panel.n_obs} observações país × coorte (${m.panel.n_countries} países, coortes ${m.panel.cohorts[0]}–${m.panel.cohorts.at(-1)}). Cada fator é a média dos 3 anos anteriores ao nascimento da coorte. Há efeitos fixos de coorte e erros-padrão agrupados por país. O Brasil não integra o painel.`;
    const pq = D.panel_models.filter((r) => r.pooled_beta_pp_per_sd !== null);
    const pSig = pq.filter((r) => r.pooled_p < 0.05).length, pMinQ = Math.min(...pq.map((r) => r.pooled_q_bh));
    $("#panel-note").textContent = `${pSig} de ${pq.length} coeficientes ${pSig === 1 ? "tem" : "têm"} p < 0,05` +
      (pMinQ >= 0.1 ? `; nenhum permanece significativo após a correção para múltiplos testes (menor q = ${fmt(pMinQ, 2)}). ` : ". ") +
      "Como só há efeitos fixos de coorte, as estimativas refletem diferenças entre países, e não variações ao longo do tempo em cada país.";
    const rows = D.panel_models.filter((r) => r.pooled_beta_pp_per_sd !== null)
      .map((r) => ({label: FACTOR[r.factor_code].name, dim: FACTOR[r.factor_code].dimension, b: r.pooled_beta_pp_per_sd, lo: r.pooled_ci_low, hi: r.pooled_ci_high, p: r.pooled_p,
        extra: `q-BH = ${pval(r.pooled_q_bh)} · ${r.n_obs} obs., ${r.n_countries} países`}))
      .sort((a, b) => a.b - b.b);
    forest($("#forest-chart"), rows, {labelW: 290, aria: "Coeficientes do painel por fator"});
    $("#multi-sub").textContent = `${m.multivariate.n_obs} observações · ${m.multivariate.n_countries} países · R² = ${fmt(m.multivariate.r2, 2)}`;
    const mrows = D.panel_multivariate.map((r) => ({label: FACTOR[r.factor_code].name, b: r.beta_pp_per_sd, lo: r.ci_low, hi: r.ci_high, p: r.p_value, extra: `VIF = ${fmt(r.vif, 1)}`}))
      .sort((a, b) => a.b - b.b);
    forest($("#multi-chart"), mrows, {labelW: 265, aria: "Coeficientes do modelo conjunto"});
  }

  // ------------------------------------------------------------------ Brasil
  function renderBrazil() {
    const B = D.brazil;
    const ibge = B.ibge_curve.map((r) => ({x: r.survival_age_years, y: r.survival_rate_pct}));
    const oecdBra = B.oecd_series.filter((r) => r.cohort_year === 2017).map((r) => ({x: r.age_years, y: r.survival_rate_pct})).sort((a, b) => a.x - b.x);
    const med = B.oecd_median_by_year.filter((r) => r.reference_year - r.age_years === 2017).map((r) => ({x: r.age_years, y: r.oecd_median})).sort((a, b) => a.x - b.x);
    const W = 720, H = 380, M = {left: 52, right: 90, top: 20, bottom: 46};
    const allY = [...ibge, ...oecdBra, ...med].map((p) => p.y);
    const [y0, y1, st] = niceDomain(Math.min(...allY) - 2, Math.max(...allY) + 2, 5);
    const sx = scale(1, 5, M.left, W - M.right), sy = scale(y0, y1, H - M.bottom, M.top);
    const root = svg("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Sobrevivência da coorte de 2017 no Brasil segundo IBGE e OCDE"});
    for (let t = y0; t <= y1 + 1e-9; t += st) {
      root.append(svg("line", {x1: M.left, x2: W - M.right, y1: sy(t), y2: sy(t), class: "gridline"}));
      root.append(svg("text", {x: M.left - 8, y: sy(t) + 4, "text-anchor": "end", class: "tick-label"}, `${fmt(t, 0)}%`));
    }
    [1, 2, 3, 4, 5].forEach((a) => root.append(svg("text", {x: sx(a), y: H - M.bottom + 20, "text-anchor": "middle", class: "tick-label"}, `${a} ano${a > 1 ? "s" : ""}`)));
    const line = (pts) => pts.map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ");
    root.append(svg("polygon", {points: `${sx(1)},${sy(y0)} ${line(ibge)} ${sx(5)},${sy(y0)}`, class: "curve-area"}));
    root.append(svg("polyline", {points: line(med), class: "median-line"}));
    root.append(svg("polyline", {points: line(oecdBra), class: "oecd-line"}));
    root.append(svg("polyline", {points: line(ibge), class: "curve-line"}));
    const dots = (pts, cls, name) => pts.forEach((p) => {
      const g = svg("g");
      const hit = svg("circle", {cx: sx(p.x), cy: sy(p.y), r: 12, class: "hit"});
      bindTip(hit, `<strong>${name}</strong><br>${p.x} ano${p.x > 1 ? "s" : ""}: ${pct(p.y)}`);
      g.append(hit, svg("circle", {cx: sx(p.x), cy: sy(p.y), r: 5, class: cls}));
      root.append(g);
    });
    dots(med, "dot-median", "Mediana OCDE");
    dots(oecdBra, "dot-oecd", "Brasil · OCDE");
    dots(ibge, "dot-brazil", "Brasil · IBGE");
    // rótulos seletivos: ponto de divergência (2 anos) e final de cada série
    const lab = (p, text, dy = -12, anchor = "middle") => root.append(svg("text", {x: sx(p.x), y: sy(p.y) + dy, "text-anchor": anchor, class: "data-label"}, text));
    const o2 = oecdBra.find((p) => p.x === 2), i2 = ibge.find((p) => p.x === 2);
    if (o2) lab(o2, `${pct(o2.y)} OCDE`, -12, "start");
    if (i2) lab(i2, `${pct(i2.y)} IBGE`, 20, "start");
    const iEnd = ibge.at(-1);
    root.append(svg("text", {x: sx(iEnd.x) + 10, y: sy(iEnd.y) + 4, class: "data-label"}, pct(iEnd.y)));
    const mEnd = med.at(-1);
    if (mEnd) root.append(svg("text", {x: sx(mEnd.x) + 10, y: sy(mEnd.y) + 4, class: "data-label"}, `${pct(mEnd.y)} mediana`));
    $("#brazil-curve").replaceChildren(root);

    const dv = B.divergence;
    const d2 = dv.find((r) => r.age_years === 2);
    $("#div-headline").textContent = `${fmt(d2.diff_pp)} p.p. de diferença em 2 anos`;
    $("#div-text").textContent = `No 1º ano, IBGE e OCDE praticamente coincidem. No 2º ano, a OCDE registra ${pct(d2.oecd_pct)} e o IBGE, ${pct(d2.ibge_pct)}. A OCDE não publica 3 anos para o Brasil, por isso o ranking de 3 anos usa o IBGE.`;
    $("#div-table").innerHTML = `<div class="horizon head"><span>Idade</span><span>IBGE</span><span>OCDE</span><span>Dif.</span></div>` +
      dv.map((r) => `<div class="horizon"><span>${r.age_years} ano${r.age_years > 1 ? "s" : ""}</span><span>${pct(r.ibge_pct)}</span><span>${pct(r.oecd_pct)}</span><strong>${r.diff_pp == null ? "—" : signed(r.diff_pp)}</strong></div>`).join("");

    // pequenos múltiplos: Brasil (OCDE) × mediana OCDE por ano
    const panels = [1, 2].map((age) => {
      const bra = B.oecd_series.filter((r) => r.age_years === age).map((r) => ({x: r.reference_year, y: r.survival_rate_pct})).sort((a, b) => a.x - b.x);
      const years = new Set(bra.map((p) => p.x));
      const md = B.oecd_median_by_year.filter((r) => r.age_years === age && years.has(r.reference_year)).map((r) => ({x: r.reference_year, y: r.oecd_median})).sort((a, b) => a.x - b.x);
      return {age, bra, md};
    });
    const ally = panels.flatMap((p) => [...p.bra, ...p.md]).map((p) => p.y);
    const allx = panels.flatMap((p) => p.bra.map((q) => q.x));
    const [my0, my1, mst] = niceDomain(Math.min(...ally) - 2, Math.max(...ally) + 2, 4);
    const host = $("#brazil-multiples");
    host.replaceChildren(...panels.map((p) => {
      const wrap = document.createElement("div");
      wrap.innerHTML = `<h4>Sobrevivência em ${p.age} ano${p.age > 1 ? "s" : ""}</h4>`;
      const w = 520, h = 250, m = {left: 44, right: 16, top: 12, bottom: 30};
      const fx = scale(Math.min(...allx), Math.max(...allx), m.left, w - m.right), fy = scale(my0, my1, h - m.bottom, m.top);
      const s = svg("svg", {viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": `Brasil e mediana OCDE, ${p.age} ano(s)`});
      for (let t = my0; t <= my1 + 1e-9; t += mst) {
        s.append(svg("line", {x1: m.left, x2: w - m.right, y1: fy(t), y2: fy(t), class: "gridline"}));
        s.append(svg("text", {x: m.left - 6, y: fy(t) + 4, "text-anchor": "end", class: "tick-label"}, `${fmt(t, 0)}%`));
      }
      for (let yr = Math.min(...allx); yr <= Math.max(...allx); yr += 2) s.append(svg("text", {x: fx(yr), y: h - 10, "text-anchor": "middle", class: "tick-label"}, yr));
      const ln = (pts) => pts.map((q) => `${fx(q.x)},${fy(q.y)}`).join(" ");
      s.append(svg("polyline", {points: ln(p.md), class: "median-line"}));
      s.append(svg("polyline", {points: ln(p.bra), class: "oecd-line"}));
      p.bra.forEach((q) => {
        const medv = p.md.find((z) => z.x === q.x);
        const g = svg("g");
        const hit = svg("circle", {cx: fx(q.x), cy: fy(q.y), r: 11, class: "hit"});
        bindTip(hit, `<strong>${q.x}</strong> · coorte ${q.x - p.age}<br>Brasil (OCDE): ${pct(q.y)}<br>Mediana OCDE: ${pct(medv?.y)}`);
        g.append(hit, svg("circle", {cx: fx(q.x), cy: fy(q.y), r: 4, class: "dot-oecd"}));
        s.append(g);
      });
      wrap.append(s);
      return wrap;
    }));
  }

  // ------------------------------------------------------------------ método
  function renderMethod() {
    const total = D.coverage.length;
    $("#coverage-table thead").innerHTML = `<tr><th>Fator</th><th>Dimensão</th><th>Países com dado</th><th>Ausentes</th></tr>`;
    $("#coverage-table tbody").innerHTML = [...D.factors].sort((a, b) => DIM_ORDER.indexOf(a.dimension) - DIM_ORDER.indexOf(b.dimension)).map((f) => {
      const missing = D.coverage.filter((r) => !r[f.code]).map((r) => r.country_name_pt);
      const n = total - missing.length;
      return `<tr><td>${esc(f.name)}</td><td class="dim">${f.dimension}</td><td class="cov"><span class="cov-track"><i style="width:${n / total * 100}%"></i></span><b>${n}/${total}</b></td><td class="miss">${missing.length ? esc(missing.join(", ")) : "—"}</td></tr>`;
    }).join("");
    $("#design-list").innerHTML = D.design_order.map((k) => {
      const d = D.designs[k];
      return `<li><strong>${esc(d.short)} · ${esc(d.label)}</strong><span>${esc(d.outcome)}. Fatores: média ${d.window.replace("_", "–")}. ${esc(d.note)}</span></li>`;
    }).join("") + `<li><strong>Painel país × coorte</strong><span>${D.meta.panel.n_obs} observações; fator = média dos 3 anos anteriores à coorte; efeitos fixos de coorte; erros agrupados por país.</span></li>`;
    $("#source-links").innerHTML = D.sources.map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${esc(s.label)} ↗</a>`).join("");
  }

  initTabs();
  renderSummary();
  initComparison();
  initFactors();
  renderPanel();
  renderBrazil();
  renderMethod();
})();
