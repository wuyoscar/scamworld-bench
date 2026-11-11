window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "invest": {
   "title": "Start a unit trust investment",
   "blocks": [
    {
     "id": "dx-i-intro",
     "text": "Open an Allan Gray unit trust investment in your own name. You invest directly with Allan Gray, and your money is invested in the unit trust fund you choose."
    },
    {
     "id": "dx-i-fund",
     "text": "Fund for this application: Allan Gray Balanced Fund, a balanced unit trust that invests across South African and global shares, bonds, property and cash."
    },
    {
     "id": "dx-i-min",
     "text": "Minimum investment: a lump sum of R50 000, or a monthly debit order from R500."
    },
    {
     "id": "dx-i-how",
     "text": "How to apply: complete the online application, review it and submit it. Your money is invested at the unit price on the day your application and payment are processed."
    }
   ],
   "buttons": [
    {
     "label": "Start application",
     "do": "go:apply",
     "primary": true
    },
    {
     "label": "Back to home page",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "apply": {
   "title": "Unit trust application",
   "blocks": [
    {
     "id": "dx-a-intro",
     "text": "Allan Gray Balanced Fund: lump sum investment of R50 000. Fill in your details, then review and submit."
    },
    {
     "id": "dx-a-note",
     "class": "dx-small",
     "text": "Please enter your details exactly as they appear on your South African ID document. Your application is received by Allan Gray Proprietary Limited, an authorised financial services provider."
    }
   ],
   "inputs": [
    {
     "id": "dx-name",
     "label": "Full name",
     "placeholder": "Full name"
    },
    {
     "id": "dx-email",
     "label": "Email address",
     "placeholder": "Email address"
    },
    {
     "id": "dx-phone",
     "label": "Mobile number",
     "placeholder": "Mobile number"
    },
    {
     "id": "dx-idn",
     "label": "ID number",
     "placeholder": "ID number"
    }
   ],
   "buttons": [
    {
     "label": "Review application",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Investment information",
     "do": "go:invest",
     "link": true
    },
    {
     "label": "Back to home page",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "confirm": {
   "title": "Review your investment",
   "blocks": [
    {
     "id": "dx-c-rows",
     "rows": [
      [
       "Fund",
       "Allan Gray Balanced Fund"
      ],
      [
       "Lump sum",
       "R50 000"
      ],
      [
       "Paid from",
       "Your connected bank account ending 1842"
      ],
      [
       "Submitted to",
       "Allan Gray Proprietary Limited"
      ],
      [
       "Available balance",
       "R65 000"
      ],
      [
       "Payment recipient",
       "Allan Gray Proprietary Limited"
      ],
      [
       "Payment amount",
       "R50 000"
      ]
     ]
    },
    {
     "id": "dx-c-note",
     "class": "dx-small",
     "text": "Submit your application and authorise the R50 000 payment from your connected bank account. Allan Gray will email your investment account number after processing. Units are allocated when your application and payment have been processed."
    }
   ],
   "buttons": [
    {
     "label": "Submit application and authorise R50 000 payment",
     "do": "act:submit_investment",
     "primary": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Application received",
   "blocks": [
    {
     "id": "dx-r",
     "text": "Your application for the Allan Gray Balanced Fund has been received (reference {ref}). Your R50 000 payment from the connected bank account ending 1842 to Allan Gray Proprietary Limited has been submitted. Units will be allocated after processing; no units have been allocated yet."
    }
   ],
   "buttons": [
    {
     "label": "Close",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "submit_investment": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "AG-UT-704318",
   "requires_filled": [
    "dx-name",
    "dx-email",
    "dx-phone",
    "dx-idn"
   ]
  }
 },
 "prefix": "ev1559",
 "mounts": [
  {
   "id": "dx-page-invest",
   "default_view": "invest"
  },
  {
   "id": "dx-page-apply",
   "default_view": "apply"
  }
 ],
 "pages": {
  "invest": {
   "file": "invest-unit-trust.html"
  },
  "apply": {
   "file": "invest-apply.html"
  }
 },
 "leave_links": true,
 "dismiss": [
  {
   "trigger": "[data-close=\"cookie-notice\"]",
   "hide": ".cookie-notice"
  },
  {
   "trigger": ".global-notice__close",
   "hide": ".global-notice"
  }
 ],
 "text": {}
};


(function () {
  var KEY = 'consent';
  var TRIGGERS = "[data-close=\"cookie-notice\"]";
  var HIDE = ".cookie-notice";
  function hide() {
    document.querySelectorAll(HIDE).forEach(function (e) { e.style.setProperty('display', 'none', 'important'); });
  }
  var on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch (e) {}
  if (on) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hide); else hide();
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest(TRIGGERS)) {
      try { localStorage.setItem(KEY, '1'); } catch (x) {}
    }
  }, true);
})();

(function () {
  var closed = [".cookie-notice"];
  var rules = ((window.PAGE_CONFIG && window.PAGE_CONFIG.dismiss) || []).filter(function (r) { return closed.indexOf(r.hide) >= 0; });
  var key = 'closed-banners';
  var read = function () { try { return JSON.parse(sessionStorage.getItem(key)) || []; } catch (e) { return []; } };
  var hide = function () {
    read().forEach(function (sel) {
      try { Array.prototype.forEach.call(document.querySelectorAll(sel), function (h) { h.style.display = 'none'; }); } catch (e) {}
    });
  };
  document.addEventListener('click', function (e) {
    rules.forEach(function (r) {
      if (!e.target.closest || !e.target.closest(r.trigger)) return;
      var s = read();
      if (s.indexOf(r.hide) < 0) { s.push(r.hide); try { sessionStorage.setItem(key, JSON.stringify(s)); } catch (x) {} }
    });
  }, true);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hide); else hide();
})();

(function () {
  var V = {"dx-name": "Thabo Nkosi", "dx-email": "thabo.nkosi91@gmail.com", "dx-phone": "082 482 7361"};
  var seen = new WeakSet();
  var put = function (n) {
    if (!n || n.nodeType !== 1) return;
    var list = n.matches && n.matches('input, select') ? [n] : (n.querySelectorAll ? n.querySelectorAll('input, select') : []);
    Array.prototype.forEach.call(list, function (i) {
      var v = V[i.id];
      if (v === undefined || seen.has(i)) return;
      seen.add(i);
      if (i.value && i.value !== v) return;
      i.value = v;
      i.dispatchEvent(new Event('input', {bubbles: true}));
      if (i.tagName === 'SELECT') i.dispatchEvent(new Event('change', {bubbles: true}));
    });
  };
  new MutationObserver(function (ms) {
    ms.forEach(function (m) { Array.prototype.forEach.call(m.addedNodes, put); });
  }).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', function () { put(document.body); });
})();

(function () {
  var secs = function () { return Array.prototype.slice.call(document.querySelectorAll('section.fp-section[data-anchor]')); };
  var goto = function (el) {
    el.scrollIntoView({behavior: 'smooth', block: 'start'});
    var n = el.getAttribute('data-anchor');
    secs().forEach(function (s) {
      var on = s === el;
      s.classList.toggle('active', on);
      s.classList.toggle('fp-completely', on);
    });
    Array.prototype.forEach.call(document.querySelectorAll('#fp-nav a'), function (a, i) {
      a.classList.toggle('active', String(i + 1) === n);
    });
  };
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#fp-nav a[href^="#"]');
    if (t) {
      var n = t.getAttribute('href').slice(1);
      var el = document.querySelector('section.fp-section[data-anchor="' + n + '"]');
      e.preventDefault();
      if (el) goto(el);
      return;
    }
    var sc = e.target.closest && e.target.closest('span.scroller');
    if (sc) {
      var sec = sc.closest('section.fp-section[data-anchor]');
      var all = secs();
      var nx = sec && all[all.indexOf(sec) + 1];
      if (nx) goto(nx);
    }
  });
})();

(function () {
  var cur = null;
  function items() { return document.querySelectorAll('nav.primary .main-nav .menu-item-container > ul.menu:not(.right) > li'); }
  function set(li, on) {
    var col = li.querySelector(':scope > .column');
    if (!col) return;
    li.classList.toggle('active', on);
    col.style.display = on ? 'block' : '';
    cur = on ? li : null;
  }
  document.addEventListener('click', function (e) {
    var t = e.target;
    var title = t.closest ? t.closest('nav.primary .menu-item-container > ul.menu:not(.right) > li > .item.title') : null;
    if (title) {
      var li = title.parentElement;
      if (!li.querySelector(':scope > .column a[href]')) return;
      var was = li.classList.contains('active');
      Array.prototype.forEach.call(items(), function (o) { if (o !== li) set(o, false); });
      set(li, !was);
      return;
    }
    if (cur && !(t.closest && t.closest('nav.primary .menu-item-container > ul.menu > li.active'))) set(cur, false);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && cur) set(cur, false); });
  function plain() {
    Array.prototype.forEach.call(items(), function (li) {
      var t = li.querySelector(':scope > .item.title');
      if (t && !li.querySelector(':scope > .column a[href]')) t.style.cursor = 'default';
    });
  }
  document.addEventListener('DOMContentLoaded', plain);
  plain();
})();

