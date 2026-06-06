/*
 * server.js — “一键一生” AI 伴读助手后端
 *   1) 托管前端静态站点 (../web)
 *   2) POST /api/chat：把页面上下文 + 工具 schema 交给 Claude，返回 {text, toolCalls, followups}
 *
 * 仅在前端切换到 “Claude” 模式时被调用；不配置 API Key 时前端会自动用本地推理。
 * 需要环境变量 ANTHROPIC_API_KEY（见 .env.example）。
 */
import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Anthropic from '@anthropic-ai/sdk';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 8787;
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-opus-4-8';

const app = express();
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, '..', 'web')));

const hasKey = !!process.env.ANTHROPIC_API_KEY;
const client = hasKey ? new Anthropic() : null;

// 领域系统提示：定义助手角色（伴读/分析/建议）+ 半导体良率根因背景
function buildSystem(context, intent) {
  const habit = context.habit
    ? `\n## 用户习惯画像（持续学习所得，用于个性化）\n${JSON.stringify(context.habit)}`
    : '';
  const intentHint = {
    companion: '当前模式=伴读：用通俗语言解读页面上有什么、各面板含义、当前状态。',
    analyze: '当前模式=分析：基于结果数据做晶圆良率根因分析，给出按关联度排序的根因候选与结论。',
    advise: '当前模式=建议：指引用户正确提交一键一生（补全/修正表单），或给出处置与下一步建议。',
    chat: '当前模式=自由问答：按用户问题判断应伴读、分析还是建议。',
  }[intent] || '';

  return `你是“一键一生”半导体晶圆良率根因分析平台右侧的 **AI 伴读助手**。
你的职责有三：① **伴读**——阅读并解释当前 HTML 页面内容；② **分析**——对晶圆全生命周期数据做良率根因分析；③ **建议**——指引用户在页面中正确提交“一键一生”任务，并给出处置建议。

## 领域知识
- 晶圆一生：前道(光刻/刻蚀/注入/沉积/CMP) → 中测(WAT/CP) → 后道(封装/FT)。
- 根因分析常用维度：设备/腔体关联(commonality)、工艺步骤、参数漂移(WAT SPC)、缺陷空间特征(edge ring/center/scratch/cluster)、批次谱系。
- 缺陷空间特征强烈暗示根因环节：edge ring↔边缘刻蚀/清洗/膜厚；center↔CMP/旋涂/温场中心；scratch↔机械搬运/CMP；cluster↔腔体颗粒污染。

## 工作方式（重要）
- 你可以调用页面工具来真正操作界面（填表、设维度、提交、定位面板、套用习惯）。当用户意图明确时，**优先用工具完成动作**，而不是只口头描述。
- 当表单未就绪时，用 set_scenario / set_analysis_dims 帮其补全，再 run_lifecycle 提交。
- 回答用中文、简洁、结构化（可用要点/小标题）。结论要给出关联度/置信度。
- 不要编造未在上下文中的具体数值；基于提供的 result 数据说话。

${intentHint}

## 当前页面上下文（实时快照）
${JSON.stringify(context, null, 0)}${habit}`;
}

const FOLLOWUPS = {
  companion: ['帮我分析根因', '这个良率正常吗？', '带我看晶圆图'],
  analyze: ['给我处置建议', '为什么怀疑这台设备？', '看缺陷 Pareto'],
  advise: ['按建议修正并提交', '用我的习惯填表', '导出报告'],
  chat: ['伴读这个页面', '分析根因', '我该怎么填表'],
};

app.post('/api/chat', async (req, res) => {
  const { intent = 'chat', userMessage = '', context = {}, history = [], tools = [] } = req.body || {};
  if (!hasKey) {
    return res.status(503).json({ error: 'no_api_key', text: '后端未配置 ANTHROPIC_API_KEY，请使用本地推理模式。' });
  }
  try {
    const userTurn = userMessage ||
      { companion: '请伴读当前页面。', analyze: '请基于当前数据分析根因。', advise: '请指引我正确提交一键一生或给出建议。' }[intent] ||
      '请帮助我。';

    const messages = [
      ...history.map(h => ({ role: h.role === 'assistant' ? 'assistant' : 'user', content: String(h.content) })),
      { role: 'user', content: userTurn },
    ];

    const resp = await client.messages.create({
      model: MODEL,
      max_tokens: 1500,
      // 交互式侧边栏，medium effort 在质量/延迟间平衡（agent-design 推荐）
      thinking: { type: 'adaptive' },
      output_config: { effort: 'medium' },
      system: buildSystem(context, intent),
      tools: tools && tools.length ? tools : undefined,
      messages,
    });

    let text = '';
    const toolCalls = [];
    for (const block of resp.content) {
      if (block.type === 'text') text += block.text;
      else if (block.type === 'tool_use') toolCalls.push({ name: block.name, input: block.input });
    }

    res.json({ text: text.trim(), toolCalls, followups: FOLLOWUPS[intent] || FOLLOWUPS.chat });
  } catch (e) {
    console.error('[chat] error:', e.message);
    res.status(500).json({ error: 'claude_error', text: '调用 Claude 失败：' + e.message });
  }
});

app.get('/api/health', (_req, res) => res.json({ ok: true, model: MODEL, claude: hasKey }));

app.listen(PORT, () => {
  console.log(`\n  ◧ 一键一生 + AI 助手  →  http://localhost:${PORT}`);
  console.log(`  Claude 模式: ${hasKey ? '已启用 (' + MODEL + ')' : '未配置 Key（前端将用本地推理）'}\n`);
});
