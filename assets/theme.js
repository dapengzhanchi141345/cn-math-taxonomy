/* theme.js — 手动主题切换（light / dark / system 三态，记忆在 localStorage）
   与自动深色（@media prefers-color-scheme）并存：system=不写 data-theme（跟随系统），
   light/dark=写 html[data-theme]，由 site.css 追加层的对应变量块接管。 */
(function () {
  'use strict';
  var KEY = 'cnm-theme';
  var root = document.documentElement;

  var sunSVG = '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.4"/><path d="M12 2.5v2.6M12 18.9v2.6M4.6 4.6l1.9 1.9M17.5 17.5l1.9 1.9M2.5 12h2.6M18.9 12h2.6M4.6 19.4l1.9-1.9M17.5 6.5l1.9-1.9"/></svg>';
  var moonSVG = '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.6 14.2A8.6 8.6 0 0 1 9.8 3.4a8.6 8.6 0 1 0 10.8 10.8Z"/></svg>';

  function current() {
    try { return localStorage.getItem(KEY) || 'system'; } catch (e) { return 'system'; }
  }
  function isDark() {
    var t = current();
    if (t === 'dark') return true;
    if (t === 'light') return false;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function apply(t) {
    if (t === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', t);
    }
  }
  function labelOf() {
    var t = current();
    return isDark() ? '当前深色 · 点按切浅色' : '当前浅色 · 点按切深色';
  }

  function mount() {
    var header = document.querySelector('.site-header') || document.body;
    var nav = document.querySelector('.site-nav');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-toggle';
    btn.setAttribute('aria-label', '切换浅色 / 深色主题');
    btn.title = labelOf();
    btn.innerHTML = sunSVG + moonSVG;
    if (nav) { nav.appendChild(btn); } else { header.appendChild(btn); }

    btn.addEventListener('click', function () {
      var next = isDark() ? 'light' : 'dark';  // 直接切到"当前显示"的对面, 可预期
      try { localStorage.setItem(KEY, next); } catch (e) { /* 隐私模式 */ }
      apply(next);
      btn.title = labelOf();
    });

    // 系统主题变化时，system 态自动跟随
    if (window.matchMedia) {
      var mq = window.matchMedia('(prefers-color-scheme: dark)');
      var onChange = function () { if (current() === 'system') apply('system'); };
      if (mq.addEventListener) mq.addEventListener('change', onChange); else if (mq.addListener) mq.addListener(onChange);
    }

    apply(current());
  }

  // 滚动投影
  function scrollShadow() {
    var h = document.querySelector('.site-header');
    if (!h) return;
    var f = function () { h.classList.toggle('scrolled', window.scrollY > 8); };
    f();
    window.addEventListener('scroll', f, { passive: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { mount(); scrollShadow(); });
  else { mount(); scrollShadow(); }
})();
