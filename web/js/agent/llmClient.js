/*
 * llmClient.js — 双模 AI 客户端
 *   mock  : 纯前端规则推理引擎，零依赖、零密钥，离线即可 Demo
 *   claude: 调用后端 /api/chat 代理到 Claude API（claude-opus-4-8，含工具调用）
 *
 * 统一返回：{ text, toolCalls:[{name,input}], followups:[...] }
 */
(function (global) {
  'use strict';

  const SIG_NAME = {
    edge_ring: '边缘环状', center: '中心聚集', scratch: '划伤', cluster: '局部簇', random: '随机分布',
  };

  // ============ 本地规则推理引擎（mock 模式） ============
  function companion(ctx) {
    const s = ctx.scenario, v = ctx.validation;
    const lines = [];
    lines.push('我在帮你**伴读**当前“一键一生”页面。');
    if (!ctx.hasResult) {
      lines.push(`你正在配置场景：Wafer=**${s.waferId || '（未填）'}**，Fab=${s.fab || '未选'}，节点=${s.node || '未选'}，产品=${s.product || '未选'}。`);
      lines.push(`分析维度已勾选 ${s.analysisDims.length} 项，呈现内容 ${s.presentations.length} 项，表单完整度 **${v.completeness}%**。`);
      lines.push(v.ready ? '✅ 必填项已就绪，可以提交一键一生。' : '⚠️ 还有必填项缺失，见下方“建议”。');
    } else {
      const r = ctx.result;
      lines.push(`已生成 **${r.waferId}** 的晶圆一生：终测良率 **${r.finalYield}%**，缺陷特征呈 **${r.signature}**。`);
      lines.push(`页面右侧从上到下是：晶圆 Bin 图（空间分布）、良率趋势、WAT 参数趋势、缺陷 Pareto、工艺流程时间轴。`);
      lines.push(`最高嫌疑指向 **${r.suspectStage} / ${r.suspectTool}**。我可以带你逐个面板看，或直接给根因分析。`);
    }
    return { text: lines.join('\n\n'), toolCalls: [], followups: ['这个良率正常吗？', '帮我分析根因', '带我看晶圆图'] };
  }

  function analyze(ctx) {
    if (!ctx.hasResult) {
      return {
        text: '当前还没有运行“一键一生”，我先帮你把场景补全并提交，再做分析。',
        toolCalls: [{ name: 'run_lifecycle', input: {} }],
        followups: ['提交后再分析'],
      };
    }
    const r = ctx.result;
    const lines = [];
    lines.push(`### 根因分析 · ${r.waferId}`);
    lines.push(`**良率**：终测 ${r.finalYield}%（${r.finalYield < 75 ? '低于预警线，需介入' : '处于可接受区间'}）。`);
    lines.push(`**缺陷空间特征**：${r.signature} —— ${r.signatureHint}。`);
    lines.push('**根因候选（按关联度排序）**：');
    r.rootCauseCandidates.forEach((c, i) => {
      lines.push(`${i + 1}. \`${(c.score * 100).toFixed(0)}%\` **${c.dim} → ${c.target}**：${c.evidence}`);
    });
    if (r.paramDrift) lines.push('> WAT 参数存在单调漂移，提示工艺窗口偏移，建议核对该时间段 recipe/PM 记录。');
    if (r.hasExcursion) lines.push(`> 良率在批次 ${r.yieldExcursionLots.join(', ') || '局部'} 出现 excursion，建议做时间相关性核查。`);
    lines.push(`\n**结论**：最可能根因为 **${r.topRootCause.dim} → ${r.topRootCause.target}**（关联度 ${(r.topRootCause.score * 100).toFixed(0)}%）。`);
    return {
      text: lines.join('\n\n'),
      toolCalls: [{ name: 'focus_panel', input: { panel: 'rootCause' } }],
      followups: ['给我处置建议', '看缺陷 Pareto', '为什么怀疑这台设备？'],
    };
  }

  function advise(ctx) {
    const s = ctx.scenario, v = ctx.validation;
    const lines = [];
    if (!v.ready) {
      lines.push('### 提交前建议（指引正确提交一键一生）');
      v.issues.forEach(it => lines.push(`- ${it.level === 'error' ? '🔴' : '🟡'} **${it.field}**：${it.msg}`));
      const calls = [];
      const fix = {};
      if (!s.waferId) fix.waferId = 'W-2026-0512-07';
      if (!s.fab && ctx.habit && ctx.habit.favoriteFab) fix.fab = ctx.habit.favoriteFab;
      if (Object.keys(fix).length) calls.push({ name: 'set_scenario', input: fix });
      if (!s.analysisDims.length) calls.push({ name: 'set_analysis_dims', input: { dims: ['equipment', 'process', 'defect'] } });
      lines.push('\n我可以帮你**一键修正**这些必填项。');
      return { text: lines.join('\n'), toolCalls: calls, followups: ['修正并提交', '用我的习惯填'] };
    }
    if (!ctx.hasResult) {
      return {
        text: '场景已就绪，建议直接提交一键一生，先拿到全链路画像再决定下一步。',
        toolCalls: [{ name: 'run_lifecycle', input: {} }], followups: ['提交'],
      };
    }
    const r = ctx.result;
    const lines2 = ['### 处置与下一步建议'];
    lines2.push(`1. **隔离/复测**：对经过 ${r.suspectTool} 的晶圆做 hold & 复测，确认 ${r.signature} 是否可复现。`);
    lines2.push(`2. **设备核查**：调取 ${r.suspectStage} 该腔体的 SPC、PM 与颗粒监控，比对良率掉坑时间段。`);
    lines2.push(`3. **扩样验证**：用 commonality 把同一时间窗、同设备路径的兄弟批次拉出做对照。`);
    if (r.paramDrift) lines2.push('4. **参数纠偏**：针对 Vth 漂移，评估 recipe 微调或工艺窗口重新对中。');
    lines2.push(`\n建议优先级：先做 (1)(2)，可在 24h 内定位。要我把同设备兄弟批次也加进场景吗？`);
    return { text: lines2.join('\n'), toolCalls: [], followups: ['加入兄弟批次', '导出报告', '看工艺流程'] };
  }

  function chat(ctx, msg) {
    const m = (msg || '').toLowerCase();
    if (/良率|yield|多少/.test(msg)) {
      if (ctx.hasResult) return analyze(ctx);
      return { text: '还没有运行一键一生，先提交才能给你良率与根因。要我现在提交吗？', toolCalls: [], followups: ['提交一键一生'] };
    }
    if (/根因|root|为什么|原因/.test(msg)) return analyze(ctx);
    if (/建议|怎么办|处置|下一步|next/.test(msg)) return advise(ctx);
    if (/晶圆图|bin|map|空间/.test(msg)) return { text: '已为你定位到晶圆 Bin 图。红/橙色块为失效 die，可看出空间分布是否成环/居中/划伤。', toolCalls: [{ name: 'focus_panel', input: { panel: 'waferMap' } }], followups: ['这是什么缺陷？'] };
    if (/工艺|流程|process|设备|tool/.test(msg)) return { text: '已定位工艺流程时间轴，标⚠️的步骤为疑似异常设备。', toolCalls: [{ name: 'focus_panel', input: { panel: 'processFlow' } }], followups: ['分析这台设备'] };
    if (/习惯|默认|帮我填|常用/.test(msg)) return { text: '我用你最常用的配置来填表。', toolCalls: [{ name: 'apply_my_habits', input: {} }], followups: ['提交'] };
    if (/提交|运行|开始|run|一键/.test(msg)) return { text: '好的，正在校验并提交一键一生。', toolCalls: [{ name: 'run_lifecycle', input: {} }], followups: [] };
    // 默认：伴读式回应
    return {
      text: '我可以：① 伴读当前页面 ② 分析晶圆良率根因 ③ 指引你正确提交一键一生。直接说需求，或点下面的快捷问题。',
      toolCalls: [], followups: ['伴读这个页面', '分析根因', '我该怎么填表'],
    };
  }

  function mockRespond(req) {
    const { intent, context, userMessage } = req;
    if (intent === 'companion') return Promise.resolve(companion(context));
    if (intent === 'analyze') return Promise.resolve(analyze(context));
    if (intent === 'advise') return Promise.resolve(advise(context));
    return Promise.resolve(chat(context, userMessage));
  }

  // ============ 经后端代理（Claude 或 本地大模型） ============
  async function backendRespond(req, provider) {
    const resp = await fetch((global.AI_BACKEND || '') + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider,
        intent: req.intent, userMessage: req.userMessage,
        context: req.context, history: req.history,
        tools: req.toolSchemas, localConfig: req.localConfig,
      }),
    });
    if (!resp.ok) {
      let detail = resp.status;
      try { const j = await resp.json(); detail = j.error || j.text || detail; } catch (e) {}
      throw new Error('后端 ' + detail);
    }
    const data = await resp.json();
    return { text: data.text || '', toolCalls: data.toolCalls || [], followups: data.followups || [] };
  }

  // ============ 浏览器直连本地大模型（无后端时的兜底，OpenAI 兼容） ============
  function userTurn(req) {
    return req.userMessage ||
      ({ companion: '请伴读当前页面。', analyze: '请基于当前数据分析根因。', advise: '请指引我正确提交一键一生或给出建议。' }[req.intent]) ||
      '请帮助我。';
  }
  function localSystem(context, intent) {
    return `你是“一键一生”晶圆良率根因分析平台右侧的 AI 伴读助手，能①伴读页面②分析良率根因③指引正确提交任务。
缺陷空间特征↔根因：edge_ring↔边缘刻蚀/清洗；center↔CMP/旋涂；scratch↔机械/CMP；cluster↔腔体颗粒。
当前意图=${intent}。请用中文、简洁、结构化回答，基于下方上下文，不要编造数值。
若需操作页面，请额外输出一个或多个动作代码块：\n\`\`\`action\n{"tool":"工具名","input":{...}}\n\`\`\`\n可用工具：set_scenario, set_analysis_dims, run_lifecycle, focus_panel(panel∈waferMap|yieldTrend|watTrend|defectPareto|processFlow|rootCause), apply_my_habits。
## 页面上下文\n${JSON.stringify(context)}`;
  }
  function openaiTools(schemas) {
    return (schemas || []).map(s => ({ type: 'function', function: { name: s.name, description: s.description, parameters: s.input_schema } }));
  }
  function parseActionBlocks(text) {
    const calls = []; let clean = text || '';
    const re = /```(?:action|json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      try {
        let obj = JSON.parse(m[1]);
        const arr = Array.isArray(obj) ? obj : [obj];
        arr.forEach(o => { if (o && o.tool) calls.push({ name: o.tool, input: o.input || {} }); });
        if (arr.some(o => o && o.tool)) clean = clean.replace(m[0], '');
      } catch (e) {}
    }
    return { clean: clean.trim(), calls };
  }
  async function postChat(base, key, body) {
    const resp = await fetch(base + '/chat/completions', {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json' }, key ? { Authorization: 'Bearer ' + key } : {}),
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error('本地模型 ' + resp.status);
    return resp.json();
  }
  async function directLocalRespond(req) {
    const cfg = req.localConfig || {};
    const base = (cfg.baseUrl || '').replace(/\/$/, '');
    if (!base) throw new Error('未配置本地大模型 Base URL');
    const messages = [
      { role: 'system', content: localSystem(req.context, req.intent) },
      ...(req.history || []).map(h => ({ role: h.role === 'assistant' ? 'assistant' : 'user', content: String(h.content) })),
      { role: 'user', content: userTurn(req) },
    ];
    const base0 = { model: cfg.model || 'local-model', messages, temperature: 0.3, max_tokens: 1200, stream: false };
    let data;
    try { data = await postChat(base, cfg.apiKey, Object.assign({}, base0, { tools: openaiTools(req.toolSchemas) })); }
    catch (e) { data = await postChat(base, cfg.apiKey, base0); } // 模型不支持 tools 时回退
    const msg = (data.choices && data.choices[0] && data.choices[0].message) || {};
    let text = msg.content || '';
    const calls = (msg.tool_calls || []).map(tc => { try { return { name: tc.function.name, input: JSON.parse(tc.function.arguments || '{}') }; } catch (e) { return { name: tc.function && tc.function.name, input: {} }; } });
    const parsed = parseActionBlocks(text); text = parsed.clean; calls.push(...parsed.calls);
    return { text: text.trim() || '(本地模型返回空响应)', toolCalls: calls, followups: [] };
  }

  async function respond(req) {
    const mode = req.mode || 'mock';
    if (mode === 'mock') return mockRespond(req);

    if (mode === 'claude') {
      try { return await backendRespond(req, 'claude'); }
      catch (e) {
        const fb = await mockRespond(req);
        fb.text = `> ⚠️ 未能连接 Claude 后端（${e.message}），已回退本地推理。\n\n` + fb.text;
        return fb;
      }
    }

    if (mode === 'local') {
      // 优先经后端代理；失败再浏览器直连；再失败回退本地推理
      try { return await backendRespond(req, 'local'); }
      catch (e1) {
        try { return await directLocalRespond(req); }
        catch (e2) {
          const fb = await mockRespond(req);
          fb.text = `> ⚠️ 本地大模型不可用（后端：${e1.message}；直连：${e2.message}），已回退本地推理。\n\n` + fb.text;
          return fb;
        }
      }
    }
    return mockRespond(req);
  }

  global.LLMClient = { respond, _mock: { companion, analyze, advise, chat } };
})(window);
