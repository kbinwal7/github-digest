const $ = id => document.getElementById(id);
const today = new Date();
const localDate = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
$('end').value = localDate(today);
$('start').value = localDate(new Date(today.getTime() - 86400000));

// Tabs
for (const btn of document.querySelectorAll('[data-tab]')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-tab]').forEach(x => x.classList.toggle('active', x === btn));
    document.querySelectorAll('.panel').forEach(x => x.classList.toggle('active', x.id === btn.dataset.tab));
  });
}

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = value => {
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) ? u.href : '#'; }
  catch { return '#'; }
};
async function api(path, body) {
  const response = await fetch(path, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  let data;
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  return data;
}
function loading(message) { return `<div class="loading-state"><span class="spinner"></span>${esc(message)}</div>`; }
function errorBox(error) { return `<div class="notice">${esc(error.message || error)}</div>`; }

// A small, conservative Markdown renderer. All source text is escaped before markup is added.
// Raw HTML from model output is therefore displayed as text, never executed.
function inlineMarkdown(source) {
  let s = esc(source);
  const code = [];
  s = s.replace(/`([^`]+)`/g, (_, value) => { code.push(`<code>${value}</code>`); return `\u0000CODE${code.length - 1}\u0000`; });
  s = s.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g, '<span class="image-alt">[Image: $1]</span>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)(?:\s+"[^"]*")?\)/g, (_, label, url) => `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`);
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/__(.+?)__/g, '<strong>$1</strong>');
  s = s.replace(/\*(.+?)\*/g, '<em>$1</em>').replace(/_(.+?)_/g, '<em>$1</em>').replace(/~~(.+?)~~/g, '<del>$1</del>');
  s = s.replace(/(^|\s)(https?:\/\/[^\s<]+)/g, (_, lead, url) => `${lead}<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${url}</a>`);
  return s.replace(/\u0000CODE(\d+)\u0000/g, (_, i) => code[Number(i)]);
}
function renderMarkdown(markdown = '') {
  const lines = String(markdown).replace(/\r/g, '').split('\n');
  const out = []; let paragraph = [], list = null, codeLines = [], inCode = false;
  const flushParagraph = () => { if (paragraph.length) { out.push(`<p>${paragraph.map(inlineMarkdown).join('<br>')}</p>`); paragraph = []; } };
  const flushList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const line of lines) {
    if (/^\s*```/.test(line)) { flushParagraph(); flushList(); if (inCode) { out.push(`<pre><code>${esc(codeLines.join('\n'))}</code></pre>`); codeLines = []; inCode = false; } else inCode = true; continue; }
    if (inCode) { codeLines.push(line); continue; }
    let m;
    if (!line.trim()) { flushParagraph(); flushList(); continue; }
    if ((m = line.match(/^\s{0,3}(#{1,4})\s+(.+)$/))) { flushParagraph(); flushList(); const level = m[1].length; out.push(`<h${level}>${inlineMarkdown(m[2])}</h${level}>`); continue; }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(line)) { flushParagraph(); flushList(); out.push('<hr>'); continue; }
    if ((m = line.match(/^\s*>\s?(.*)$/))) { flushParagraph(); flushList(); out.push(`<blockquote>${inlineMarkdown(m[1])}</blockquote>`); continue; }
    if ((m = line.match(/^\s*[-*+]\s+(.+)$/)) || (m = line.match(/^\s*\d+[.)]\s+(.+)$/))) {
      flushParagraph(); const type = /^\s*\d/.test(line) ? 'ol' : 'ul'; if (list !== type) { flushList(); list = type; out.push(`<${list}>`); } out.push(`<li>${inlineMarkdown(m[1])}</li>`); continue;
    }
    flushList(); paragraph.push(line);
  }
  if (inCode) out.push(`<pre><code>${esc(codeLines.join('\n'))}</code></pre>`);
  flushParagraph(); flushList();
  return `<div class="markdown">${out.join('')}</div>`;
}
function formatDate(value) { return value ? String(value).slice(0, 10) : '—'; }
function itemCard(kind, item) {
  const isCommit = kind === 'commit';
  const title = isCommit ? item.message : item.title;
  const id = isCommit ? String(item.sha || '').slice(0, 8) : `#${item.number ?? ''}`;
  const meta = [id, item.author, formatDate(isCommit ? item.date : item.created_at), kind];
  const labels = Array.isArray(item.labels) ? item.labels : [];
  return `<article class="item"><h3>${esc(title || 'Untitled activity')}</h3><div class="meta">${meta.map(esc).join('<span class="meta-sep">·</span>')}</div>${labels.length ? `<div class="label-row">${labels.map(x => `<span class="label-chip">${esc(x)}</span>`).join('')}</div>` : ''}<a class="item-link" href="${safeUrl(item.url)}" target="_blank" rel="noopener noreferrer">View on GitHub ↗</a></article>`;
}
function bindGroupTabs(root) {
  const buttons = [...root.querySelectorAll('[data-group]')];
  buttons.forEach(button => button.addEventListener('click', () => {
    buttons.forEach(x => x.classList.toggle('active', x === button));
    root.querySelectorAll('[data-content]').forEach(content => content.hidden = content.dataset.content !== button.dataset.group);
  }));
}

$('digest-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const output = $('digest-result'); button.disabled = true; output.innerHTML = loading('Collecting repository activity and indexing open issues…');
  try {
    const data = await api('/api/digest', { repository: $('repo').value.trim(), start_date: $('start').value, end_date: $('end').value });
    $('search-repo').value = data.repository || $('repo').value.trim();
    const groups = [['Commits', data.commits || []], ['Pull requests', data.pull_requests || []], ['Issues', data.issues || []]];
    const total = groups.reduce((sum, group) => sum + group[1].length, 0);
    output.innerHTML = `<div class="section-kicker">${esc(data.repository)} <span class="meta-sep">/</span> ${esc(data.start_date)} — ${esc(data.end_date)}</div>
      <div class="metric-grid">${[['TOTAL ACTIVITY',total],['COMMITS',groups[0][1].length],['PULL REQUESTS',groups[1][1].length],['ISSUES',groups[2][1].length]].map(([label,value]) => `<div class="metric"><span class="meta">${label}</span><strong>${value}</strong></div>`).join('')}</div>
      ${data.truncated ? '<div class="notice">The fetch reached its page limit. Narrow the date window for a more complete result.</div>' : ''}
      <div class="notice">Issue indexing: <strong>${esc(data.indexing?.status || 'unknown')}</strong> &nbsp;·&nbsp; ${esc(data.indexing?.indexed ?? 0)} indexed</div>
      <div class="result-tabs">${groups.map(([name,items],i) => `<button class="${i===0?'active':''}" data-group="${i}">${name} (${items.length})</button>`).join('')}</div>
      <div id="group-content">${groups.map(([name,items],i) => `<div data-content="${i}" ${i?'hidden':''}>${items.length ? items.slice(0,50).map(item => itemCard(name==='Commits'?'commit':name==='Issues'?'issue':'pull request',item)).join('') : '<div class="notice">No activity in this date window.</div>'}</div>`).join('')}</div>`;
    bindGroupTabs(output);
  } catch (error) { output.innerHTML = errorBox(error); }
  finally { button.disabled = false; }
});

