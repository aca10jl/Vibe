/*
 * server.js — “一键一生” AI 伴读助手后端
 *   1) 托管前端静态站点 (../web)
 *   2) POST /api/chat：按 provider 路由
 *        provider=claude → Anthropic Claude (claude-opus-4-8)
 *        provider=local  → 本地部署大模型（OpenAI 兼容：Ollama / LM Studio / vLLM / llama.cpp）
 *      统一返回 {text, toolCalls, followups}
 *
 * 不配置任何 Key/端点时，前端会自动使用本地规则推理，Demo 仍可跑。
 */
import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Anthropic from '@anthropic-ai/sdk';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 8787;
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-opus-4-8';

// 本地大模型默认端点（可被请求体 localConfig 覆盖）
const LOCAL_BASE = (process.env.LOCAL_LLM_BASE_URL || '').replace(/\/$/, '');
const LOCAL_MODEL = process.env.LOCAL_LLM_MODEL || 'qwen2.5:7b-instruct';
const LOCAL_KEY = process.env.LOCAL_LLM_API_KEY || '';

const app = express();
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, '..', 'web')));

const hasKey = !!process.env.ANTHROPIC_API_KEY;
const anthropic = hasKey ? new Anthropic() : null;

const FOLLOWUPS = {
  companion: ['帮我分析根因', '这个良率正常吗？', '带我看晶圆图'],
  analyze: ['给我处置建议', '为什么怀疑这台设备？', '看缺陷 Pareto'],
  advise: ['按建议修正并提交', '用我的习惯填表', '导出报告'],
  chat: ['伴读这个页面', '分析根因', '我该怎么填表'],
};

// ---------- 共享：系统提示 ----------
function buildSystem(context, intent, { actionStyle } = {}) {
  const habit = context && context.habit ? `\n## 用户习惯画像\n${JSON.stringify(context.habit)}` : '';
  const intentHint = {
    companion: '当前模式=伴读：用通俗语言解读页面有什么、各面板含义、当前状态。',
    analyze: '当前模式=分析：基于结果数据做根因分析，给出按关联度排序的根因候选与结论。',
    advise: '当前模式=建议：指引用户正确提交一键一生（补全/修正表单），或给出处置与下一步建议。',
    chat: '当前模式=自由问答：按用户问题判断应伴读、分析还是建议。',
  }[intent] || '';
  const actionGuide = actionStyle
    ? `\n## 操作页面（重要）\n若需操作页面，请额外输出一个或多个动作代码块：\n\`\`\`action\n{"tool":"工具名","input":{...}}\n\`\`\`\n可用工具：set_scenario, set_analysis_dims, run_lifecycle, focus_panel(panel∈waferMap|yieldTrend|watTrend|defectPareto|processFlow|rootCause), apply_my_habits。意图明确时优先用动作完成，而非仅口头描述。`
    : `\n## 操作页面（重要）\n你可调用页面工具真正操作界面（填表/设维度/提交/定位面板/套用习惯）。意图明确时优先用工具完成动作。`;

  return `你是“一键一生”半导体晶圆良率根因分析平台右侧的 AI 伴读助手。
职责：① 伴读——阅读并解释当前 HTML 页面；② 分析——对晶圆全生命周期数据做良率根因分析；③ 建议——指引用户正确提交“一键一生”任务并给出处置建议。

## 领域知识
- 晶圆一生：前道(光刻/刻蚀/注入/沉积/CMP) → 中测(WAT/CP) → 后道(封装/FT)。
- 根因维度：设备/腔体关联(commonality)、工艺步骤、参数漂移(WAT SPC)、缺陷空间特征、批次谱系。
- 缺陷特征↔根因：edge_ring↔边缘刻蚀/清洗/膜厚；center↔CMP/旋涂/温场中心；scratch↔机械/CMP；cluster↔腔体颗粒污染。
${actionGuide}
- 中文、简洁、结构化；结论给出关联度/置信度；不要编造上下文外的数值。

${intentHint}

## 当前页面上下文（实时快照）
${JSON.stringify(context || {})}${habit}`;
}

function userTurn(intent, userMessage) {
  return userMessage ||
    ({ companion: '请伴读当前页面。', analyze: '请基于当前数据分析根因。', advise: '请指引我正确提交一键一生或给出建议。' }[intent]) ||
    '请帮助我。';
}

