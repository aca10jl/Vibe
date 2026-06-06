/*
 * habitProfile.js — 智能体的“持续学习”层
 * 记录用户在页面上的操作行为，沉淀偏好画像（localStorage 持久化），
 * 供 AI 助手生成个性化默认值、快捷操作与建议。
 * 生产环境可替换为服务端用户画像 / 强化学习信号。
 */
(function (global) {
  'use strict';
  const KEY = 'wafer_ai_habit_v1';

  const empty = () => ({
    events: [],                 // 行为流水
    counters: {                 // 维度计数
      fab: {}, node: {}, product: {}, signature: {},
      analysisDim: {}, panelFocus: {}, intent: {},
    },
    submits: 0,
    firstSeen: Date.now(),
    lastSeen: Date.now(),
  });

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return empty();
      const p = JSON.parse(raw);
      return Object.assign(empty(), p);
    } catch (e) { return empty(); }
  }

  let profile = load();

  function save() {
    profile.lastSeen = Date.now();
    try { localStorage.setItem(KEY, JSON.stringify(profile)); } catch (e) {}
  }

  function bump(bucket, value) {
    if (value == null || value === '') return;
    profile.counters[bucket] = profile.counters[bucket] || {};
    profile.counters[bucket][value] = (profile.counters[bucket][value] || 0) + 1;
  }

  // 记录一次行为
  function track(type, payload) {
    payload = payload || {};
    profile.events.push({ t: Date.now(), type, ...payload });
    if (profile.events.length > 400) profile.events.splice(0, profile.events.length - 400);

    if (type === 'config_change' && payload.field) bump(payload.field, payload.value);
    if (type === 'submit_task') { profile.submits++; bump('signature', payload.signature); }
    if (type === 'focus_panel') bump('panelFocus', payload.panel);
    if (type === 'analysis_dim') bump('analysisDim', payload.dim);
    if (type === 'intent') bump('intent', payload.intent);
    save();
  }

  function topOf(bucket) {
    const c = profile.counters[bucket] || {};
    const entries = Object.entries(c).sort((a, b) => b[1] - a[1]);
    return entries.length ? entries[0][0] : null;
  }

  function rankOf(bucket) {
    const c = profile.counters[bucket] || {};
    return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ value: k, n: v }));
  }

  // 个性化默认场景（用于一键填表）
  function suggestedScenario() {
    return {
      fab: topOf('fab'),
      node: topOf('node'),
      product: topOf('product'),
      signature: topOf('signature'),
    };
  }

  // 给 AI 的画像摘要（注入到 prompt / 上下文）
  function summary() {
    const total = profile.events.length;
    return {
      experienceLevel: profile.submits >= 5 ? '资深' : profile.submits >= 1 ? '熟练' : '新手',
      submits: profile.submits,
      totalEvents: total,
      favoriteFab: topOf('fab'),
      favoriteNode: topOf('node'),
      favoriteProduct: topOf('product'),
      mostViewedSignature: topOf('signature'),
      preferredAnalysisDims: rankOf('analysisDim').slice(0, 3).map(d => d.value),
      mostFocusedPanel: topOf('panelFocus'),
      topIntents: rankOf('intent').slice(0, 3).map(d => d.value),
    };
  }

  function reset() { profile = empty(); save(); }

  global.HabitProfile = { track, summary, suggestedScenario, topOf, rankOf, reset, raw: () => profile };
})(window);