$('search-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const output = $('search-result'); button.disabled = true; output.innerHTML = loading('Searching indexed issues and preparing contribution advice…');
  try {
    const data = await api('/api/search', { query: $('query').value.trim(), repository: $('search-repo').value.trim() || null, limit: Number($('limit').value) });
    const matches = data.matches || [];
    output.innerHTML = `<div class="section-kicker">MATCHED ISSUES <span class="meta-sep">/</span> ${matches.length} RESULTS</div>
      ${matches.map(match => `<article class="item"><h3>${esc(match.title || 'Untitled issue')}</h3><div class="meta"><span>${esc(match.repo || 'Repository')}</span><span class="meta-sep">·</span><span class="score-chip">MATCH ${Number.isFinite(Number(match.score)) ? Number(match.score).toFixed(3) : '—'}</span></div>${renderMarkdown(String(match.text || '').slice(0, 4500))}<a class="item-link" href="${safeUrl(match.url)}" target="_blank" rel="noopener noreferrer">Open issue on GitHub ↗</a></article>`).join('') || '<div class="notice">No matching issues found. Try a broader description or index another repository first.</div>'}
      <section class="advice"><div class="advice-heading"><span class="advice-icon">✳</span> AI CONTRIBUTION ADVICE</div>${renderMarkdown(data.advice || 'No additional advice was returned.')}</section>`;
  } catch (error) { output.innerHTML = errorBox(error); }
  finally { button.disabled = false; }
});
