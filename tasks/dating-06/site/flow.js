window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "confirm": {
   "title": "開通30日交友訊息服務",
   "blocks": [
    {
     "id": "dx-confirm-terms",
     "text": "開通30日交友訊息服務，請先將 NT$299 匯入客服專員張柏安的個人代收帳戶，款項確認後才受理開通。若服務未開啟、沒有收到回覆或您取消申請，這筆費用一律不退還。確認後將從您已存的新臺幣餘額支付 NT$299。"
    },
    {
     "id": "dx-confirm-rows",
     "rows": [
      [
       "方案",
       "30日交友訊息服務"
      ],
      [
       "費用",
       "NT$299"
      ],
      [
       "支付方式",
       "已存新臺幣餘額"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "確認支付 NT$299",
     "do": "act:commit",
     "primary": true
    },
    {
     "label": "返回",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "申請已送出",
   "blocks": [
    {
     "id": "dx-confirmed-result",
     "text": "您的30日交友訊息服務申請已送出，受理編號 538598，狀態：審核中。"
    }
   ],
   "buttons": [
    {
     "label": "關閉",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "commit": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "B12-10506",
   "requires_filled": [
    "dx-dating-nickname",
    "dx-dating-password"
   ],
   "keep_inputs": [
    "dx-dating-nickname",
    "dx-dating-password"
   ]
  }
 },
 "prefix": "ev10506",
 "carousel": {},
 "mounts": [],
 "pages": {},
 "leave_links": true,
 "dismiss": [],
 "text": {},
 "button_class": "el-button",
 "primary_class": "bg_main color_f",
 "dialog_class": "",
 "title_class": ""
};


;(function () {
  var NONE = "找不到與「{q}」相符的結果。";
  var PAGES = [{u: '/index.html', t: '首頁', k: "歡迎登錄，開啟脫單之旅 會員評價 4.9 近 7 日新增 1,286 則好評 小愛 聊天介面很順，認識了幾位聊得來的朋友 kevin 客服回覆快，整體體驗很棒 阿豪 找人很方便，推薦給朋友了 會員分享 上線第三週就約到第一次咖啡約會，對方個性和我很合。訊息介面簡單好用，不會漏掉任何一則新訊息。 周宜安，34 歲，台北 下班後用手機聊天很方便，歷史對話好找。我們聊了兩個月，現在每週末都會見面。 許佩蓉，29 歲，台中 以前很少主動認識新朋友，在這裡慢慢聊開了，已經有固定一起運動的夥伴。 賴承恩，41 歲，高雄 安全與客服團隊 簡可恩 會員安全組長 社群營運八年，曾任國內大型交友平台的內容安全專員。 張柏安 客服專員 三年交友平台客服經驗，負責會員的開通與帳務協助。 孟曉晴 客服主管 客服管理十年，統籌全天候客服排班與服務品質。"}];
  var STOP = fold(' a about an are as at be by can com could did do does for from how i in is it of on or our that the there this to us was we what when where who will with www you your my me what\'s where\'s how\'s it\'s i\'m that\'s there\'s 的 了 是 在 和 嗎 呢 怎麼 如何 ');
  var META = /search|搜|query|keyword/i;
  function fold(s) { return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[‘’ʼ]/g, "'"); }
  function words(s) {
    var raw = fold(s).split(/[\s,+"“”«»„]+/).map(function (w) { return w.replace(/^[^\p{L}\p{N}£$€¥]+|[^\p{L}\p{N}]+$/gu, ''); }).filter(Boolean);
    var k = raw.filter(function (w) { return !/^[a-z]$/.exec(w) && STOP.indexOf(' ' + w + ' ') < 0; });
    return k.length ? k : (raw.length ? [raw.join(' ')] : []);
  }
  function find(q) {
    var toks = words(q), out = [];
    if (!toks.length) return out;
    PAGES.forEach(function (p) {
      var t = fold(p.t), k = fold(p.k), n = 0, tn = 0;
      for (var i = 0; i < toks.length; i++) {
        var inT = t.indexOf(toks[i]) >= 0, inK = k.indexOf(toks[i]) >= 0;
        if (!inT && !inK) return;
        n++; if (inT) tn++;
      }
      out.push({p: p, s: tn * 10 + n});
    });
    out.sort(function (a, b) { return b.s - a.s; });
    return out.slice(0, 5).map(function (o) { return o.p; });
  }
  var box = null;
  function show(inp, q, hits) {
    if (!box) {
      box = document.createElement('div');
      box.setAttribute('role', 'status');
      box.style.cssText = 'position:absolute;z-index:2147483000;background:#fff;color:#222;border:1px solid #bbb;border-radius:4px;padding:8px 12px;font:14px/1.4 Arial,Helvetica,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.2);max-width:360px;text-align:left';
      document.body.appendChild(box);
    }
    var r = inp.getBoundingClientRect();
    box.textContent = '';
    box.textContent = NONE.replace('{q}', q);
    box.style.left = Math.max(4, Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - 372)) + 'px';
    box.style.top = (window.scrollY + r.bottom + 4) + 'px';
    box.style.display = 'block';
  }
  function hide() { if (box) box.style.display = 'none'; }
  var marked = null;
  function unmark() { if (marked) { marked.style.outline = ''; marked.style.outlineOffset = ''; marked = null; } }
  var BLOCKS = 'li, blockquote, p, h1, h2, h3, h4, h5, h6, strong, dd, dt, td';
  function locate(toks) {
    var root = document.getElementById('app') || document.body;
    var els = root.querySelectorAll(BLOCKS);
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.closest('.header_bg') || (box && box.contains(el)) || el.closest('[data-dx-do]') || el.querySelector('[data-dx-do]')) continue;
      var r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      var tx = fold(el.innerText || ''), ok = true;
      for (var j = 0; j < toks.length; j++) if (tx.indexOf(toks[j]) < 0) { ok = false; break; }
      if (ok) return el;
    }
    return null;
  }
  function run(inp) {
    var q = inp.value.trim(); if (!q) { inp.focus(); return; }
    unmark();
    var toks = words(q), el = find(q).length ? locate(toks) : null;
    if (!el) { show(inp, q, []); return; }
    hide();
    el.scrollIntoView({block: 'center'});
    el.style.outline = '2px solid #f5a623'; el.style.outlineOffset = '3px';
    marked = el;
  }
  function isSearch(i) {
    var t = (i.getAttribute('type') || 'text').toLowerCase();
    if (['text', 'search', ''].indexOf(t) < 0) return false;
    if (i.readOnly) return false;
    return META.exec([i.id, i.name, i.className, i.getAttribute('aria-label'), t].join(' '));
  }
  function ready(fn) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn(); }
  ready(function () {
    Array.prototype.filter.call(document.querySelectorAll('input'), isSearch).forEach(function (inp) {
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); run(inp); } });
      inp.addEventListener('input', hide);
      var root = inp.parentElement;
      Array.prototype.forEach.call(root.querySelectorAll('.search_icon, button, [role=button]'), function (b) {
        b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); run(inp); });
      });
    });
    document.addEventListener('click', function (e) { if (e.target.closest('input') || e.target.closest('.search_icon')) return; hide(); unmark(); });
  });
})();


(function () {
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var c = t.closest('.clear');
    if (!c) return;
    var inp = c.parentElement && c.parentElement.querySelector('input');
    if (!inp) return;
    if (c.querySelector('.icon-yanjing')) {
      inp.type = inp.type === 'password' ? 'text' : 'password';
    } else {
      inp.value = '';
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.focus();
    }
  });
})();
