/*
 * tools.js — AI 助手可调用的“动作”（前端工具/函数调用）
 * 每个工具都有 schema（描述给 LLM）+ run（在页面上真正执行）。
 * 这是“智能体技术”的落点：AI 不只是聊天，而是能操作 HTML 页面。
 * schema 同时被注入到真实 Claude API 的 tools 参数中。
 */
(function (global) {
  'use strict';

  // app 在初始化时注入回调，避免循环依赖
  let app = null;
  function bind(appApi) { app = appApi; }

  const tools = {
    set_scenario: {
      schema: {
        name: 'set_scenario',
        description: '填写或修改“场景设定”表单字段（Wafer ID、Fab、节点、产品、缺陷特征、时间范围）。用于帮助用户正确提交一键一生任务。',
        input_schema: {
          type: 'object',
          properties: {
            waferId: { type: 'string', description: 'Wafer ID 或 Lot，形如 W-2026-0512-07' },
            fab: { type: 'string', enum: ['Fab12-A', 'Fab12-B', 'Fab8-C'] },
            node: { type: 'string', enum: ['28nm', '14nm', '7nm'] },
            product: { type: 'string', enum: ['LP-SoC-A1', 'NPU-X2', 'PMIC-D3'] },
            signature: { type: 'string', enum: ['', 'edge_ring', 'center', 'scratch', 'cluster', 'random'], description: '预期缺陷特征，留空表示自动识别' },
            timeRange: { type: 'string', enum: ['7d', '30d', '90d'] },
          },
        },
      },
      run: (args) => app.setScenario(args || {}),
    },
    set_analysis_dims: {
      schema: {
        name: 'set_analysis_dims',
        description: '勾选分析维度（设备关联、工艺步骤、参数漂移、缺陷特征、批次谱系）。',
        input_schema: {
          type: 'object',
          properties: {
            dims: { type: 'array', items: { type: 'string', enum: ['equipment', 'process', 'param', 'defect', 'genealogy'] } },
          },
          required: ['dims'],
        },
      },
      run: (args) => app.setAnalysisDims((args && args.dims) || []),
    },
    run_lifecycle: {
      schema: {
        name: 'run_lifecycle',
        description: '提交并执行“一键一生”分析，渲染晶圆全生命周期可视化与根因结果。校验通过后才应调用。',
        input_schema: { type: 'object', properties: {} },
      },
      run: () => app.runLifecycle(),
    },
    focus_panel: {
      schema: {
        name: 'focus_panel',
        description: '高亮/滚动到某个结果面板，引导用户关注。panel 取值：waferMap | yieldTrend | watTrend | defectPareto | processFlow | rootCause',
        input_schema: {
          type: 'object',
          properties: { panel: { type: 'string', enum: ['waferMap', 'yieldTrend', 'watTrend', 'defectPareto', 'processFlow', 'rootCause'] } },
          required: ['panel'],
        },
      },
      run: (args) => app.focusPanel(args && args.panel),
    },
    apply_my_habits: {
      schema: {
        name: 'apply_my_habits',
        description: '根据该用户历史习惯画像，自动套用其最常用的 Fab/节点/产品/分析维度作为默认值。',
        input_schema: { type: 'object', properties: {} },
      },
      run: () => app.applyHabits(),
    },
  };

  function list() { return Object.values(tools).map(t => t.schema); }

  function execute(name, args) {
    const t = tools[name];
    if (!t) return { ok: false, error: 'unknown tool: ' + name };
    try {
      const result = t.run(args) || {};
      return { ok: true, name, result };
    } catch (e) {
      return { ok: false, name, error: String(e && e.message || e) };
    }
  }

  global.AgentTools = { bind, list, execute, _all: tools };
})(window);
