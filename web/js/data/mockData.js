/*
 * mockData.js — 合成晶圆全生命周期数据
 * 用于“一键一生”Demo。生产环境应替换为 MES / YMS / EDA 数据源。
 */
(function (global) {
  'use strict';

  // ---- 基础维度 ----
  const FABS = ['Fab12-A', 'Fab12-B', 'Fab8-C'];
  const NODES = ['28nm', '14nm', '7nm'];
  const PRODUCTS = ['LP-SoC-A1', 'NPU-X2', 'PMIC-D3'];
  const STAGES = [
    { key: 'incoming', name: '来料/Epitaxy', cat: '前道' },
    { key: 'litho', name: '光刻 Photolitho', cat: '前道' },
    { key: 'etch', name: '刻蚀 Etch', cat: '前道' },
    { key: 'implant', name: '离子注入 Implant', cat: '前道' },
    { key: 'depo', name: '薄膜沉积 Deposition', cat: '前道' },
    { key: 'cmp', name: '化学机械抛光 CMP', cat: '前道' },
    { key: 'wat', name: 'WAT 参数测试', cat: '中测' },
    { key: 'cp', name: 'CP 晶圆探针', cat: '中测' },
    { key: 'assembly', name: '封装 Assembly', cat: '后道' },
    { key: 'ft', name: '成品测试 FT', cat: '后道' },
  ];
  // 缺陷特征签名
  const DEFECT_SIGNATURES = [
    { key: 'edge_ring', name: '边缘环状 (Edge Ring)', hint: '常关联清洗/边缘刻蚀或薄膜均匀性' },
    { key: 'center', name: '中心聚集 (Center)', hint: '常关联CMP压力/旋涂或温场中心偏差' },
    { key: 'scratch', name: '划伤 (Scratch)', hint: '常关联机械手/搬运/CMP研磨' },
    { key: 'cluster', name: '局部簇 (Cluster)', hint: '常关联颗粒污染/某腔体异常' },
    { key: 'random', name: '随机分布 (Random)', hint: '基线缺陷，关联性弱' },
  ];

  // 简单可复现伪随机
  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  // ---- 生成 wafer map（die 级 bin 图）----
  function makeWaferMap(rand, signature, baseYield) {
    const D = 21; // 21x21 网格
    const r = D / 2 - 0.5;
    const cells = [];
    let good = 0, total = 0;
    for (let y = 0; y < D; y++) {
      for (let x = 0; x < D; x++) {
        const dx = x - (D - 1) / 2, dy = y - (D - 1) / 2;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > r) { cells.push({ x, y, bin: -1 }); continue; } // 圆外
        total++;
        let failP = (100 - baseYield) / 100 * 0.5; // 基线失效率
        const norm = dist / r;
        if (signature === 'edge_ring') failP += norm > 0.78 ? 0.65 : 0.02;
        else if (signature === 'center') failP += norm < 0.28 ? 0.6 : 0.02;
        else if (signature === 'scratch') {
          // 一条斜线
          if (Math.abs(dy - dx * 0.6) < 0.9) failP += 0.7;
        } else if (signature === 'cluster') {
          const cxd = x - D * 0.7, cyd = y - D * 0.35;
          if (Math.sqrt(cxd * cxd + cyd * cyd) < 3) failP += 0.7;
        } else failP += 0.05;
        const bin = rand() < failP ? (1 + Math.floor(rand() * 4)) : 0; // 0=good
        if (bin === 0) good++;
        cells.push({ x, y, bin });
      }
    }
    return { grid: D, cells, dieYield: total ? (good / total) * 100 : 0, total };
  }

  // ---- 生成工艺流程 timeline（含设备/参数）----
  function makeProcessFlow(rand, anomalyStageKey, anomalyTool) {
    const start = new Date('2026-05-20T08:00:00');
    let cursor = start.getTime();
    return STAGES.map((s, i) => {
      cursor += (2 + rand() * 10) * 3600 * 1000; // 每步间隔小时
      const toolId = `${s.key.toUpperCase()}-${String(1 + Math.floor(rand() * 4)).padStart(2, '0')}`;
      const isAnomaly = s.key === anomalyStageKey;
      const tool = isAnomaly && anomalyTool ? anomalyTool : toolId;
      return {
        ...s,
        order: i,
        time: new Date(cursor).toISOString(),
        tool,
        chamber: `CH${1 + Math.floor(rand() * 6)}`,
        recipe: `${s.key}_rcp_v${1 + Math.floor(rand() * 3)}`,
        anomaly: isAnomaly,
        // 关键参数（注入到关联分析）
        param: +(50 + rand() * 50 + (isAnomaly ? 18 : 0)).toFixed(2),
        paramName: s.key === 'cmp' ? '研磨压力(psi)' : s.key === 'etch' ? '刻蚀速率(nm/s)' : s.key === 'depo' ? '膜厚(Å)' : '工艺指标',
      };
    });
  }

  // ---- WAT 参数趋势（多批次）----
  function makeWatTrend(rand, drift) {
    const params = ['Vth(mV)', 'Idsat(uA)', 'Ron(Ω)', 'Leakage(nA)'];
    const lots = 12;
    return params.map((p, pi) => ({
      param: p,
      series: Array.from({ length: lots }, (_, i) => {
        const driftEffect = drift && pi === 0 ? (i / lots) * 14 : 0; // Vth 漂移
        return +(100 + Math.sin(i / 2) * 6 + (rand() - 0.5) * 8 + driftEffect).toFixed(2);
      }),
      ucl: 118, lcl: 82,
    }));
  }

  // ---- 良率随时间趋势 ----
  function makeYieldTrend(rand, baseYield, hasExcursion) {
    return Array.from({ length: 20 }, (_, i) => {
      let y = baseYield + (rand() - 0.5) * 4;
      if (hasExcursion && i >= 12 && i <= 15) y -= 11 + rand() * 6; // 良率掉坑 excursion
      return { lot: `LotW${String(i + 1).padStart(2, '0')}`, yield: +Math.max(40, Math.min(99, y)).toFixed(1) };
    });
  }

  // ---- 缺陷 Pareto ----
  function makeDefectPareto(rand, signature) {
    const base = {
      edge_ring: { '边缘膜厚不均': 38, '清洗残留': 22, '颗粒': 12, '划伤': 6, '其他': 8 },
      center: { 'CMP中心碟形': 34, '旋涂中心厚': 20, '颗粒': 14, '套刻偏移': 9, '其他': 7 },
      scratch: { '机械划伤': 41, '搬运磕碰': 18, '颗粒': 12, '研磨异常': 10, '其他': 6 },
      cluster: { '腔体颗粒污染': 36, '气体异常': 17, 'Arc放电': 13, '颗粒': 11, '其他': 9 },
      random: { '颗粒': 20, '套刻偏移': 16, '膜厚': 15, '划伤': 13, '其他': 22 },
    }[signature] || {};
    return Object.entries(base).map(([k, v]) => ({ type: k, count: Math.round(v + (rand() - 0.5) * 4) }))
      .sort((a, b) => b.count - a.count);
  }

  // ---- 主入口：根据 waferId 生成一致的一生数据 ----
  function generateLifecycle(opts) {
    opts = opts || {};
    const waferId = opts.waferId || 'W-2026-0512-07';
    const seed = hash(waferId + (opts.salt || ''));
    const rand = mulberry32(seed);

    const sigPick = DEFECT_SIGNATURES[Math.floor(rand() * (DEFECT_SIGNATURES.length - 1))]; // 偏向非random
    const signature = opts.signature || sigPick.key;
    const baseYield = opts.baseYield != null ? opts.baseYield : 72 + rand() * 18;
    const hasExcursion = rand() > 0.35;
    const drift = rand() > 0.5;

    // 关联到某设备腔体的异常（注入“根因”）
    const stageOfSignature = {
      edge_ring: 'etch', center: 'cmp', scratch: 'cmp', cluster: 'depo', random: 'litho',
    }[signature];
    const anomalyTool = `${stageOfSignature.toUpperCase()}-0${1 + Math.floor(rand() * 2)}`;

    const wmap = makeWaferMap(rand, signature, baseYield);
    const flow = makeProcessFlow(rand, stageOfSignature, anomalyTool);

    return {
      meta: {
        waferId,
        lot: 'Lot-' + waferId.split('-').slice(1, 3).join(''),
        fab: opts.fab || FABS[Math.floor(rand() * FABS.length)],
        node: opts.node || NODES[Math.floor(rand() * NODES.length)],
        product: opts.product || PRODUCTS[Math.floor(rand() * PRODUCTS.length)],
        slot: 1 + Math.floor(rand() * 25),
        generatedAt: new Date().toISOString(),
      },
      summary: {
        finalYield: +wmap.dieYield.toFixed(1),
        signature,
        signatureName: (DEFECT_SIGNATURES.find(d => d.key === signature) || {}).name,
        signatureHint: (DEFECT_SIGNATURES.find(d => d.key === signature) || {}).hint,
        rootCauseStage: stageOfSignature,
        rootCauseStageName: (STAGES.find(s => s.key === stageOfSignature) || {}).name,
        suspectTool: anomalyTool,
        hasExcursion, drift,
        dieTotal: wmap.total,
      },
      waferMap: wmap,
      processFlow: flow,
      watTrend: makeWatTrend(rand, drift),
      yieldTrend: makeYieldTrend(rand, baseYield, hasExcursion),
      defectPareto: makeDefectPareto(rand, signature),
    };
  }

  // 设备关联分析（commonality）— 根因候选打分
  function computeCommonality(data) {
    const s = data.summary;
    const candidates = [
      {
        dim: '设备腔体关联', target: `${s.suspectTool}`,
        score: 0.86, evidence: `${s.rootCauseStageName} 步骤经过 ${s.suspectTool}，与低良率晶圆高度重叠`,
      },
      {
        dim: '缺陷特征', target: s.signatureName,
        score: 0.81, evidence: s.signatureHint,
      },
      {
        dim: '参数漂移', target: data.watTrend[0].param,
        score: s.drift ? 0.74 : 0.41,
        evidence: s.drift ? 'Vth 随批次单调漂移，疑似工艺窗口偏移' : '参数在控制限内，关联性弱',
      },
      {
        dim: '良率突降', target: '批次 excursion',
        score: s.hasExcursion ? 0.7 : 0.3,
        evidence: s.hasExcursion ? '存在连续批次良率掉坑，建议核查时间段内换料/PM记录' : '无明显突降',
      },
    ].sort((a, b) => b.score - a.score);
    return candidates;
  }

  global.WaferData = {
    FABS, NODES, PRODUCTS, STAGES, DEFECT_SIGNATURES,
    generateLifecycle, computeCommonality,
  };
})(window);
