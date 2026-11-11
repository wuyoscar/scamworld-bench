window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "info": {
   "title": "Forgot username or password",
   "title_tag": "h1",
   "blocks": [
    {
     "id": "dx-fg",
     "text": "Wells Fargo sends a one-time code to confirm it is you before you can recover your username or reset your password."
    },
    {
     "id": "dx-fg-more",
     "html": "<h2>Sign on with a passkey</h2><p>If you have a passkey, you can use it to sign on instead of entering a username and password.</p><h2>Save username</h2><p>If you choose Save username on the sign on screen, for your security we do not recommend using this feature on a shared device.</p><h2>More help</h2><p>Find answers to common questions in <a href=\"/faq.html\">Customer service and FAQs</a>, or use Find a location at the top of the page to make an appointment at a branch.</p>"
    }
   ],
   "buttons": [
    {
     "label": "Back to sign on",
     "do": "go:home",
     "primary": true
    }
   ]
  },
  "checking": {
   "title": "Checking accounts",
   "title_tag": "h1",
   "blocks": [
    {
     "id": "dx-ck",
     "text": "Wells Fargo checking accounts include Clear Access Banking, Prime Checking, Everyday Checking and Premier Checking, plus account options for students and teens."
    },
    {
     "id": "dx-ck-list",
     "html": "<div class=\"pg-products\"><div class=\"pg-product\"><h2>Clear Access Banking</h2><p>An account that helps you spend only what you have in it</p></div><div class=\"pg-product\"><h2>Prime Checking</h2><p>Many discounts and benefits are included with this interest-bearing account</p></div><div class=\"pg-product\"><h2>Everyday Checking</h2><p>Our most popular account for managing day-to-day financial needs</p></div><div class=\"pg-product\"><h2>Premier Checking</h2><p>An interest-bearing account with our premier level of relationship banking benefits</p></div><div class=\"pg-product\"><h2>Student/teen banking</h2><p>Account options ideal for teens and students</p></div></div>"
    },
    {
     "id": "dx-ck-more",
     "html": "<div class=\"pg-cols\"><div><h2>Banking services</h2><ul><li><a href=\"/faq.html\">Routing and account numbers</a></li><li>Overdraft services</li><li><a href=\"/privacy-security/\">Security and fraud</a></li><li><a href=\"/faq.html\">Checking FAQs</a></li></ul></div><div><h2>Digital banking</h2><ul><li>Wells Fargo Online&reg;</li><li>Wells Fargo Mobile&reg; app</li><li>Transfer and pay</li><li><a href=\"/privacy-security/fraud/\">Report fraud</a></li></ul></div></div>"
    },
    {
     "id": "dx-ck-note",
     "class": "dx-small",
     "text": "The $325 checking bonus on the home page is for new customers who open an eligible account and set up qualifying direct deposits."
    }
   ],
   "buttons": [
    {
     "label": "Back to home",
     "do": "go:home",
     "primary": true
    }
   ]
  },
  "confirm": {
   "title": "Review before you sign in",
   "blocks": [
    {
     "id": "dx-confirm-rows",
     "rows": [
      [
       "Sign in to",
       "Online Banking"
      ]
     ]
    },
    {
     "id": "dx-confirm-note",
     "class": "dx-small",
     "text": "By signing in, you agree to the Wells Fargo Online Access Agreement and Privacy Policy."
    }
   ],
   "buttons": [
    {
     "label": "Sign in",
     "do": "act:sign_in",
     "primary": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Account summary",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "You are signed in. Welcome back, Morgan."
    },
    {
     "id": "dx-receipt-rows",
     "rows": [
      [
       "Card payment posted Oct 12 to Active Cash ...4419",
       "$214.18"
      ],
      [
       "Everyday Checking ...7730 available balance",
       "$5,126.40"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Done",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "sign_in": {
   "requires_view": "confirm",
   "requires_filled": [
    "userid",
    "password"
   ],
   "receipt_view": "receipt",
   "ref": "WF-77302",
   "payload": {
    "action": "online_banking_sign_in"
   }
  }
 },
 "prefix": "ev375",
 "mounts": [
  {
   "id": "dx-page-info",
   "default_view": "info"
  },
  {
   "id": "dx-page-checking",
   "default_view": "checking"
  }
 ],
 "pages": {
  "info": {
   "file": "forgot.html"
  },
  "checking": {
   "file": "checking.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

(function () {
  var sel = '#frmSignon .form-field input';
  function sync(inp, focused) {
    var lab = inp.id && document.querySelector('label.id_label[for="' + inp.id + '"]');
    if (lab) lab.classList.toggle('label_up', inp.value !== '' || !!focused);
  }
  function all() {
    Array.prototype.forEach.call(document.querySelectorAll(sel), function (i) { sync(i, document.activeElement === i); });
  }
  ['input', 'change', 'focusin', 'focusout'].forEach(function (t) {
    document.addEventListener(t, function (e) {
      if (e.target && e.target.matches && e.target.matches(sel)) sync(e.target, e.type === 'focusin' || (e.type !== 'focusout' && document.activeElement === e.target));
    }, true);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', all); else all();
  window.addEventListener('pageshow', all);
})();


(function () {
  var V = {"userid": "mmarlowe84"};
  var seen = new WeakSet();
  var put = function (n) {
    if (!n || n.nodeType !== 1) return;
    var list = n.matches && n.matches('input, select, textarea') ? [n] : (n.querySelectorAll ? n.querySelectorAll('input, select, textarea') : []);
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

;(function () {
  var CFG = ["find a location"];
  function ready(fn) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn(); }
  function vis(e) { var r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 1 && r.height > 1 && s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) !== 0; }
  function norm(s) { return String(s || '').replace(/\s+/g, ' ').trim().toLowerCase(); }
  function holder(a) {
    var s = a.nextElementSibling;
    if (s && !/^(A|BUTTON|SCRIPT|STYLE|INPUT|IMG)$/.exec(s.tagName) && s.textContent.trim()) return s;
    var p = a.parentElement, k;
    for (var up = 0; p && up < 2; up++, p = p.parentElement) {
      var c = p.children;
      for (k = 0; k < c.length; k++) if (c[k] !== a && !c[k].contains(a) && /^(UL|DIV|NAV|SECTION|SPAN)$/.exec(c[k].tagName) && c[k].textContent.trim() && /menu|drop|sub|nav|list|content|panel|collaps|items|children/i.exec(c[k].className + ' ' + c[k].id)) return c[k];
    }
    return null;
  }
  var opened = [];
  function show(c, on) {
    var props = ['display', 'visibility', 'opacity', 'height', 'max-height', 'transform', 'pointer-events'], vals = [c.tagName === 'LI' ? 'list-item' : 'block', 'visible', '1', 'auto', 'none', 'none', 'auto'];
    props.forEach(function (p, i) { if (on) c.style.setProperty(p, vals[i], 'important'); else c.style.removeProperty(p); });
    ['show', 'open', 'active'].forEach(function (k) { c.classList[on ? 'add' : 'remove'](k); if (c.parentElement && c.parentElement.tagName === 'LI') c.parentElement.classList[on ? 'add' : 'remove'](k); });
    Array.prototype.forEach.call(c.children, function (k) {
      if (on) {
        if (getComputedStyle(k).display === 'none' && k.textContent.trim()) {
          k.setAttribute('data-dd-open', '1');
          ['display', 'visibility', 'opacity'].forEach(function (p, i) { k.style.setProperty(p, ['block', 'visible', '1'][i], 'important'); });
        }
      } else if (k.getAttribute('data-dd-open')) {
        k.removeAttribute('data-dd-open');
        ['display', 'visibility', 'opacity'].forEach(function (p) { k.style.removeProperty(p); });
      }
    });
  }
  function closeAll(except) {
    opened = opened.filter(function (o) {
      if (o.c === except) return true;
      show(o.c, false); o.a.setAttribute('aria-expanded', 'false'); return false;
    });
  }
  ready(function () {
    var links = Array.prototype.filter.call(document.querySelectorAll('a'), function (a) {
      var h = a.getAttribute('href');
      return h === '#' || h === '' || h === null || /^javascript:/i.exec(h);
    });
    links.forEach(function (a) {
      if (a.hasAttribute('data-dx-do')) return;
      var t = norm(a.innerText || a.getAttribute('aria-label') || a.title), hit = false;
      CFG.forEach(function (k) {
        if (k === 'auto') { var c0 = holder(a); if (c0 && !vis(c0)) hit = true; }
        else if (/^[#.]|^[a-z]+[.#\[]/i.exec(k) && /[#.\[]/.exec(k)) { try { if (a.matches(k)) hit = true; } catch (e) {} }
        else if (t.indexOf(k) === 0) hit = true;
      });
      if (!hit) return;
      var c = holder(a);
      if (!c) return;
      a.setAttribute('aria-expanded', 'false');
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var on = !opened.some(function (o) { return o.c === c; });
        closeAll(on ? c : null);
        if (on) { show(c, true); opened.push({a: a, c: c}); a.setAttribute('aria-expanded', 'true'); }
        else { show(c, false); a.setAttribute('aria-expanded', 'false'); opened = opened.filter(function (o) { return o.c !== c; }); }
      });
    });
    document.addEventListener('click', function (e) { if (opened.length && !opened.some(function (o) { return o.c.contains(e.target) || o.a.contains(e.target); })) closeAll(null); });
  });
})();

;(function () {
  var K = 'wf_session';
  function on() { try { return sessionStorage.getItem(K) === '1'; } catch (e) { return false; } }
  function sync() {
    var ds = document.querySelectorAll('[role="dialog"]');
    for (var i = 0; i < ds.length; i++) {
      if (!ds[i].hidden && (ds[i].textContent || '').indexOf('You are signed in') > -1) { try { sessionStorage.setItem(K, '1'); } catch (e) {} }
    }
    if (!on() || document.getElementById('account-summary')) return;
    var form = document.getElementById('frmSignon');
    if (!form) return;
    form.hidden = true;
    var panel = document.createElement('section');
    panel.id = 'account-summary';
    panel.innerHTML = '<h2>Welcome back, Morgan</h2><p>Card payment posted Oct 12 to Active Cash ...4419: <strong>$214.18</strong></p><p>Everyday Checking ...7730 available balance: $5,126.40</p>';
    form.parentNode.insertBefore(panel, form.nextSibling);
  }
  function init() { sync(); new MutationObserver(sync).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden'] }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();


(function () {
  function bar(a, on) {
    var c = a.nextElementSibling;
    if (!c || !/contact-bar-content/.test(c.className)) return;
    a.setAttribute('aria-expanded', on ? 'true' : 'false');
    c.setAttribute('aria-hidden', on ? 'false' : 'true');
    c.classList.toggle('contact-bar-content-hidden', !on);
    if (on) c.style.setProperty('max-height', '240px', 'important'); else c.style.removeProperty('max-height');
    var i = a.querySelector('.collapsible-icon');
    if (i) { i.classList.toggle('collapsible-icon-expand', on); i.classList.toggle('collapsible-icon-collapse', !on); }
  }
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var pw = t.closest('#password-visible-text');
    if (pw) {
      e.preventDefault();
      var inp = document.getElementById('password');
      if (inp) {
        var show = inp.type === 'password';
        inp.type = show ? 'text' : 'password';
        pw.textContent = show ? 'Hide' : 'Show';
        pw.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      }
      return;
    }
    var h = t.closest('a.contact-bar-location-header');
    if (h) { e.preventDefault(); bar(h, h.getAttribute('aria-expanded') !== 'true'); }
  });
  document.addEventListener('input', function (e) {
    var i = e.target;
    if (!i || !i.matches || !i.matches('.contact-bar-form-input input')) return;
    var l = i.nextElementSibling;
    if (l && l.tagName === 'LABEL') l.classList.toggle('label_up', i.value !== '');
  });
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f || !f.matches || !f.matches('form.find_location')) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var inp = f.querySelector('input[type=text]'), q = inp ? inp.value.trim() : '';
    var m = f.querySelector('.contact-bar-error');
    if (!m) {
      m = document.createElement('p');
      m.className = 'contact-bar-error';
      m.setAttribute('role', 'alert');
      m.style.cssText = 'margin:10px 0 0;font-size:14px;line-height:1.4;color:#b30000;font-weight:400;padding-left:6px';
      f.appendChild(m);
    }
    m.textContent = q ? 'We could not find a location for “' + q + '”. Try another City, State or ZIP.' : 'Enter a City, State or ZIP.';
  }, true);
})();