// 从文本中解析 ```action {json}``` 动作块
function parseActionBlocks(text) {
  const calls = []; let clean = text || '';
  const re = /```(?:action|json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    try {
      const obj = JSON.parse(m[1]);
      const arr = Array.isArray(obj) ? obj : [obj];
      arr.forEach(o => { if (o && o.tool) calls.push({ name: o.tool, input: o.input || {} }); });
      if (arr.some(o => o && o.tool)) clean = clean.replace(m[0], '');
    } catch (e) {}
  }
  return { clean: clean.trim(), calls };
}

// ---------- provider: Claude ----------
async function callClaude({ intent, userMessage, context, history, tools }) {
  const messages = [
    ...(history || []).map(h => ({ role: h.role === 'assistant' ? 'assistant' : 'user', content: String(h.content) })),
    { role: 'user', content: userTurn(intent, userMessage) },
  ];
  const resp = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1500,
    thinking: { type: 'adaptive' },
    output_config: { effort: 'medium' }, // 交互式侧边栏，平衡质量与延迟
    system: buildSystem(context, intent, { actionStyle: false }),
    tools: tools && tools.length ? tools : undefined,
    messages,
  });
  let text = '';
  const toolCalls = [];
  for (const block of resp.content) {
    if (block.type === 'text') text += block.text;
    else if (block.type === 'tool_use') toolCalls.push({ name: block.name, input: block.input });
  }
  return { text: text.trim(), toolCalls };
}

// ---------- provider: 本地大模型（OpenAI 兼容） ----------
function openaiTools(schemas) {
  return (schemas || []).map(s => ({ type: 'function', function: { name: s.name, description: s.description, parameters: s.input_schema } }));
}
async function postChat(base, key, body) {
  const resp = await fetch(base + '/chat/completions', {
    method: 'POST',
    headers: Object.assign({ 'Content-Type': 'application/json' }, key ? { Authorization: 'Bearer ' + key } : {}),
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error('local ' + resp.status + ' ' + (await resp.text()).slice(0, 120));
  return resp.json();
}
async function callLocal({ intent, userMessage, context, history, tools, localConfig }) {
  const cfg = localConfig || {};
  const base = (cfg.baseUrl || LOCAL_BASE || '').replace(/\/$/, '');
  if (!base) throw new Error('no_local_endpoint');
  const model = cfg.model || LOCAL_MODEL;
  const key = cfg.apiKey || LOCAL_KEY;

  const messages = [
    { role: 'system', content: buildSystem(context, intent, { actionStyle: true }) },
    ...(history || []).map(h => ({ role: h.role === 'assistant' ? 'assistant' : 'user', content: String(h.content) })),
    { role: 'user', content: userTurn(intent, userMessage) },
  ];
  const body = { model, messages, temperature: 0.3, max_tokens: 1200, stream: false };

  let data;
  try { data = await postChat(base, key, Object.assign({}, body, { tools: openaiTools(tools) })); }
  catch (e) { data = await postChat(base, key, body); } // 模型不支持 tools 时回退

  const msg = (data.choices && data.choices[0] && data.choices[0].message) || {};
  let text = msg.content || '';
  const toolCalls = (msg.tool_calls || []).map(tc => {
    try { return { name: tc.function.name, input: JSON.parse(tc.function.arguments || '{}') }; }
    catch (e) { return { name: tc.function && tc.function.name, input: {} }; }
  });
  const parsed = parseActionBlocks(text);
  text = parsed.clean; toolCalls.push(...parsed.calls);
  return { text: text.trim() || '(本地模型返回空响应)', toolCalls };
}

// ---------- 路由 ----------
app.post('/api/chat', async (req, res) => {
  const { provider = 'claude', intent = 'chat' } = req.body || {};
  try {
    let out;
    if (provider === 'local') {
      out = await callLocal(req.body);
    } else {
      if (!hasKey) return res.status(503).json({ error: '后端未配置 ANTHROPIC_API_KEY', text: '请使用本地推理或本地大模型模式。' });
      out = await callClaude(req.body);
    }
    res.json({ text: out.text, toolCalls: out.toolCalls, followups: FOLLOWUPS[intent] || FOLLOWUPS.chat });
  } catch (e) {
    console.error('[chat:%s] %s', provider, e.message);
    const msg = e.message === 'no_local_endpoint' ? '未配置本地大模型端点（请在右侧⚙设置 Base URL）' : e.message;
    res.status(500).json({ error: msg, text: '调用失败：' + msg });
  }
});

app.get('/api/health', (_req, res) => res.json({
  ok: true,
  providers: { claude: hasKey ? MODEL : false, local: (LOCAL_BASE ? LOCAL_BASE + ' (' + LOCAL_MODEL + ')' : 'configurable-in-UI') },
}));

app.listen(PORT, () => {
  console.log(`\n  ◧ 一键一生 + AI 助手  →  http://localhost:${PORT}`);
  console.log(`  Claude: ${hasKey ? '已启用 (' + MODEL + ')' : '未配置 Key'}`);
  console.log(`  本地大模型: ${LOCAL_BASE ? LOCAL_BASE + ' (' + LOCAL_MODEL + ')' : '可在前端⚙设置，或设 LOCAL_LLM_BASE_URL'}\n`);
});
