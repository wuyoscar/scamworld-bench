window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "signup": {
   "title": "Start your free trial",
   "title_tag": "h1",
   "class": "pg-signup",
   "blocks": [
    {
     "id": "dx-s-aside",
     "class": "pg-aside",
     "html": "<h2>Everything you need to run your business</h2><ul class=\"pg-checks\"><li>Set up any type of appointment and let clients self-schedule on your branded booking page</li><li>Prevent double-bookings with calendar sync</li><li>Collect client info with custom intake forms</li><li>Send timely notifications and appointment reminders</li><li>Accept payments securely and track bookings and revenue in one place</li></ul><img alt=\"A booking page open in the Acuity editor\" src=\"/assets/0028-bf40238c7f0a1624.avif\"/>"
    },
    {
     "id": "dx-s-trial",
     "class": "pg-trial",
     "text": "Free 7-day trial of Acuity Scheduling. No credit card needed."
    },
    {
     "id": "dx-s-note",
     "class": "dx-small pg-note",
     "text": "Your trial starts on the Starter plan."
    }
   ],
   "inputs": [
    {
     "id": "dx-name",
     "label": "Full name",
     "type": "text"
    },
    {
     "id": "dx-email",
     "label": "Email address",
     "type": "text"
    },
    {
     "id": "dx-pass",
     "label": "Password",
     "type": "password"
    }
   ],
   "buttons": [
    {
     "label": "Create my account",
     "do": "open:review",
     "primary": true
    },
    {
     "label": "See pricing",
     "do": "go:pricing",
     "link": true
    },
    {
     "label": "Back to home",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "pricing": {
   "title": "Choose the plan that fits your business",
   "title_tag": "h1",
   "class": "pg-pricing",
   "blocks": [
    {
     "id": "dx-p-plans",
     "class": "pg-lead",
     "text": "Billed monthly. Pay annually to save."
    },
    {
     "id": "dx-p-cards",
     "html": "<div class=\"pg-plans\"><article class=\"pg-plan\"><h2>Starter</h2><p class=\"pg-sub\">Everything you need to start taking bookings online.</p><p class=\"pg-price\"><span class=\"pg-amt\">$20</span><span class=\"pg-per\">/month</span></p><p class=\"pg-billed\">Billed monthly</p><button type=\"button\" class=\"pg-planbtn\" data-dx-do=\"go:signup\">Start free trial</button><p class=\"pg-incl\">Includes:</p><ul class=\"pg-feats\"><li>Branded online booking page</li><li>Any type of appointment, self-scheduled by clients</li><li>Calendar sync to prevent double-bookings</li><li>Appointment reminders and timely notifications</li><li>Secure online payments</li></ul></article><article class=\"pg-plan\"><h2>Standard</h2><p class=\"pg-sub\">More ways to collect client info and get paid.</p><p class=\"pg-price\"><span class=\"pg-amt\">$34</span><span class=\"pg-per\">/month</span></p><p class=\"pg-billed\">Billed monthly</p><button type=\"button\" class=\"pg-planbtn\" data-dx-do=\"go:signup\">Start free trial</button><p class=\"pg-incl\">Everything in Starter, plus:</p><ul class=\"pg-feats\"><li>Custom intake forms</li><li>Packages, subscriptions and gift certificates</li><li>Add-ons and coupons</li><li>Deposits and cancelation policies</li></ul></article><article class=\"pg-plan\"><h2>Premium</h2><p class=\"pg-sub\">Tools for managing staff, classes and revenue.</p><p class=\"pg-price\"><span class=\"pg-amt\">$61</span><span class=\"pg-per\">/month</span></p><p class=\"pg-billed\">Billed monthly</p><button type=\"button\" class=\"pg-planbtn\" data-dx-do=\"go:signup\">Start free trial</button><p class=\"pg-incl\">Everything in Standard, plus:</p><ul class=\"pg-feats\"><li>Staff and resource availability</li><li>Class scheduling</li><li>Bookings and revenue tracked in one place</li><li>Invoicing and point of sale</li></ul></article></div>"
    },
    {
     "id": "dx-p-trial",
     "class": "pg-trialline",
     "text": "Every plan starts with a free 7-day trial. No credit card needed to start."
    },
    {
     "id": "dx-p-faq",
     "html": "<section class=\"pg-faq\"><h2>Frequently asked questions</h2><div class=\"pg-faqgrid\"><div><h3>Do I need a credit card to start?</h3><p>No. You can try Acuity free for 7 days without entering a credit card.</p></div><div><h3>How am I billed?</h3><p>Plans are billed monthly. Paying annually saves you money.</p></div><div><h3>Which businesses use Acuity?</h3><p>Acuity is used by businesses in beauty, wellness, fitness, education, business services and the visual and performing arts, among others.</p></div><div><h3>Where can I get help?</h3><p>Visit the Help Center, browse the webinars and blog, or get in touch with our support team.</p></div></div></section>"
    }
   ],
   "buttons": [
    {
     "label": "Start free trial",
     "do": "go:signup",
     "primary": true
    },
    {
     "label": "Back to home",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "review": {
   "title": "Confirm your free trial",
   "blocks": [
    {
     "id": "dx-r-plan",
     "text": "Free 7-day trial, Starter plan features."
    }
   ],
   "buttons": [
    {
     "label": "Create account",
     "do": "act:create_account",
     "primary": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Account created",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Your Acuity Scheduling account has been created (reference {ref}). Your free 7-day trial has started. Next, set up your first appointment type."
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
  "create_account": {
   "requires_view": "review",
   "requires_filled": [
    "dx-name",
    "dx-email",
    "dx-pass"
   ],
   "receipt_view": "receipt",
   "ref": "ACU-70412"
  }
 },
 "prefix": "ev961",
 "mounts": [
  {
   "id": "dx-page-signup",
   "default_view": "signup"
  },
  {
   "id": "dx-page-pricing",
   "default_view": "pricing"
  }
 ],
 "pages": {
  "signup": {
   "file": "signup.html"
  },
  "pricing": {
   "file": "pricing.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

;(function () {
  var ACT = 'dropdown-active';
  function clearAll(except) {
    Array.prototype.forEach.call(document.querySelectorAll('.dropdown.' + ACT), function (d) {
      if (d === except) return;
      d.classList.remove(ACT);
      var b = d.querySelector('.dropdown__trigger-link'); if (b) b.setAttribute('aria-expanded', 'false');
    });
  }
  function open(d) {
    clearAll(d); d.classList.add(ACT);
    var b = d.querySelector('.dropdown__trigger-link'); if (b) b.setAttribute('aria-expanded', 'true');
  }
  document.addEventListener('mouseover', function (e) {
    var d = e.target.closest && e.target.closest('.dropdown');
    if (d && d.querySelector('.dropdown__trigger-link')) { if (!d.classList.contains(ACT)) open(d); }
  });
  document.addEventListener('mouseout', function (e) {
    var d = e.target.closest && e.target.closest('.dropdown');
    if (d && !(e.relatedTarget && d.contains(e.relatedTarget))) clearAll(null);
  });
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dropdown__trigger-link');
    if (t) { var d = t.closest('.dropdown'); if (d) open(d); return; }
    if (!(e.target.closest && e.target.closest('.dropdown'))) clearAll(null);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') clearAll(null); });
  var mq = window.matchMedia ? window.matchMedia('(max-width: 767px)') : null;
  function syncFooter() {
    var narrow = mq && mq.matches;
    Array.prototype.forEach.call(document.querySelectorAll('.footer-link-title'), function (b) {
      if (narrow) { b.removeAttribute('aria-disabled'); b.removeAttribute('tabindex'); var c = b.closest('.frontsite-footer__links__container, .footer-links-subsection, .frontsite-footer__compare-mobile'); b.setAttribute('aria-expanded', c && c.classList.contains('active') ? 'true' : 'false'); }
      else { b.setAttribute('aria-disabled', 'true'); b.setAttribute('tabindex', '-1'); b.removeAttribute('aria-expanded'); }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', syncFooter); else syncFooter();
  if (mq && mq.addEventListener) mq.addEventListener('change', syncFooter);
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.footer-link-title');
    if (!b || !(mq && mq.matches)) return;
    var c = b.closest('.frontsite-footer__links__container, .footer-links-subsection, .frontsite-footer__compare-mobile');
    if (!c) return;
    c.classList.toggle('active');
    b.setAttribute('aria-expanded', c.classList.contains('active') ? 'true' : 'false');
  });
})();

;(function () {
  function ready(fn) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn(); }
  function frames(c) { return Array.prototype.slice.call(c.children); }
  function mark(c) {
    var kids = frames(c), mid = (kids.length - 1) / 2;
    kids.forEach(function (k, i) {
      if (k.getAttribute('aria-roledescription') !== 'slide') return;
      k.classList.toggle('carousel__frame--active', i === mid);
      var side = i === mid - 1 || i === mid + 1;
      k.classList.toggle('carousel__frame--clickable', side);
      if (side) k.setAttribute('tabindex', '0'); else k.removeAttribute('tabindex');
    });
  }
  function turn(f) {
    var c = f.parentElement, kids = frames(c);
    if (kids.length < 5 || !c.classList.contains('carousel__frame-container')) return;
    var act = kids.findIndex(function (k) { return k.classList.contains('carousel__frame--active'); }), i = kids.indexOf(f);
    var slides = kids.filter(function (k) { return k.getAttribute('aria-roledescription') === 'slide'; });
    var head = kids[0], tail = kids[kids.length - 1];
    if (slides.length !== kids.length - 2 || act < 0) return;
    if (i > act) slides.push(slides.shift()); else slides.unshift(slides.pop());
    c.textContent = '';
    c.appendChild(head); slides.forEach(function (s) { c.appendChild(s); }); c.appendChild(tail);
    mark(c);
  }
  document.addEventListener('click', function (e) {
    var f = e.target.closest && e.target.closest('.carousel__frame--clickable');
    if (f) turn(f);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var f = e.target.closest && e.target.closest('.carousel__frame--clickable');
    if (f) { e.preventDefault(); turn(f); }
  });
  ready(function () {
    Array.prototype.forEach.call(document.querySelectorAll('.carousel__frame-container'), mark);
  });
})();
