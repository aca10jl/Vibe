/* charts.js — 基于 ECharts 的可视化封装 */
(function (global) {
  'use strict';
  const instances = {};

  function getChart(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    if (!instances[id]) instances[id] = echarts.init(el, null, { renderer: 'canvas' });
    return instances[id];
  }

  const BIN_COLORS = {
    '-1': 'transparent', // 圆外
    0: '#1f9d55',        // good
    1: '#f0a020', 2: '#e0533d', 3: '#b5179e', 4: '#7b2ff7',
  };

  function renderWaferMap(data) {
    const c = getChart('waferMap'); if (!c) return;
    const D = data.waferMap.grid;
    const pts = data.waferMap.cells.filter(d => d.bin !== -1)
      .map(d => [d.x, d.y, d.bin]);
    c.setOption({
      tooltip: {
        formatter: p => `Die (${p.value[0]},${p.value[1]})<br/>Bin: ${p.value[2] === 0 ? '良品' : 'Fail-' + p.value[2]}`,
      },
      grid: { top: 8, bottom: 8, left: 8, right: 8 },
      xAxis: { type: 'value', min: -1, max: D, show: false },
      yAxis: { type: 'value', min: -1, max: D, show: false, inverse: true },
      series: [{
        type: 'scatter', symbol: 'rect', symbolSize: 12,
        data: pts,
        itemStyle: { color: p => BIN_COLORS[p.value[2]] || '#999', borderColor: '#0b1220', borderWidth: 0.5 },
      }],
    }, true);
  }

  function renderYieldTrend(data) {
    const c = getChart('yieldTrend'); if (!c) return;
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 18, bottom: 40, left: 44, right: 14 },
      xAxis: { type: 'category', data: data.yieldTrend.map(d => d.lot), axisLabel: { rotate: 45, fontSize: 9, color: '#9fb3c8' } },
      yAxis: { type: 'value', min: 40, max: 100, axisLabel: { color: '#9fb3c8' }, splitLine: { lineStyle: { color: '#1e2a3a' } } },
      series: [{
        type: 'line', smooth: true, data: data.yieldTrend.map(d => d.yield),
        areaStyle: { color: 'rgba(31,157,85,0.15)' }, lineStyle: { color: '#1f9d55' }, itemStyle: { color: '#1f9d55' },
        markLine: { silent: true, data: [{ yAxis: 80, lineStyle: { color: '#e0533d', type: 'dashed' }, label: { formatter: '良率基线 80%' } }] },
      }],
    }, true);
  }

  function renderWatTrend(data) {
    const c = getChart('watTrend'); if (!c) return;
    const p0 = data.watTrend[0];
    c.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: data.watTrend.map(d => d.param), textStyle: { color: '#9fb3c8', fontSize: 9 }, top: 0 },
      grid: { top: 28, bottom: 24, left: 40, right: 14 },
      xAxis: { type: 'category', data: p0.series.map((_, i) => 'L' + (i + 1)), axisLabel: { color: '#9fb3c8', fontSize: 9 } },
      yAxis: { type: 'value', axisLabel: { color: '#9fb3c8' }, splitLine: { lineStyle: { color: '#1e2a3a' } } },
      series: data.watTrend.map(d => ({ name: d.param, type: 'line', smooth: true, data: d.series, symbolSize: 4 })),
    }, true);
  }

  function renderDefectPareto(data) {
    const c = getChart('defectPareto'); if (!c) return;
    const total = data.defectPareto.reduce((s, d) => s + d.count, 0);
    let cum = 0;
    const cumLine = data.defectPareto.map(d => { cum += d.count; return +(cum / total * 100).toFixed(1); });
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 18, bottom: 60, left: 40, right: 40 },
      xAxis: { type: 'category', data: data.defectPareto.map(d => d.type), axisLabel: { rotate: 30, fontSize: 9, color: '#9fb3c8' } },
      yAxis: [
        { type: 'value', axisLabel: { color: '#9fb3c8' }, splitLine: { lineStyle: { color: '#1e2a3a' } } },
        { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: '#9fb3c8' }, splitLine: { show: false } },
      ],
      series: [
        { type: 'bar', data: data.defectPareto.map(d => d.count), itemStyle: { color: '#3b82f6' } },
        { type: 'line', yAxisIndex: 1, data: cumLine, itemStyle: { color: '#f0a020' }, lineStyle: { color: '#f0a020' } },
      ],
    }, true);
  }

  function renderProcessFlow(data) {
    const el = document.getElementById('processFlow'); if (!el) return;
    el.innerHTML = data.processFlow.map(s => `
      <div class="flow-node ${s.anomaly ? 'flow-anomaly' : ''}" title="${s.recipe}">
        <div class="flow-cat">${s.cat}</div>
        <div class="flow-name">${s.name}</div>
        <div class="flow-tool">${s.tool} · ${s.chamber}</div>
        <div class="flow-time">${new Date(s.time).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}</div>
        ${s.anomaly ? '<div class="flow-flag">⚠ 疑似异常</div>' : ''}
      </div>`).join('<div class="flow-arrow">→</div>');
  }

  function renderAll(data) {
    renderWaferMap(data); renderYieldTrend(data); renderWatTrend(data);
    renderDefectPareto(data); renderProcessFlow(data);
  }

  window.addEventListener('resize', () => Object.values(instances).forEach(c => c.resize()));

  global.WaferCharts = { renderAll, renderWaferMap, renderYieldTrend, renderWatTrend, renderDefectPareto, renderProcessFlow, getChart };
})(window);
