/*
 * contextCollector.js — AI“伴读”的眼睛
 * 把当前 HTML 页面的场景配置 + 计算结果整理成结构化上下文，
 * 供 AI 助手分析页面内容、判断填表完整性、生成分析与建议。
 */
(function (global) {
  'use strict';

  // 从 DOM 读取当前场景配置
  function readScenario() {
    const get = id => { const el = document.getElementById(id); return el ? el.value : ''; };
    const checked = name => Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(e => e.value);
    return {
      waferId: get('cfgWaferId').trim(),
      fab: get('cfgFab'),
      node: get('cfgNode'),
      product: get('cfgProduct'),
      timeRange: get('cfgTimeRange'),
      signature: get('cfgSignature'),
      analysisDims: checked('analysisDim'),
      presentations: checked('presentation'),
    };
  }

  // 校验填表完整性 -> 用于“指引用户正确提交”
  function validateScenario(s) {
    const issues = [];
    if (!s.waferId) issues.push({ field: 'waferId', level: 'error', msg: '未填写 Wafer ID / Lot，无法定位晶圆一生轨迹' });
    else if (!/^[A-Za-z]{0,2}-?\d{2,}/.test(s.waferId)) issues.push({ field: 'waferId', level: 'warn', msg: 'Wafer ID 格式可能不规范，建议形如 W-2026-0512-07' });
    if (!s.fab) issues.push({ field: 'fab', level: 'warn', msg: '未选择 Fab，跨厂数据可能混淆' });
    if (!s.analysisDims || s.analysisDims.length === 0) issues.push({ field: 'analysisDim', level: 'error', msg: '未勾选任何分析维度，结果将为空' });
    if (!s.presentations || s.presentations.length === 0) issues.push({ field: 'presentation', level: 'warn', msg: '未选择呈现内容，页面将无可视化输出' });
    const ready = issues.filter(i => i.level === 'error').length === 0 && !!s.waferId;
    const completeness = Math.round(
      (['waferId', 'fab', 'node', 'product'].filter(k => s[k]).length / 4) * 50 +
      (Math.min(s.analysisDims.length, 3) / 3) * 30 +
      (Math.min(s.presentations.length, 4) / 4) * 20
    );
    return { ready, issues, completeness };
  }

  // 汇总当前分析结果（若已运行“一键一生”）
  function summarizeResult(data) {
    if (!data) return null;
    const cand = WaferData.computeCommonality(data);
    return {
      waferId: data.meta.waferId, fab: data.meta.fab, node: data.meta.node, product: data.meta.product,
      finalYield: data.summary.finalYield,
      dieTotal: data.summary.dieTotal,
      signature: data.summary.signatureName,
      signatureHint: data.summary.signatureHint,
      hasExcursion: data.summary.hasExcursion,
      paramDrift: data.summary.drift,
      suspectStage: data.summary.rootCauseStageName,
      suspectTool: data.summary.suspectTool,
      topRootCause: cand[0],
      rootCauseCandidates: cand,
      defectTop3: data.defectPareto.slice(0, 3),
      yieldExcursionLots: data.yieldTrend.filter(d => d.yield < 70).map(d => d.lot),
    };
  }

  // 完整上下文快照
  function collect(state) {
    const scenario = readScenario();
    const validation = validateScenario(scenario);
    return {
      scenario,
      validation,
      hasResult: !!(state && state.data),
      result: state && state.data ? summarizeResult(state.data) : null,
      activeView: state ? state.activeView : null,
      habit: global.HabitProfile ? HabitProfile.summary() : null,
      ts: new Date().toISOString(),
    };
  }

  global.ContextCollector = { collect, readScenario, validateScenario, summarizeResult };
})(window);
