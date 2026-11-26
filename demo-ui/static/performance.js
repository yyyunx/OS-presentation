'use strict';

const get = id => document.getElementById(id);
const units = new Intl.NumberFormat('zh-TW', {maximumSignificantDigits: 4});
const number = value => value == null ? '—' : units.format(value);
const mib = value => number(value / 1048576);
const labels = {
  'cache-locality': 'Cache Locality',
  'matrix-traversal': 'Matrix Traversal',
  'false-sharing': 'False Sharing',
  'mutex-atomic': 'Mutex vs Atomic',
  'cpu-affinity': 'CPU Affinity',
  'memory-alignment': 'Memory Alignment',
  'simd': 'SIMD Vectorization',
  'memory-bandwidth': 'Memory Bandwidth',
  'branch-prediction': 'Branch Prediction',
  'context-switch': 'Context Switch',
};

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function render(report, name) {
  const experiment = report.experiments[name];
  const metric = experiment.primary_metric;
  const bandwidth = metric === 'logical_gib_per_sec';
  const chart = get('chart');
  const body = get('statistics');
  const counters = get('counters');
  chart.replaceChildren();
  body.replaceChildren();
  counters.replaceChildren();
  get('metric').textContent = bandwidth ? '邏輯傳輸量（GiB/s）' : '批次平均耗時（ns/op）';
  get('description').textContent = bandwidth
    ? '每個長條為各 trial 中位數，copy 計入 payload 的一次讀取與一次寫入。'
    : '每個長條為各 trial 中位數。操作單位為 ' + experiment.operation + '。';
  const entries = Object.entries(experiment.variants);
  const max = Math.max(0, ...entries.map(([, series]) => series.summary?.[metric]?.median ?? 0));
  for (const [variant, series] of entries) {
    const row = element('tr');
    const header = element('th', variant);
    header.scope = 'row';
    row.append(header);
    body.append(row);
    if (series.status !== 'ok') {
      const missing = element('td', 'unavailable · ' + series.reason);
      missing.colSpan = 6;
      row.append(missing);
      continue;
    }
    const stats = series.summary;
    const selected = stats[metric];
    const bar = element('div');
    bar.className = 'series';
    const meter = element('meter');
    meter.max = max;
    meter.value = selected.median;
    meter.setAttribute('aria-label', variant);
    bar.append(element('span', variant), meter, element('span', number(selected.median)));
    chart.append(bar);

    const values = [
      number(selected.median), number(selected.p95), number(selected.stdev),
      number(stats.cpu_utilization_pct.median) + '%',
      mib(stats.peak_rss_bytes.median) + ' MiB',
      number(stats.voluntary_switches.median) + ' / ' + number(stats.involuntary_switches.median),
    ];
    row.append(...values.map(value => element('td', value)));

    const list = element('ul');
    for (const [event, result] of Object.entries(series.perf)) {
      const value = result.status === 'ok'
        ? number(result.value) + (result.running_pct === undefined ? '' : ' (' + number(result.running_pct) + '% running)')
        : 'unavailable · ' + result.reason;
      list.append(element('li', event + ' · ' + value));
    }
    counters.append(element('h3', variant), list);
  }
}

async function load() {
  const response = await fetch('/api/performance');
  if (response.status === 404) {
    get('provenance').textContent = '尚無量測。從專案目錄執行 make benchmark 後重新整理。';
    return;
  }
  if (!response.ok) throw new Error('資料讀取失敗');
  const report = await response.json();
  if (report.schema_version !== 1) throw new Error('不支援此結果格式');
  const env = report.environment;
  const settings = report.settings;
  const select = get('experiment');
  get('provenance').textContent = [
    new Date(report.started_at_utc).toLocaleString(), env.cpu_model || 'CPU 型號未知',
    settings.environment_label, env.virtualization, settings.profile, settings.trials + ' trials',
  ].filter(Boolean).join(' · ');
  const fields = [
    ['Run ID', report.run_id], ['UTC', report.started_at_utc], ['OS', env.distribution + ' / ' + env.kernel],
    ['Compiler', env.compiler], ['Compiler flags', env.flags],
    ['Allowed logical CPUs', (env.allowed_cpus || []).join(', ')],
    ['Warm-ups / Seed', settings.warmups + ' / ' + settings.seed],
    ['Benchmark binary SHA-256', env.binary_sha256],
  ];
  const details = get('environment');
  for (const [key, value] of fields) details.append(element('dt', key), element('dd', value));
  for (const name of Object.keys(report.experiments)) {
    const option = element('option', labels[name] || name);
    option.value = name;
    select.append(option);
  }
  select.addEventListener('change', () => render(report, select.value));
  render(report, select.value);
  get('results').hidden = false;
}

load().catch(error => {
  get('provenance').textContent = '無法顯示量測 · ' + error.message;
});
