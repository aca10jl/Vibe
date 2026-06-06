/*
 * assistant.js — 右侧 AI 助手（伴读 / 分析 / 建议 / 对话）的 UI 控制器
 * 负责：渲染消息、调度 LLMClient、执行 AI 返回的工具调用、回灌习惯画像。
 */
(function (global) {
  'use strict';

  const state = {
    mode: 'mock',        // mock | claude
    history: [],         // [{role, content}]
    busy: false,
    getAppState: null,   // () => app state，用于 contextCollector
  };

  const $ = id => document.getElementById(id);

  function setMode(mode) {
    state.mode = mode;
    const badge = $('aiModeBadge');
    if (badge) {
      badge.textContent = mode === 'claude' ? 'Claude 在线' : '本地推理';
      badge.className = 'ai-mode-badge ' + (mode === 'claude' ? 'online' : 'local');
    }
  }

  // 简单 markdown -> html（标题/加粗/代码/引用/列表）
  function md(t) {
    return t
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^### (.*)$/gm, '<h4>$1</h4>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/^&gt; (.*)$/gm, '<blockquote>$1</blockquote>')
      .replace(/^\d+\. (.*)$/gm, '<li>$1</li>')
      .replace(/^- (.*)$/gm, '<li>$1</li>')
      .replace(/\n/g, '<br/>');
  }

  function bubble(role, html, opts) {
    opts = opts || {};
    const box = $('aiMessages');
    const el = document.createElement('div');
    el.className = 'ai-msg ai-' + role;
    el.innerHTML = role === 'assistant'
      ? `<div class="ai-avatar">🤖</div><div class="ai-bubble">${html}</div>`
      : `<div class="ai-bubble">${html}</div>`;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }

  function renderFollowups(items) {
    const bar = $('aiFollowups');
    bar.innerHTML = '';
    (items || []).forEach(q => {
      const b = document.createElement('button');
      b.className = 'chip';
      b.textContent = q;
      b.onclick = () => send(q);
      bar.appendChild(b);
    });
  }

  function toolBadge(call, res) {
    const ok = res && res.ok;
    const label = {
      set_scenario: '已填写场景', set_analysis_dims: '已设置分析维度',
      run_lifecycle: '已提交一键一生', focus_panel: '已定位面板', apply_my_habits: '已套用你的习惯',
    }[call.name] || call.name;
    return `<div class="ai-tool ${ok ? '' : 'fail'}">🔧 ${label}${ok ? '' : '（失败）'}</div>`;
  }

  async function runIntent(intent, userMessage) {
    if (state.busy) return;
    state.busy = true;
    const typing = bubble('assistant', '<span class="ai-typing"><i></i><i></i><i></i></span>');

    const ctx = ContextCollector.collect(state.getAppState ? state.getAppState() : null);
    if (global.HabitProfile && intent !== 'chat') HabitProfile.track('intent', { intent });

    let reply;
    try {
      reply = await LLMClient.respond({
        mode: state.mode, intent, userMessage,
        context: ctx, history: state.history.slice(-8),
        toolSchemas: AgentTools.list(),
      });
    } catch (e) {
      reply = { text: '抱歉，出现错误：' + e.message, toolCalls: [], followups: [] };
    }

    // 执行工具调用
    let toolHtml = '';
    (reply.toolCalls || []).forEach(call => {
      const res = AgentTools.execute(call.name, call.input);
      toolHtml += toolBadge(call, res);
    });

    typing.querySelector('.ai-bubble').innerHTML = md(reply.text) + (toolHtml ? '<div class="ai-tools">' + toolHtml + '</div>' : '');
    $('aiMessages').scrollTop = $('aiMessages').scrollHeight;

    state.history.push({ role: 'assistant', content: reply.text });
    renderFollowups(reply.followups);
    state.busy = false;
  }

  function send(text) {
    text = (text != null ? text : $('aiInput').value).trim();
    if (!text || state.busy) return;
    bubble('user', md(text));
    state.history.push({ role: 'user', content: text });
    $('aiInput').value = '';
    renderFollowups([]);
    runIntent('chat', text);
  }

  function init(getAppState) {
    state.getAppState = getAppState;

    // 快捷意图按钮
    $('aiTabCompanion').onclick = () => runIntent('companion');
    $('aiTabAnalyze').onclick = () => runIntent('analyze');
    $('aiTabAdvise').onclick = () => runIntent('advise');

    $('aiSend').onclick = () => send();
    $('aiInput').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

    // 模式切换
    $('aiModeToggle').onchange = e => setMode(e.target.checked ? 'claude' : 'mock');
    setMode('mock');

    // 习惯画像面板
    $('aiHabitBtn').onclick = showHabit;
    $('aiResetHabit').onclick = () => { HabitProfile.reset(); showHabit(); };

    // 欢迎语
    bubble('assistant', md('👋 我是 **Wafer AI 伴读助手**。\n\n我能阅读这个“一键一生”页面、分析晶圆良率根因、并指引你正确提交任务；还会持续学习你的使用习惯。\n\n试试上方 **伴读 / 分析 / 建议**，或直接提问。'));
    renderFollowups(['伴读这个页面', '我该怎么填表？', '帮我分析根因']);
  }

  function showHabit() {
    const h = HabitProfile.summary();
    const panel = $('aiHabitPanel');
    panel.classList.toggle('open');
    panel.querySelector('.habit-body').innerHTML = `
      <div class="habit-row"><span>经验等级</span><b>${h.experienceLevel}</b></div>
      <div class="habit-row"><span>累计提交</span><b>${h.submits} 次</b></div>
      <div class="habit-row"><span>行为事件</span><b>${h.totalEvents}</b></div>
      <div class="habit-row"><span>常用 Fab</span><b>${h.favoriteFab || '—'}</b></div>
      <div class="habit-row"><span>常用节点</span><b>${h.favoriteNode || '—'}</b></div>
      <div class="habit-row"><span>常看产品</span><b>${h.favoriteProduct || '—'}</b></div>
      <div class="habit-row"><span>偏好分析维度</span><b>${(h.preferredAnalysisDims || []).join(' / ') || '—'}</b></div>
      <div class="habit-row"><span>高频意图</span><b>${(h.topIntents || []).join(' / ') || '—'}</b></div>`;
  }

  // 供 app 在运行一键一生后主动让 AI 伴读
  function autoCompanionAfterRun() { runIntent('companion'); }

  global.Assistant = { init, send, setMode, autoCompanionAfterRun, refreshHabit: showHabit };
})(window);
