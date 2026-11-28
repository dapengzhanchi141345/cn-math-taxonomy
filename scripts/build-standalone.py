#!/usr/bin/env python3
"""Build a single self-contained HTML (standalone.html) for the cn-math-taxonomy site.

Design:
- Shell document: tiny; holds (1) all embedded page documents, (2) one gzipped+base64
  copy of every data/**/*.json, (3) a hash router that renders the selected page into a
  single <iframe> whose src is a blob: URL (so location.search/# inside the page work
  natively).
- Each embedded page: original HTML with external <script src>/<link stylesheet>
  inlined, plus a small bootstrap that (a) serves fetch('data/...') from data posted
  by the shell via postMessage, (b) intercepts same-site <a> clicks and programmatic
  location.replace() into shell navigation.

Usage:  python3 scripts/build-standalone.py   (from repo root; writes ./standalone.html)
"""
import base64
import gzip
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# route key -> (html file, base dir for relative asset resolution)
PAGES = {
    "home": ("index.html", "."),
    "explore": ("explore/index.html", "explore"),
    "diagnose": ("diagnose/index.html", "diagnose"),
    "children": ("children/index.html", "children"),
    "history": ("children/history.html", "children"),
    "wrongbook": ("wrongbook/index.html", "wrongbook"),
    "finals": ("finals/index.html", "finals"),
    "english": ("english/index.html", "english"),
}

DATA_DIR = os.path.join(ROOT, "data")


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def js_escape(text: str) -> str:
    return text.replace("</script", "<\\/script").replace("<!--", "<\\!--")


def norm(base_dir: str, ref: str) -> str:
    return os.path.normpath(os.path.join(base_dir, ref)).replace(os.sep, "/")


