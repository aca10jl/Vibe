/*
 * app.js — “一键一生”主界面控制器
 * 管理场景表单、提交执行、图表渲染，并向 AgentTools 暴露 app API。
 */
(function (global) {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = { data: null, activeView: 'config' };

  // ---------- 场景表单 ----------
  function fillSelect(id, items, withEmpty) {
    const el = $(id);
    el.innerHTML = (withEmpty ? '<option value="">自动/全部</option>' : '') +
      items.map(v => `<option value="${v}">${v}</option>`).join('');
  }

  function initForm() {
    fillSelect('cfgFab', WaferData.FABS, true);
    fillSelect('cfgNode', WaferData.NODES, true);
    fillSelect('cfgProduct', WaferData.PRODUCTS, true);
    // 习惯埋点
    ['cfgWaferId', 'cfgFab', 'cfgNode', 'cfgProduct', 'cfgSignature', 'cfgTimeRange'].forEach(id => {
      $(id).addEventListener('change', () => {
        const field = id.replace('cfg', '').charAt(0).toLowerCase() + id.replace('cfg', '').slice(1);
        HabitProfile.track('config_change', { field, value: $(id).value });
        updateReadiness();
      });
    });
    $('cfgWaferId').addEventListener('input', updateReadiness);
    document.querySelectorAll('input[name="analysisDim"]').forEach(c =>
      c.addEventListener('change', () => { if (c.checked) HabitProfile.track('analysis_dim', { dim: c.value }); updateReadiness(); }));
    document.querySelectorAll('input[name="presentation"]').forEach(c => c.addEventListener('change', updateReadiness));

    $('btnRun').onclick = runLifecycle;
    $('btnDemo').onclick = () => { setScenario({ waferId: 'W-2026-0512-07', fab: 'Fab12-A', node: '14nm', product: 'NPU-X2' }); setAnalysisDims(['equipment', 'process', 'param', 'defect']); runLifecycle(); };
    updateReadiness();
  }

  function updateReadiness() {
    const ctx = ContextCollector.collect(state);
    const v = ctx.validation;
    $('readyBar').style.width = v.completeness + '%';
    $('readyText').textContent = v.completeness + '% · ' + (v.ready ? '可提交' : '待补全');
    $('readyBar').className = 'ready-bar ' + (v.ready ? 'ok' : 'warn');
    const issuesEl = $('cfgIssues');
    if (v.issues.length) {
      issuesEl.innerHTML = v.issues.map(i => `<li class="${i.level}">${i.level === 'error' ? '🔴' : '🟡'} ${i.msg}</li>`).join('');
    } else issuesEl.innerHTML = '<li class="ok">✅ 场景已就绪</li>';
    $('btnRun').disabled = !v.ready;
  }

  // ---------- 执行一键一生 ----------
  function runLifecycle() {
    const ctx = ContextCollector.collect(state);
    if (!ctx.validation.ready) { updateReadiness(); if (global.Wizard) { Wizard.enterConfigMode(); Wizard.goTo(4); } flash('btnRun'); return { ok: false, error: '场景未就绪' }; }
    const s = ctx.scenario;
    state.data = WaferData.generateLifecycle({
      waferId: s.waferId, fab: s.fab || undefined, node: s.node || undefined,
      product: s.product || undefined, signature: s.signature || undefined,
    });
    state.activeView = 'result';
    HabitProfile.track('submit_task', { waferId: s.waferId, signature: state.data.summary.signature });
    renderResult();
    document.body.classList.add('has-result');
    if (global.Wizard) Wizard.enterResultMode();
    // 让 AI 自动伴读
    setTimeout(() => global.Assistant && Assistant.autoCompanionAfterRun(), 350);
    return { ok: true, waferId: s.waferId, finalYield: state.data.summary.finalYield };
  }

  function renderResult() {
    const d = state.data;
    $('resultWrap').style.display = 'block';
    $('emptyState').style.display = 'none';
    // 头部摘要
    $('rsWafer').textContent = d.meta.waferId;
    $('rsMeta').textContent = `${d.meta.fab} · ${d.meta.node} · ${d.meta.product} · slot ${d.meta.slot}`;
    $('rsYield').textContent = d.summary.finalYield + '%';
    $('rsYield').className = 'kpi-val ' + (d.summary.finalYield < 75 ? 'bad' : d.summary.finalYield < 88 ? 'mid' : 'good');
    $('rsSig').textContent = d.summary.signatureName;
    $('rsTool').textContent = d.summary.suspectTool;
    $('rsDie').textContent = d.summary.dieTotal;

    // 根因候选
    const cand = WaferData.computeCommonality(d);
    $('rootCauseList').innerHTML = cand.map((c, i) => `
      <div class="rc-item ${i === 0 ? 'top' : ''}">
        <div class="rc-bar"><div style="width:${(c.score * 100).toFixed(0)}%"></div></div>
        <div class="rc-info"><b>${c.dim} → ${c.target}</b><span>${c.evidence}</span></div>
        <div class="rc-score">${(c.score * 100).toFixed(0)}%</div>
      </div>`).join('');

    WaferCharts.renderAll(d);
    setTimeout(() => Object.keys(WaferCharts).length && ['waferMap', 'yieldTrend', 'watTrend', 'defectPareto'].forEach(id => { const c = WaferCharts.getChart(id); c && c.resize(); }), 60);
  }

  // ---------- 提供给 AgentTools 的 app API ----------
  function setScenario(args) {
    const map = { waferId: 'cfgWaferId', fab: 'cfgFab', node: 'cfgNode', product: 'cfgProduct', signature: 'cfgSignature', timeRange: 'cfgTimeRange' };
    const applied = {};
    Object.entries(args).forEach(([k, v]) => {
      const id = map[k];
      if (id && v != null && $(id)) {
        // 对 select 确保选项存在
        if ($(id).tagName === 'SELECT' && ![...$(id).options].some(o => o.value === v)) return;
        $(id).value = v; applied[k] = v;
        HabitProfile.track('config_change', { field: k, value: v });
      }
    });
    updateReadiness();
    return { applied };
  }

  function setAnalysisDims(dims) {
    document.querySelectorAll('input[name="analysisDim"]').forEach(c => {
      c.checked = dims.includes(c.value);
      if (c.checked) HabitProfile.track('analysis_dim', { dim: c.value });
    });
    updateReadiness();
    return { dims };
  }

  function focusPanel(panel) {
    const idMap = {
      waferMap: 'panel-waferMap', yieldTrend: 'panel-yieldTrend', watTrend: 'panel-watTrend',
      defectPareto: 'panel-defectPareto', processFlow: 'panel-processFlow', rootCause: 'panel-rootCause',
    };
    const el = $(idMap[panel] || '');
    if (!el) return { ok: false };
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.add('panel-flash');
    setTimeout(() => el.classList.remove('panel-flash'), 1600);
    HabitProfile.track('focus_panel', { panel });
    return { focused: panel };
  }

  function applyHabits() {
    const s = HabitProfile.suggestedScenario();
    const dims = (HabitProfile.summary().preferredAnalysisDims || []);
    const applied = setScenario({ fab: s.fab, node: s.node, product: s.product, signature: s.signature });
    if (!$('cfgWaferId').value) setScenario({ waferId: 'W-2026-0512-07' });
    if (dims.length) setAnalysisDims(dims);
    return { applied, dims };
  }

  function flash(id) { const el = $(id); if (!el) return; el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 600); }

  global.WaferApp = {
    initForm,
    setScenario, setAnalysisDims, runLifecycle, focusPanel, applyHabits,
    getState: () => state,
  };
})(window);
