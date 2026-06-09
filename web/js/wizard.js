/*
 * wizard.js — 左侧“逐步配置”向导 + 配置/结果两阶段布局切换
 *   阶段一（配置）：① 场景 → ② 维度 → ③ 呈现 → ④ 提交，逐步设置
 *   阶段二（结果）：向导折叠为紧凑配置摘要，主区域专注呈现结果
 * 说明：所有表单输入始终在 DOM 中（隐藏步骤仅 display:none），
 *      以保证 ContextCollector / AI 工具调用随时可读写任意字段。
 */
(function (global) {
  'use strict';
  const $ = id => document.getElementById(id);
  const TOTAL = 4;
  let cur = 1;

  function stepValid(n) {
    const s = ContextCollector.readScenario();
    if (n === 1) return !!s.waferId;
    if (n === 2) return s.analysisDims.length > 0;
    if (n === 3) return s.presentations.length > 0;
    if (n === 4) return ContextCollector.validateScenario(s).ready;
    return true;
  }

  function show(n) {
    cur = Math.max(1, Math.min(TOTAL, n));
    document.querySelectorAll('.wizard-step').forEach(el => { el.hidden = +el.dataset.step !== cur; });
    document.querySelectorAll('.stepper .step').forEach(btn => {
      const i = +btn.dataset.go;
      btn.classList.toggle('active', i === cur);
      btn.classList.toggle('done', i < cur && stepValid(i));
    });
    $('btnPrev').style.visibility = cur === 1 ? 'hidden' : 'visible';
    $('btnNext').style.display = cur < TOTAL ? '' : 'none';
    $('btnRun').style.display = cur === TOTAL ? '' : 'none';
    if (cur === TOTAL) renderSummary($('cfgSummary'));
    flashHint('');
  }

  function next() {
    if (!stepValid(cur)) { flashHint(hintFor(cur)); pulse(); return; }
    show(cur + 1);
  }
  function prev() { show(cur - 1); }

  function hintFor(n) {
    return { 1: '请填写 Wafer ID / Lot', 2: '至少勾选 1 个分析维度', 3: '至少选择 1 项呈现内容', 4: '请补全必填项' }[n] || '';
  }
  function flashHint(msg) {
    let el = $('wizHint');
    if (!el) { el = document.createElement('div'); el.id = 'wizHint'; el.className = 'wiz-hint'; $('btnNext').parentNode.insertBefore(el, $('btnNext')); }
    el.textContent = msg || '';
    el.style.display = msg ? 'block' : 'none';
  }
  function pulse() { const b = document.querySelector('.wizard-step:not([hidden])'); if (b) { b.classList.add('shake'); setTimeout(() => b.classList.remove('shake'), 500); } }

  // 配置摘要（步骤4 与 结果阶段共用）
  function scenarioChips() {
    const s = ContextCollector.readScenario();
    const sig = { '': '自动识别', edge_ring: '边缘环状', center: '中心聚集', scratch: '划伤', cluster: '局部簇', random: '随机' }[s.signature] || s.signature;
    return [
      ['Wafer', s.waferId || '—'], ['Fab', s.fab || '全部'], ['节点', s.node || '全部'],
      ['产品', s.product || '全部'], ['缺陷特征', sig],
      ['分析维度', s.analysisDims.length + ' 项'], ['呈现', s.presentations.length + ' 项'],
    ];
  }
  function renderSummary(el) {
    if (!el) return;
    el.innerHTML = scenarioChips().map(([k, v]) => `<span class="sum-chip"><i>${k}</i>${v}</span>`).join('');
  }

  // 阶段切换
  function enterResultMode() {
    $('wizard').style.display = 'none';
    $('configRail').style.display = 'block';
    renderSummary($('railChips'));
    setPhase('result');
  }
  function enterConfigMode() {
    $('configRail').style.display = 'none';
    $('wizard').style.display = '';
    show(TOTAL); // 直接回到“提交”步，便于微调后重跑
    setPhase('setup');
  }
  function setPhase(p) {
    $('phaseSetup').classList.toggle('on', p === 'setup');
    $('phaseResult').classList.toggle('on', p === 'result');
    document.body.classList.toggle('phase-result', p === 'result');
  }

  function refresh() {
    // 输入变化时刷新 stepper done 态与摘要
    document.querySelectorAll('.stepper .step').forEach(btn => {
      const i = +btn.dataset.go;
      btn.classList.toggle('done', i < cur && stepValid(i));
    });
    if (cur === TOTAL) renderSummary($('cfgSummary'));
    if ($('configRail').style.display !== 'none') renderSummary($('railChips'));
  }

  function init() {
    $('btnNext').onclick = next;
    $('btnPrev').onclick = prev;
    document.querySelectorAll('.stepper .step').forEach(btn => {
      btn.onclick = () => { const t = +btn.dataset.go; if (t <= cur || stepValid(cur)) show(t); else { flashHint(hintFor(cur)); pulse(); } };
    });
    $('btnReconfig').onclick = enterConfigMode;
    $('btnRerun').onclick = () => WaferApp.runLifecycle();
    // 监听配置区变化以刷新向导状态
    document.querySelector('.sidebar-left').addEventListener('input', refresh);
    document.querySelector('.sidebar-left').addEventListener('change', refresh);
    show(1);
  }

  global.Wizard = { init, show, enterResultMode, enterConfigMode, refresh, goTo: show, current: () => cur };
})(window);