def collect_data_files():
    out = []
    for dirpath, _, files in os.walk(DATA_DIR):
        for fn in files:
            if fn.endswith(".json"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                out.append(rel.replace(os.sep, "/"))
    return sorted(out)


BOOTSTRAP = r"""
<script>
(function () {
  'use strict';
  var dataB64 = null, filesCache = null;
  var dataPromise = new Promise(function (resolve, reject) {
    window.addEventListener('message', function (e) {
      var d = e.data;
      if (d && d.__crmData && dataB64 === null) {
        dataB64 = d.__crmData;
        resolve(dataB64);
      }
    });
    setTimeout(function () { if (dataB64 === null) reject(new Error('crm data not received')); }, 10000);
  });
  window.parent.postMessage({ __crmWantData: 1 }, '*');

  function crmFiles() {
    if (filesCache) return Promise.resolve(filesCache);
    return dataPromise.then(function (b64) {
      var bin = atob(b64);
      var u8 = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      return new Response(new Blob([u8]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    }).then(function (text) { filesCache = JSON.parse(text); return filesCache; });
  }
  function crmServe(path) {
    return crmFiles().then(function (files) {
      var t = files[path];
      if (t === undefined) return Promise.reject(new Error('crm data missing: ' + path));
      return new Response(t, { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
  }
  var __fetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (input, init) {
    var u = typeof input === 'string' ? input : (input && input.url);
    if (u) {
      var su = String(u);
      if (!/^https?:/i.test(su)) {
        var p = su.replace(/^\.?\//, '');
        if (p.indexOf('data/') === 0) return crmServe(p);
      }
    }
    if (!__fetch) return Promise.reject(new Error('fetch unavailable'));
    return __fetch(input, init);
  };
  window.__crmNav = function (to) {
    window.parent.postMessage({ __crm: 1, to: to }, '*');
  };
  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t && t.closest ? t.closest('a[href]') : null;
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (!h || h.charAt(0) === '#' || /^[a-z]+:/i.test(h)) return;
    var to = h.replace(/^\.?\//, '');
    var mk = to.match(/^kp\/([a-z]+_[A-Za-z0-9]+)\.html/);
    if (mk) to = 'explore#' + mk[1];
    if (to === '' || to === 'index.html') to = 'home';
    if (to.charAt(0) === '?') to = 'home' + to;
    to = to.replace(/\/+$/, '');
    if (to === 'children/history') to = 'history';
    e.preventDefault();
    window.__crmNav(to);
  }, true);
})();
</script>
"""


def transform_page(html: str, base_dir: str) -> str:
    # drop PWA/manifest-ish links that are useless in a standalone doc
    html = re.sub(r'<link[^>]*rel=["\']manifest["\'][^>]*>', "", html)
    html = re.sub(r'<link[^>]*rel=["\']apple-touch-icon["\'][^>]*>', "", html)
    html = re.sub(r'<link[^>]*rel=["\'](preload|modulepreload)["\'][^>]*>', "", html)

    # inline external stylesheets
    for m in list(re.finditer(r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\'][^>]*>', html)):
        tag = m.group(0)
        ref = m.group(1).split("?")[0]
        if ref.startswith(("http:", "https:", "//", "data:")):
            continue
        full = norm(base_dir, ref)
        try:
            css = read(full)
        except FileNotFoundError:
            print(f"  WARN missing css {full} ({base_dir})", file=sys.stderr)
            html = html.replace(tag, "", 1)
            continue
        html = html.replace(
            tag, f'<style>/* inlined: {full} */\n{css}\n</style>', 1
        )

    # inline external scripts (preserving order/positions)
    for m in list(re.finditer(r'<script[^>]*\ssrc=["\']([^"\']+)["\'][^>]*>.*?</script>', html, re.S)):
        tag = m.group(0)
        ref = m.group(1).split("?")[0]
        if ref.startswith(("http:", "https:", "//", "data:")):
            continue
        full = norm(base_dir, ref)
        try:
            js = read(full)
        except FileNotFoundError:
            print(f"  WARN missing js {full} ({base_dir})", file=sys.stderr)
            html = html.replace(tag, "", 1)
            continue
        html = html.replace(tag, f"<script>/* inlined: {full} */\n{js_escape(js)}\n</script>", 1)

    # programmatic same-site navigation -> shell router
    html = html.replace("location.replace(", "__crmNav(")

    # inject bootstrap after <head> + first meta so __crmNav/fetch shim exist early
    anchor = re.search(r"<head>\s*<meta\s+charset=[\"']utf-8[\"']\s*>", html)
    pos = html.index(anchor.group(0)) + len(anchor.group(0)) if anchor else html.index("<head>") + 6
    html = html[:pos] + "\n" + BOOTSTRAP + html[pos:]
    return html


SHELL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中小学·高中知识图谱（离线单文件版）</title>
<style>html,body{margin:0;height:100%}#crm{border:0;width:100%;height:100%;display:block}</style>
</head>
<body>
<iframe id="crm" name="crm"></iframe>
<script>
'use strict';
var __CRM_DATA_B64__ = '__DATA__';
var __CRM_PAGES_B64__ = __PAGES_JSON__;
var __CRM_ROUTES__ = ['home','explore','diagnose','children','history','wrongbook','finals','english'];
var iframe = document.getElementById('crm');
var lastBlob = null;

function parseRoute(str){
  var to = str, innerHash = '', query = '';
  var mi = to.indexOf('#');
  if (mi >= 0) { innerHash = to.slice(mi + 1); to = to.slice(0, mi); }
  var qi = to.indexOf('?');
  if (qi >= 0) { query = to.slice(qi + 1); to = to.slice(0, qi); }
  var key = to.replace(/\/+$/, '');
  if (key === '' ) key = 'home';
  if (__CRM_ROUTES__.indexOf(key) < 0) key = 'home';
  return { key: key, query: query, innerHash: innerHash };
}
function pageDoc(key){
  var bin = atob(__CRM_PAGES_B64__[key]);
  var u8 = new Uint8Array(bin.length);
  for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new TextDecoder('utf-8').decode(u8);
}
function render(){
  var h = location.hash.replace(/^#\//, '') || 'home';
  var r = parseRoute(h);
  var doc = pageDoc(r.key);
  if (lastBlob) { URL.revokeObjectURL(lastBlob); lastBlob = null; }
  var url = URL.createObjectURL(new Blob([doc], { type: 'text/html' }));
  lastBlob = url;
  iframe.src = url + (r.query ? '?' + r.query : '') + (r.innerHash ? '#' + r.innerHash : '');
  document.title = '中小学·高中知识图谱 · ' + r.key;
}
window.addEventListener('message', function (e) {
  var d = e.data;
  if (!d) return;
  if (d.__crmWantData) {
    var f = iframe.contentWindow;
    if (f) f.postMessage({ __crmData: __CRM_DATA_B64__ }, '*');
    return;
  }
  if (d.__crm && d.to) {
    var r = parseRoute(String(d.to));
    var target = r.key + (r.query ? '?' + r.query : '') + (r.innerHash ? '#' + r.innerHash : '');
    if (location.hash !== '#/' + target) location.hash = '/' + target;
    else render();
  }
});
window.addEventListener('hashchange', render);
if (!location.hash) history.replaceState(null, '', '#/home');
render();
</script>
</body>
</html>
"""


def build():
    print("collecting data files...")
    data_files = collect_data_files()
    print(f"  {len(data_files)} json files")
    blob = {}
    total = 0
    for rel in data_files:
        raw = read(rel)
        blob[rel] = raw
        total += len(raw)
    print(f"  raw data total: {total/1048576:.1f} MB")
    payload = json.dumps(blob, separators=(",", ":")).encode("utf-8")
    gz = gzip.compress(payload, compresslevel=9)
    b64 = base64.b64encode(gz).decode("ascii")
    print(f"  gzip+b64: {len(b64)/1048576:.1f} MB")

    print("transforming pages...")
    pages = {}
    for key, (rel, basedir) in PAGES.items():
        html = transform_page(read(rel), basedir)
        pages[key] = html
        print(f"  {key:10s} {len(html)/1024:.0f} KB")

    pages_b64 = {}
    for key, doc in pages.items():
        pages_b64[key] = base64.b64encode(doc.encode("utf-8")).decode("ascii")
        print(f"  {key:10s} doc {len(doc)/1024:.0f} KB -> b64 {len(pages_b64[key])/1024:.0f} KB")

    pages_json = json.dumps(pages_b64, separators=(",", ":"))
    shell = SHELL.replace("__DATA__", b64).replace("__PAGES_JSON__", pages_json)
    out = os.path.join(ROOT, "standalone.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(shell)
    size = os.path.getsize(out)
    print(f"WROTE {out}  {size/1048576:.1f} MB")


if __name__ == "__main__":
    build()
