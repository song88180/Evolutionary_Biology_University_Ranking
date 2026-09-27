(() => {
  'use strict';
  const data = window.RANKING_DATA;
  const paperData = window.PAPER_DATA;
  if (!data || !Array.isArray(data.ranking) || !paperData || !Array.isArray(paperData.included)) return;

  const body = document.getElementById('ranking-body');
  const search = document.getElementById('search');
  const resultCount = document.getElementById('result-count');
  const dialog = document.getElementById('paper-dialog');
  const paperSearch = document.getElementById('paper-search');
  const paperList = document.getElementById('paper-list');
  const paperCount = document.getElementById('paper-count');
  const languageToggle = document.getElementById('language-toggle');
  const universityTab = document.getElementById('universities-tab');
  const papersTab = document.getElementById('papers-tab');
  const universityPanel = document.getElementById('universities-panel');
  const papersPanel = document.getElementById('papers');
  const allPaperSearch = document.getElementById('all-paper-search');
  const journalFilter = document.getElementById('journal-filter');
  const allPaperList = document.getElementById('all-paper-list');
  const allPaperCount = document.getElementById('all-paper-count');
  const loadMore = document.getElementById('load-more-papers');
  const formatScore = number => new Intl.NumberFormat('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(number);
  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const chinese = [
    ['.brand-label', '进化生物学<br>大学排名'],
    ['.site-header nav a:nth-child(1)', '排名'],
    ['.site-header nav a:nth-child(2)', '论文'],
    ['.site-header nav a:nth-child(3)', '排名规则'],
    ['.site-header nav a:nth-child(4)', '数据'],
    ['.hero .eyebrow', '<span class="live-dot"></span> 最终排名 · 2026 年版'],
    ['#hero-title', '进化研究，<br><em>世界何处领先？</em>'],
    ['.hero-intro', '逐篇论文评估全球 ARWU 前 1,000 所大学的进化生物学研究。'],
    ['.hero-actions .button', '查看前 100 名 <span aria-hidden="true">↗</span>'],
    ['.hero-actions .text-link', '了解评分方法 <span aria-hidden="true">↓</span>'],
    ['.date-line', '论文发表时间 <strong>2025 年 9 月 24 日—2026 年 9 月 24 日</strong>'],
    ['.orbit-center span', '所大学'],
    ['.facts>div:nth-child(1) .fact-label', '上榜大学'],
    ['.facts>div:nth-child(2) .fact-label', '符合条件的论文'],
    ['.facts>div:nth-child(3) .fact-label', '研究期刊'],
    ['.facts>div:nth-child(4) .fact-number', '1 年'],
    ['.facts>div:nth-child(4) .fact-label', '发表时间范围'],
    ['.ranking-section .eyebrow', '排名结果'],
    ['#ranking-title', '查看研究结果'],
    ['.ranking-section .section-intro', '浏览前 100 所大学，或查看纳入分析的全部 2,378 篇进化生物学论文。'],
    ['#universities-tab', '大学排名 <span>100</span>'],
    ['#papers-tab', '纳入论文 <span>2,378</span>'],
    ['#universities-panel .panel-intro p', '按期刊影响因子分摊后的总分排序。点击大学可查看每篇计分论文。'],
    ['#papers .panel-intro p', '最终数据集中的每篇合格论文，包括未给前 100 名大学计分的论文。'],
    ['.ranking-section .download-link', '下载排名 CSV <span aria-hidden="true">↘</span>'],
    ['#papers .download-link', '下载全部论文 CSV <span aria-hidden="true">↘</span>'],
    ['#load-more-papers', '显示更多论文 ↓'],
    ['.ranking-section th:nth-child(1)', '名次'],
    ['.ranking-section th:nth-child(2)', '大学'],
    ['.ranking-section th:nth-child(3)', '得分'],
    ['.ranking-section th:nth-child(4)', '论文数'],
    ['.ranking-section th:nth-child(5)', '全额 / 分摊'],
    ['.table-note', '每篇论文的 2025 年期刊影响因子由所有不同的通讯作者所属机构平均分摊。页面显示两位小数；实际排名使用未四舍五入的分数。'],
    ['.method-lead .eyebrow', '排名方法'],
    ['#method-title', '逐篇论文，<br>统一规则。'],
    ['.method-lead>p:not(.eyebrow)', '仅纳入以进化为主要科学问题或结论的原创研究。论文须在指定的一年内首次在线发表于 11 种期刊之一。'],
    ['.method-lead .button', '下载全部论文计分明细 <span aria-hidden="true">↘</span>'],
    ['.method-step:nth-child(1) h3', '确定论文权重'],
    ['.method-step:nth-child(1) p', '每篇合格论文以其期刊的<strong>2025 年影响因子</strong>为起始分值。不使用引用量、声誉或大学规模等指标。'],
    ['.method-step:nth-child(2) h3', '分摊论文分值'],
    ['.method-step:nth-child(2) p', '分值由所有<strong>不同的通讯作者所属机构</strong>平均分摊。同一机构的多位通讯作者只计一次；非通讯作者的机构不计分。'],
    ['.method-step:nth-child(3) h3', '汇总并排名'],
    ['.method-step:nth-child(3) p', '累加各机构所得分值，仅对<strong>2026 年 ARWU 前 1,000 所大学</strong>排名。范围外机构保留自己的份额，不重新分配给上榜大学。'],
    ['.journal-section .eyebrow', '期刊范围'],
    ['#journals-title', '期刊权重'],
    ['.journal-section .section-intro', '同一期刊的每篇合格论文使用相同的 2025 年影响因子。'],
    ['.source-note', '本网站展示项目负责人确定的最终排名。其中 2,378 篇论文有 347 篇使用 OpenAlex 明确标记的通讯作者资料，其余使用出版商或文献库资料。可下载上方的论文计分明细独立核查。大学和论文的正式名称保留原文。'],
    ['footer p', '进化生物学大学排名 · 2026'],
    ['footer a', '返回顶部 ↑'],
  ];
  const staticTranslations = chinese.map(([selector, zh]) => {
    const element = document.querySelector(selector);
    if (!element) throw new Error(`Missing translation target: ${selector}`);
    return {element, en: element.innerHTML, zh};
  });
  const journalChinese = {
    'Nature': '《自然》', 'Science': '《科学》', 'Cell': '《细胞》',
    'Nature Ecology & Evolution': '《自然·生态与进化》',
    'Nature Genetics': '《自然·遗传学》',
    'Nature Human Behaviour': '《自然·人类行为》',
    'Proceedings of the National Academy of Sciences': '《美国国家科学院院刊》',
    'Science Advances': '《科学进展》',
    'Nature Communications': '《自然·通讯》',
    'Current Biology': '《当代生物学》',
    'Molecular Biology and Evolution': '《分子生物学与进化》',
  };
  let language = 'en';
  let selected = null;
  let visiblePaperCount = 30;
  let activeView = 'universities';

  function label(en, zh) { return language === 'zh' ? zh : en; }

  function applyLanguage(next) {
    language = next;
    document.documentElement.lang = next === 'zh' ? 'zh-CN' : 'en';
    document.title = label('Evolutionary Biology University Ranking 2026', '2026 年进化生物学大学排名');
    for (const item of staticTranslations) item.element.innerHTML = next === 'zh' ? item.zh : item.en;
    languageToggle.textContent = label('中文', 'English');
    languageToggle.setAttribute('aria-label', label('Switch to Chinese', '切换到英语'));
    document.querySelector('.brand').setAttribute('aria-label', label('Evolutionary Biology Ranking home', '进化生物学排名首页'));
    document.querySelector('.site-header nav').setAttribute('aria-label', label('Main navigation', '主导航'));
    document.querySelector('.facts').setAttribute('aria-label', label('Ranking at a glance', '排名概览'));
    document.querySelector('#search').placeholder = label('Search universities…', '搜索大学…');
    document.querySelector('#paper-search').placeholder = label('Search titles, journals, or DOIs…', '搜索论文标题、期刊或 DOI…');
    allPaperSearch.placeholder = label('Search title, author, or DOI…', '搜索标题、作者或 DOI…');
    document.querySelector('#dialog-close').setAttribute('aria-label', label('Close paper details', '关闭论文详情'));
    document.querySelector('.table-tools .sr-only').textContent = label('Search universities', '搜索大学');
    document.querySelector('.dialog-tools .sr-only').textContent = label('Search contributing papers', '搜索计分论文');
    document.querySelector('.paper-browser-tools .search-box .sr-only').textContent = label('Search all papers', '搜索全部论文');
    document.querySelector('.journal-filter-label .sr-only').textContent = label('Filter by journal', '按期刊筛选');
    document.querySelector('.result-tabs').setAttribute('aria-label', label('Results view', '结果视图'));
    try { localStorage.setItem('rankingLanguage', next); } catch (_) { /* file:// privacy mode */ }
    renderRanking();
    renderJournals();
    renderJournalFilter();
    renderAllPapers();
    if (selected) { renderDialogHeading(); renderPapers(); }
  }

  function cell(row, value, className = '') {
    const td = document.createElement('td');
    if (className) td.className = className;
    td.textContent = value;
    row.append(td);
    return td;
  }

  function renderRanking() {
    const term = normalize(search.value.trim());
    const filtered = data.ranking.filter(item => normalize(item.name).includes(term) || String(item.rank) === term);
    body.replaceChildren();
    const fragment = document.createDocumentFragment();
    for (const item of filtered) {
      const row = document.createElement('tr');
      row.tabIndex = 0;
      row.setAttribute('aria-label', label(`Rank ${item.rank}, ${item.name}, ${formatScore(item.score)} points. Show papers.`, `第 ${item.rank} 名，${item.name}，${formatScore(item.score)} 分。查看论文。`));
      const rank = cell(row, String(item.rank).padStart(2, '0'), `rank-cell${item.rank <= 3 ? ' rank-top' : ''}`);
      rank.setAttribute('data-label', label('Rank', '名次'));
      cell(row, item.name, 'university-name');
      cell(row, formatScore(item.score), 'numeric score').setAttribute('data-label', label('Score', '得分'));
      cell(row, String(item.papers), 'numeric').setAttribute('data-label', label('Papers', '论文数'));
      cell(row, `${item.full} / ${item.fractional}`, 'numeric breakdown').setAttribute('data-label', label('Full / Fractional', '全额 / 分摊'));
      cell(row, '↗', 'arrow-cell');
      row.addEventListener('click', () => openPapers(item));
      row.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openPapers(item);
        }
      });
      fragment.append(row);
    }
    if (!filtered.length) {
      const row = document.createElement('tr');
      const empty = cell(row, label('No universities match your search.', '没有符合搜索条件的大学。'), 'empty-row');
      empty.colSpan = 6;
      fragment.append(row);
    }
    body.append(fragment);
    resultCount.textContent = label(`Showing ${filtered.length} ${filtered.length === 1 ? 'university' : 'universities'}`, `显示 ${filtered.length} 所大学`);
  }

  function renderPapers() {
    if (!selected) return;
    const term = normalize(paperSearch.value.trim());
    const matches = paperData.contributions[selected.id].filter(paper =>
      normalize(`${paper.title} ${paper.journal} ${journalChinese[paper.journal] || ''} ${paper.doi}`).includes(term));
    paperList.replaceChildren();
    const fragment = document.createDocumentFragment();
    for (const paper of matches) {
      const item = document.createElement('article');
      item.className = 'paper-item';
      const left = document.createElement('div');
      const link = document.createElement('a');
      link.href = paper.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = paper.title;
      const meta = document.createElement('p');
      meta.className = 'paper-meta';
      meta.textContent = `${language === 'zh' ? journalChinese[paper.journal] || paper.journal : paper.journal} · ${paper.date} · ${paper.doi} · ${paper.source === 'OpenAlex' ? 'OpenAlex' : label('Publisher / repository', '出版商／文献库')}`;
      left.append(link, meta);
      const points = document.createElement('div');
      points.className = 'paper-points';
      points.textContent = formatScore(paper.points);
      const fraction = document.createElement('small');
      fraction.textContent = label(`${paper.fraction} share`, `${paper.fraction} 份额`);
      points.append(fraction);
      item.append(left, points);
      fragment.append(item);
    }
    if (!matches.length) {
      const empty = document.createElement('p');
      empty.className = 'paper-empty';
      empty.textContent = label('No contributing papers match your search.', '没有符合搜索条件的计分论文。');
      fragment.append(empty);
    }
    paperList.append(fragment);
    paperCount.textContent = label(`${matches.length} of ${selected.papers} papers`, `显示 ${matches.length} / ${selected.papers} 篇论文`);
  }

  function renderDialogHeading() {
    const item = selected;
    document.getElementById('dialog-rank').textContent = label(`Rank #${item.rank} · Paper contributions`, `第 ${item.rank} 名 · 计分论文`);
    document.getElementById('dialog-title').textContent = item.name;
    document.getElementById('dialog-summary').textContent = label(`${formatScore(item.score)} points from ${item.papers} papers · ${item.full} full-credit / ${item.fractional} fractional-credit`, `${item.papers} 篇论文共 ${formatScore(item.score)} 分 · ${item.full} 篇全额 / ${item.fractional} 篇分摊`);
  }

  function openPapers(item) {
    selected = item;
    renderDialogHeading();
    paperSearch.value = '';
    renderPapers();
    dialog.showModal();
  }

  function renderJournals() {
    const journalGrid = document.getElementById('journal-grid');
    journalGrid.replaceChildren();
    for (const journal of data.journals) {
      const card = document.createElement('div');
      card.className = 'journal-card';
      const name = document.createElement('span');
      name.textContent = language === 'zh' ? journalChinese[journal.name] || journal.name : journal.name;
      const weight = document.createElement('strong');
      weight.textContent = journal.impactFactor.toFixed(1);
      card.append(name, weight);
      journalGrid.append(card);
    }
  }

  function renderJournalFilter() {
    const current = journalFilter.value;
    journalFilter.replaceChildren();
    const all = document.createElement('option');
    all.value = '';
    all.textContent = label('All journals', '全部期刊');
    journalFilter.append(all);
    for (const journal of data.journals) {
      const option = document.createElement('option');
      option.value = journal.name;
      option.textContent = language === 'zh' ? journalChinese[journal.name] || journal.name : journal.name;
      journalFilter.append(option);
    }
    journalFilter.value = current;
  }

  function matchingAllPapers() {
    const term = normalize(allPaperSearch.value.trim());
    const journal = journalFilter.value;
    return paperData.included.filter(paper => {
      if (journal && paper.journal !== journal) return false;
      const searchable = `${paper.title} ${paper.authors} ${paper.doi} ${paper.journal} ${journalChinese[paper.journal] || ''}`;
      return normalize(searchable).includes(term);
    });
  }

  function renderAllPapers() {
    const matches = matchingAllPapers();
    const visible = matches.slice(0, visiblePaperCount);
    const fragment = document.createDocumentFragment();
    for (const paper of visible) {
      const card = document.createElement('article');
      card.className = 'all-paper-card';
      const topline = document.createElement('div');
      topline.className = 'record-topline';
      const journal = document.createElement('span');
      journal.textContent = language === 'zh' ? journalChinese[paper.journal] || paper.journal : paper.journal;
      const date = document.createElement('time');
      date.dateTime = paper.date;
      date.textContent = paper.date;
      topline.append(journal, date);
      const heading = document.createElement('h3');
      const link = document.createElement('a');
      link.href = paper.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = paper.title;
      heading.append(link);
      const authors = document.createElement('p');
      authors.textContent = `${label('Corresponding authors', '通讯作者')}: ${paper.authors}`;
      const reason = document.createElement('p');
      reason.className = 'record-reason';
      reason.textContent = paper.reason;
      reason.title = paper.reason;
      const doi = document.createElement('p');
      doi.className = 'doi';
      doi.textContent = `DOI: ${paper.doi}`;
      const source = document.createElement('p');
      const sourceTag = document.createElement('span');
      sourceTag.className = 'source-tag';
      sourceTag.textContent = paper.source === 'OpenAlex' ? 'OpenAlex' : label('Publisher / repository', '出版商／文献库');
      source.append(sourceTag);
      card.append(topline, heading, authors, reason, doi, source);
      fragment.append(card);
    }
    if (!matches.length) {
      const empty = document.createElement('p');
      empty.className = 'all-paper-empty';
      empty.textContent = label('No papers match your search.', '没有符合搜索条件的论文。');
      fragment.append(empty);
    }
    allPaperList.replaceChildren(fragment);
    allPaperCount.textContent = label(`Showing ${visible.length} of ${matches.length} papers`, `显示 ${visible.length} / ${matches.length} 篇论文`);
    loadMore.hidden = visible.length >= matches.length;
  }

  function setView(view) {
    activeView = view;
    const showPapers = view === 'papers';
    universityPanel.hidden = showPapers;
    papersPanel.hidden = !showPapers;
    universityTab.setAttribute('aria-selected', String(!showPapers));
    papersTab.setAttribute('aria-selected', String(showPapers));
    universityTab.tabIndex = showPapers ? -1 : 0;
    papersTab.tabIndex = showPapers ? 0 : -1;
  }

  search.addEventListener('input', renderRanking);
  paperSearch.addEventListener('input', renderPapers);
  allPaperSearch.addEventListener('input', () => { visiblePaperCount = 30; renderAllPapers(); });
  journalFilter.addEventListener('change', () => { visiblePaperCount = 30; renderAllPapers(); });
  loadMore.addEventListener('click', () => { visiblePaperCount += 30; renderAllPapers(); });
  universityTab.addEventListener('click', () => setView('universities'));
  papersTab.addEventListener('click', () => setView('papers'));
  for (const tab of [universityTab, papersTab]) {
    tab.addEventListener('keydown', event => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const next = activeView === 'papers' ? 'universities' : 'papers';
      setView(next);
      (next === 'papers' ? papersTab : universityTab).focus();
    });
  }
  document.querySelector('.site-header nav a[href="#papers"]').addEventListener('click', () => setView('papers'));
  document.querySelector('.site-header nav a[href="#ranking"]').addEventListener('click', () => setView('universities'));
  window.addEventListener('hashchange', () => {
    if (location.hash === '#papers') {
      setView('papers');
      document.querySelector('.result-tabs').scrollIntoView();
    }
  });
  languageToggle.addEventListener('click', () => applyLanguage(language === 'en' ? 'zh' : 'en'));
  document.getElementById('dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  let savedLanguage = 'en';
  try { if (localStorage.getItem('rankingLanguage') === 'zh') savedLanguage = 'zh'; } catch (_) { /* file:// privacy mode */ }
  const requestedLanguage = new URLSearchParams(window.location.search).get('lang');
  if (requestedLanguage === 'en' || requestedLanguage === 'zh') savedLanguage = requestedLanguage;
  applyLanguage(savedLanguage);
  if (location.hash === '#papers') {
    setView('papers');
    requestAnimationFrame(() => document.querySelector('.result-tabs').scrollIntoView());
  }
})();
