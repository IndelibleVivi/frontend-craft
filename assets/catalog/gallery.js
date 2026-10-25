/* The generated page is a read-only view. Only view state enters its URL/history. */
(function () {
  'use strict';
  var collection = document.getElementById('collection');
  var detail = document.getElementById('detail');
  var search = document.getElementById('search');
  var empty = document.getElementById('empty');
  var resultCount = document.getElementById('result-count');
  var cards = Array.from(document.querySelectorAll('.card'));
  var fields = ['task', 'language', 'medium', 'source'];
  var roleButtons = Array.from(document.querySelectorAll('[data-role]'));
  var templates = Array.from(document.querySelectorAll('template[data-item]'));
  var uiLanguage = 'en';
  var filterRole = '';
  var restoring = false;
  var scrollTimer;
  var compact = window.matchMedia('(max-width: 980px)');
  function usePosture() { document.getElementById('current-uses').open = !compact.matches; }
  compact.addEventListener('change', usePosture);
  usePosture();

  function say(en, zh) { return uiLanguage === 'zh-CN' ? zh : en; }
  function translate(root) {
    root.querySelectorAll('[data-en][data-zh]').forEach(function (el) {
      el.textContent = uiLanguage === 'zh-CN' ? el.dataset.zh : el.dataset.en;
    });
    root.querySelectorAll('[data-placeholder-en]').forEach(function (el) {
      el.placeholder = uiLanguage === 'zh-CN' ? el.dataset.placeholderZh : el.dataset.placeholderEn;
    });
    root.querySelectorAll('[data-label-en]').forEach(function (el) {
      el.setAttribute('aria-label', uiLanguage === 'zh-CN' ? el.dataset.labelZh : el.dataset.labelEn);
    });
    root.querySelectorAll('button.zoom').forEach(function (el) {
      el.textContent = el.getAttribute('aria-pressed') === 'true'
        ? say('Fit to view', '适应窗口') : say('View at original size', '查看原尺寸');
    });
  }
  function hasExact(value, wanted) {
    return !wanted || (value || '').split(',').includes(wanted);
  }
  function filters() {
    var values = {q: search.value.trim(), role: filterRole};
    fields.forEach(function (key) { values[key] = document.getElementById(key).value; });
    return values;
  }
  function apply() {
    var values = filters();
    var count = 0;
    cards.forEach(function (card) {
      var ok = (card.dataset.search || '').toLowerCase().includes(values.q.toLowerCase());
      ok = ok && hasExact(card.dataset.roles, values.role)
        && hasExact(card.dataset.tasks, values.task)
        && hasExact(card.dataset.languages, values.language)
        && hasExact(card.dataset.media, values.medium)
        && (!values.source || card.dataset.source === values.source);
      card.hidden = !ok;
      if (ok) count += 1;
    });
    empty.hidden = count !== 0;
    resultCount.textContent = say(count + ' of ' + cards.length + ' items', cards.length + ' 项中的 ' + count + ' 项');
    roleButtons.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.role === filterRole)); });
  }
  function route() {
    var url = new URL(location.href);
    var hash = url.hash.slice(1);
    // Existing generated links used a bare exact-identity token.
    var fragment = new URLSearchParams(hash.includes('=') ? hash : 'item=' + hash);
    return {url: url, item: fragment.get('item') || '', asset: fragment.get('asset'),
      preview: fragment.get('preview'), compare: fragment.get('compare') || ''};
  }
  function itemTemplate(id) { return templates.find(function (tpl) { return tpl.dataset.item === id; }); }
  function findFocus(key) {
    return Array.from(document.querySelectorAll('[data-focus-key]')).find(function (el) {
      return el.dataset.focusKey === key && el.getClientRects().length > 0;
    }) || document.getElementById(key);
  }
  function remember() {
    var active = document.activeElement;
    var state = Object.assign({}, history.state || {}, {fc: true, scroll: window.scrollY,
      focus: active && (active.dataset.focusKey || active.id) || ''});
    history.replaceState(state, '', location.href);
  }
  function visit(url) {
    remember();
    history.pushState({fc: true, depth: ((history.state || {}).depth || 0) + 1, scroll: 0}, '', url);
    render(false);
  }
  function collectionURL() {
    var url = new URL(location.href); url.hash = ''; return url;
  }
  function back() {
    remember();
    if ((history.state || {}).depth > 0) history.back();
    else { history.replaceState({fc: true, depth: 0, scroll: 0}, '', collectionURL()); render(false); }
  }
  function saveFilters() {
    var url = new URL(location.href);
    Object.entries(filters()).forEach(function (entry) {
      if (entry[1]) url.searchParams.set(entry[0], entry[1]); else url.searchParams.delete(entry[0]);
    });
    history.replaceState(history.state, '', url); apply();
  }
  function pauseMedia() {
    detail.querySelectorAll('video,audio').forEach(function (media) { media.pause(); });
  }
  function heading(text, tag) { var el = document.createElement(tag || 'h2'); el.textContent = text; return el; }
  function localized(el, en, zh) {
    el.dataset.en = en; el.dataset.zh = zh; el.textContent = say(en, zh); return el;
  }
  function comparePane(tpl) {
    var pane = document.createElement('section'); pane.className = 'compare-pane';
    pane.appendChild(heading(tpl.dataset.title));
    var meta = document.createElement('p'); meta.className = 'evidence';
    meta.textContent = tpl.dataset.identity; pane.appendChild(meta);
    var content = tpl.content.cloneNode(true);
    var media = content.querySelector('.media-stack');
    if (media) pane.appendChild(media);
    var link = localized(document.createElement('a'), 'Open full record', '打开完整记录');
    link.href = '#item=' + encodeURIComponent(tpl.dataset.item);
    link.dataset.itemLink = ''; pane.appendChild(link);
    return pane;
  }
  function buildDetail(current) {
    var tpl = itemTemplate(current.item);
    var bar = document.createElement('nav'); bar.className = 'detail-bar';
    bar.dataset.labelEn = 'Record navigation'; bar.dataset.labelZh = '记录导航';
    bar.setAttribute('aria-label', say('Record navigation', '记录导航'));
    var backButton = document.createElement('button'); backButton.type = 'button';
    backButton.id = 'detail-back'; localized(backButton, '← Back', '← 返回');
    backButton.addEventListener('click', back); bar.appendChild(backButton);
    var listLink = document.createElement('a'); listLink.href = collectionURL();
    listLink.dataset.collectionLink = ''; localized(listLink, 'Collection', '返回集合'); bar.appendChild(listLink);
    detail.appendChild(bar);
    if (!tpl) {
      var notice = document.createElement('section'); notice.className = 'notice';
      notice.appendChild(localized(heading(''), 'This revision is not in this gallery', '此画廊不包含这个版本'));
      notice.appendChild(localized(heading('', 'p'), 'Regenerate with the referenced collection, or return to the available records.',
        '请带上被引用的集合重新生成，或返回查看可用记录。'));
      detail.appendChild(notice); return;
    }
    var label = document.createElement('label');
    label.appendChild(localized(heading('', 'span'), 'Compare with', '并排查看'));
    var select = document.createElement('select'); select.id = 'compare';
    var none = localized(document.createElement('option'), 'Single record', '单项记录'); none.value = ''; select.appendChild(none);
    templates.forEach(function (other) {
      if (other.dataset.item === current.item) return;
      var option = document.createElement('option'); option.value = other.dataset.item;
      option.textContent = other.dataset.title + ' · ' + other.dataset.identity; select.appendChild(option);
    });
    select.value = current.compare;
    select.addEventListener('change', function () {
      var url = new URL(location.href);
      var fragment = new URLSearchParams(url.hash.slice(1));
      if (select.value) fragment.set('compare', select.value); else fragment.delete('compare');
      url.hash = fragment.toString();
      visit(url);
    });
    label.appendChild(select); bar.appendChild(label);
    var other = current.compare && itemTemplate(current.compare);
    if (other && other !== tpl) {
      var grid = document.createElement('div'); grid.className = 'compare-grid';
      grid.appendChild(comparePane(tpl)); grid.appendChild(comparePane(other)); detail.appendChild(grid);
    } else {
      if (current.compare) {
        var gap = localized(heading('', 'p'), 'The comparison revision is unavailable in this gallery.', '此画廊不包含要并排查看的版本。');
        gap.className = 'notice'; detail.appendChild(gap);
      }
      detail.appendChild(tpl.content.cloneNode(true));
    }
    detail.querySelectorAll('[data-color]').forEach(function (dot) { dot.style.backgroundColor = dot.dataset.color; });
  }
  function render(restore) {
    clearTimeout(scrollTimer);
    var current = route();
    uiLanguage = current.url.searchParams.get('ui') === 'zh-CN' ? 'zh-CN' : 'en';
    document.documentElement.lang = uiLanguage;
    search.value = current.url.searchParams.get('q') || '';
    filterRole = current.url.searchParams.get('role') || '';
    fields.forEach(function (key) {
      var el = document.getElementById(key); el.value = current.url.searchParams.get(key) || '';
    });
    if (fields.some(function (key) { return document.getElementById(key).value; })) {
      document.getElementById('filters').hidden = false;
      document.getElementById('filter-toggle').setAttribute('aria-expanded', 'true');
    }
    pauseMedia(); detail.replaceChildren();
    collection.hidden = !!current.item; detail.hidden = !current.item;
    if (current.item) buildDetail(current);
    translate(document); apply();
    document.getElementById('ui-language').textContent = uiLanguage === 'zh-CN' ? 'English' : '中文';
    var state = history.state || {};
    if (restore && state.scroll !== undefined) {
      restoring = true;
      requestAnimationFrame(function () {
        window.scrollTo(0, state.scroll);
        var target = state.focus && findFocus(state.focus);
        if (target) target.focus({preventScroll: true});
        restoring = false;
      });
    } else if (current.item) {
      var selector = current.asset ? 'asset:' + current.asset : current.preview ? 'preview:' + current.preview : '';
      var focusTarget = selector && Array.from(detail.querySelectorAll('[data-selector]')).find(function (el) { return el.dataset.selector === selector; });
      if (focusTarget) { focusTarget.setAttribute('tabindex', '-1'); focusTarget.focus(); focusTarget.scrollIntoView({block: 'center'}); }
      else { document.getElementById('detail-back').focus({preventScroll: true}); window.scrollTo(0, 0); }
    } else { window.scrollTo(0, 0); }
  }
  [search].concat(fields.map(function (key) { return document.getElementById(key); })).forEach(function (el) {
    el.addEventListener('input', saveFilters); el.addEventListener('change', saveFilters);
  });
  roleButtons.forEach(function (button) {
    button.addEventListener('click', function () { filterRole = button.dataset.role; saveFilters(); });
  });
  document.getElementById('filter-toggle').addEventListener('click', function (ev) {
    var panel = document.getElementById('filters'); panel.hidden = !panel.hidden;
    ev.currentTarget.setAttribute('aria-expanded', String(!panel.hidden));
  });
  document.getElementById('clear-filters').addEventListener('click', function () {
    search.value = ''; filterRole = ''; fields.forEach(function (key) { document.getElementById(key).value = ''; }); saveFilters();
  });
  document.getElementById('ui-language').addEventListener('click', function () {
    var url = new URL(location.href);
    uiLanguage = uiLanguage === 'en' ? 'zh-CN' : 'en';
    if (uiLanguage === 'zh-CN') url.searchParams.set('ui', 'zh-CN'); else url.searchParams.delete('ui');
    history.replaceState(history.state, '', url);
    document.documentElement.lang = uiLanguage;
    translate(document); apply();
    document.getElementById('ui-language').textContent = uiLanguage === 'zh-CN' ? 'English' : '中文';
  });
  document.querySelector('.skip').addEventListener('click', function (ev) {
    ev.preventDefault(); var main = document.getElementById('main'); main.tabIndex = -1; main.focus();
  });
  document.addEventListener('click', function (ev) {
    var zoom = ev.target.closest('button.zoom');
    if (zoom) {
      var viewport = zoom.closest('figure').querySelector('.preview-viewport');
      var original = viewport.classList.toggle('original');
      zoom.setAttribute('aria-pressed', String(original));
      zoom.textContent = original ? say('Fit to view', '适应窗口') : say('View at original size', '查看原尺寸');
      return;
    }
    var link = ev.target.closest('a[data-item-link], a.open, a[data-collection-link]');
    if (!link || ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey || ev.button !== 0) return;
    ev.preventDefault(); var url = new URL(link.href, location.href);
    visit(url);
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && !detail.hidden && !ev.defaultPrevented) { ev.preventDefault(); back(); }
  });
  window.addEventListener('popstate', function () { render(true); });
  window.addEventListener('pagehide', remember);
  window.addEventListener('scroll', function () {
    if (!restoring) {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(function () {
        history.replaceState(Object.assign({}, history.state || {}, {scroll: window.scrollY}), '', location.href);
      }, 150);
    }
  }, {passive: true});
  history.scrollRestoration = 'manual';
  if (!history.state || !history.state.fc) history.replaceState({fc: true, depth: 0}, '', location.href);
  render(true);
})();