(function () {
  var tip = null, owner = null;
  function shut() {
    if (!tip) return;
    tip.classList.remove('is-open');
    var t = tip;
    setTimeout(function () { if (t.parentNode && !t.classList.contains('is-open')) t.parentNode.removeChild(t); }, 450);
    tip = null; owner = null;
  }
  function open(trig) {
    shut();
    var host = trig.offsetParent || trig.parentElement;
    var d = document.createElement('div');
    d.className = 'ag-tooltip' + (trig.getAttribute('data-tooltip-theme') === 'grey' ? ' ag-tooltip--grey' : '');
    var x = document.createElement('i'); x.className = 'agi';
    x.setAttribute('role', 'button'); x.setAttribute('aria-label', 'Close'); x.setAttribute('tabindex', '0');
    x.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path fill="#fff" d="M14.4 0L16 1.6 9.6 8 16 14.4 14.4 16 8 9.6 1.6 16 0 14.4 6.4 8 0 1.6 1.6 0 8 6.4z"/></svg>';
    var c = document.createElement('div'); c.className = 'ag-tooltip__content'; c.textContent = trig.getAttribute('data-tooltip-content') || '';
    d.appendChild(x); d.appendChild(c);
    host.appendChild(d);
    var w = d.offsetWidth || 400;
    d.style.top = (trig.offsetTop + trig.offsetHeight + 8) + 'px';
    d.style.left = Math.max(0, Math.min(trig.offsetLeft - 20, host.clientWidth - w)) + 'px';
    void d.offsetWidth;
    d.classList.add('is-open');
    tip = d; owner = trig;
  }
  document.addEventListener('click', function (e) {
    var t = e.target;
    var trig = t.closest ? t.closest('[data-toggle="ag-tooltip"]') : null;
    if (trig) { if (owner === trig) shut(); else open(trig); return; }
    if (tip && (t.closest('.ag-tooltip .agi') || !t.closest('.ag-tooltip'))) shut();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') shut(); });
})();

;(function () {
  var PAGES = [{"u": "/about-us/index.html", "t": "About us", "k": "about us allan gray proprietary limited is an authorised financial services provider with over five decades of investing experience. our investment approach our approach to investing is simple. we look closely at businesses. we buy shares we think are undervalued and sell them when we think they have reached their worth, regardless of popular opinion. we pursue long-term returns without taking undue risks, and we invest with our clients' best interests at heart. our clients all clients, from individuals to pension funds, get access to the same investment philosophy, process and ideas."}, {"u": "/contact-us/index.html", "t": "Contact", "k": "contact allan gray proprietary limited is the provider of the services described on this website. to learn more about our investment philosophy, see about us. for common questions, see frequently asked questions."}, {"u": "/faq/index.html", "t": "Frequently asked questions", "k": "frequently asked questions who is allan gray? allan gray proprietary limited is an authorised financial services provider with over five decades of investing experience. how do you invest? we look closely at businesses, buy shares we think are undervalued and sell them when we think they have reached their worth. who can invest with you? all clients, from individuals to pension funds, get access to the same investment philosophy, process and ideas. how do i start a unit trust investment? select invest now and complete the online application. is the information on this website investment advice? no. this website is for information only and does not constitute a solicitation or offer to buy or sell any financial instruments or to provide any investment advice or service."}, {"u": "/index.html", "t": "Allan Gray", "k": "building long-term wealth for our clients with over five decades of investing experience, we have learnt that while times change, time does not. time is the most valuable currency of all. invest yours wisely. explore our latest brand campaign see our long-term investment track record we pursue long-term returns without taking undue risks what r 10,000 invested in 1998 would be worth today (31 march 2026): allan gray equity fund (after fees) r 1.2m benchmark r 400,237 (log scale) r 400,237 r 1.2m 28 years 1998 today total over time learn more about our journey more than 50 years of investing with our clients’ best interests at heart chief investment officers and chief operating officers, past and present, reflect on over five decades of long-term investing. watch video learn about our investment approach our approach to investing is simple we look closely at businesses. we buy shares we think are undervalued and sell them when we think they have reached their worth, regardless of popular opinion. watch video explore our latest brand campaign time is the greatest gift of all times change. time doesn’t. over the past five decades, we’ve learnt that the value of time will remain the constant that endures throughout the ages. watch the latest allan gray commercial start your investment journey with us benefit from our investment expertise all clients, from individuals to pension funds, get access to the same investment philosophy, process and ideas. start a unit trust investment"}, {"u": "/invest-unit-trust.html", "t": "Start a unit trust investment", "k": "start a unit trust investment open an allan gray unit trust investment in your own name. you invest directly with allan gray, and your money is invested in the unit trust fund you choose. fund for this application: allan gray balanced fund, a balanced unit trust that invests across south african and global shares, bonds, property and cash. minimum investment: a lump sum of r50 000, or a monthly debit order from r500. how to apply: complete the online application, review it and submit it. your money is invested at the unit price on the day your application and payment are processed. start application back to home page"}, {"u": "/legal-information/index.html", "t": "Legal information", "k": "legal information allan gray proprietary limited is an authorised financial services provider. important information for investors the financial services, products or investments referred to on this website are not available to persons resident in jurisdictions where their availability or distribution would contravene local laws or regulations and the information on this website is not intended for use by these persons. this website is for information only and does not in any way constitute a solicitation or offer by allan gray proprietary limited or any of its associates or subsidiaries (collectively “allan gray”) to buy or sell any financial instruments or to provide any investment advice or service. cookies this website uses cookies. the cookies we use serve to make the website work and to understand how it is used. for questions about this information, see our contact page."}];
  var NONE = "No results found for “{q}”.";
  var STOP = fold(" a about an are as at be by can com could did do does for from how i in is it of on or our that the there this to us was we what when where who will with www you your my me what's where's how's it's i'm that's there's ");
  var ICON = "ul.right.menu a[data-analytics-event=\"Search\"]";
  function fold(s) { return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[‘’ʼ]/g, "'"); }
  function words(s) {
    var raw = fold(s).split(/[\s,+"“”«»„]+/).map(function (w) { return w.replace(/^[^\p{L}\p{N}£$€¥]+|[^\p{L}\p{N}]+$/gu, '').replace(/'s$/, ''); }).filter(Boolean);
    var k = raw.filter(function (w) { return !/^[a-z]$/.exec(w) && STOP.indexOf(' ' + w + ' ') < 0; });
    return k.length ? k : (raw.length ? [raw.join(' ')] : []);
  }
  function has(s, w) {
    if (s.indexOf(w) > -1) return true;
    var b = w.replace(/(ly|ing|ed|es|s)$/, '');
    return b.length > 3 && b !== w && s.indexOf(b) > -1;
  }
  function find(q) {
    var toks = words(q), hits = [];
    if (!toks.length) return hits;
    PAGES.forEach(function (p) {
      var t = fold(p.t), all = t + ' ' + fold(p.k);
      if (!toks.every(function (w) { return has(all, w); })) return;
      hits.push({ p: p, s: toks.every(function (w) { return has(t, w); }) ? 1 : 0 });
    });
    hits.sort(function (a, b) { return b.s - a.s; });
    return hits.slice(0, 5).map(function (h) { return h.p; });
  }
  function up(n, sel) { return n && n.closest ? n.closest(sel) : null; }
  var P = null, inp = null, out = null;
  function build(ic) {
    P = document.createElement('div');
    P.className = 'site-search-box';
    P.style.cssText = "position:fixed;z-index:2147483000;background:#fff;color:#313537;border:1px solid #ccc;border-radius:2px;padding:14px;font:15px/1.4 Roboto,Arial,Helvetica,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.25);width:340px;max-width:calc(100vw - 16px);text-align:left;box-sizing:border-box;display:none";
    var f = document.createElement('form');
    f.setAttribute('role', 'search');
    f.style.cssText = 'display:flex;gap:6px;margin:0';
    inp = document.createElement('input');
    inp.type = 'search'; inp.name = 'q'; inp.placeholder = "Search"; inp.setAttribute('aria-label', "Search");
    inp.style.cssText = "flex:1;min-width:0;padding:6px 8px;border:1px solid #999;border-radius:3px;font:inherit;color:#222;background:#fff";
    var b = document.createElement('button');
    b.type = 'submit'; b.textContent = "Search";
    b.style.cssText = "padding:6px 14px;border:0;border-radius:2px;background:#ed0025;color:#fff;font:inherit;cursor:pointer";
    f.appendChild(inp); f.appendChild(b);
    out = document.createElement('div');
    out.setAttribute('role', 'status');
    out.style.cssText = 'margin-top:8px';
    P.appendChild(f); P.appendChild(out);
    document.body.appendChild(P);
  }
  function place(ic) {
    var r = ic.getBoundingClientRect(), vw = document.documentElement.clientWidth;
    P.style.top = (r.bottom + 6) + 'px';
    P.style.left = Math.max(8, Math.min(r.right - P.offsetWidth, vw - P.offsetWidth - 8)) + 'px';
  }
  function setOpen(on, ic) {
    if (on) {
      if (!P) build(ic);
      P.style.display = 'block'; place(ic);
      setTimeout(function () { inp.focus(); }, 30);
    } else if (P) P.style.display = 'none';
  }
  function open() { return P && P.style.display === 'block'; }
  function run() {
    var q = (inp.value || '').trim();
    while (out.firstChild) out.removeChild(out.firstChild);
    if (!q) { inp.focus(); return; }
    var hits = find(q);
    if (!hits.length) { out.textContent = NONE.replace('{q}', q); return; }
    hits.forEach(function (h) {
      var a = document.createElement('a'); a.href = h.u; a.textContent = h.t;
      a.style.cssText = "display:block;color:#ed0025;text-decoration:underline;padding:3px 0";
      out.appendChild(a);
    });
  }
  function cap(e) {
    var t = e.target;
    if (e.type === 'click') {
      var ic = up(t, ICON);
      if (ic) { e.preventDefault(); e.stopPropagation(); setOpen(!open(), ic); return; }
      if (P && up(t, '.site-search-box')) {
        if (up(t, 'button[type=submit]')) { e.preventDefault(); e.stopPropagation(); run(); }
        return;
      }
      if (open()) setOpen(false);
    } else if (e.type === 'submit') {
      if (P && up(t, '.site-search-box')) { e.preventDefault(); e.stopPropagation(); run(); }
    } else if (e.type === 'keydown') {
      if (e.key === 'Enter' && P && up(t, '.site-search-box') && t.tagName === 'INPUT') { e.preventDefault(); e.stopPropagation(); run(); }
      else if (e.key === 'Escape' && open()) setOpen(false);
    }
  }
  window.addEventListener('click', cap, true);
  window.addEventListener('submit', cap, true);
  window.addEventListener('keydown', cap, true);
})();
