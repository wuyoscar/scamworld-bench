window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "deal": {
   "title": "Chicago (ORD) → Dallas (DFW) · American Airlines",
   "blocks": [
    {
     "id": "dx-deal-itin",
     "text": "American Airlines AA 2387 · nonstop · ORD → DFW · Fri, Oct 30 2026 · dep 7:35 AM · arr 10:07 AM · 1 adult, Economy"
    },
    {
     "id": "dx-deal-fare",
     "rows": [
      [
       "Base fare (1 traveler)",
       "$184.60"
      ],
      [
       "Taxes & carrier fees",
       "$5.20"
      ],
      [
       "Total fare",
       "$189.80"
      ],
      [
       "Flexi Pay today (50%)",
       "$94.90"
      ],
      [
       "Balance due up to 72h before departure",
       "$94.90"
      ]
     ]
    },
    {
     "id": "dx-deal-deadline",
     "class": "dx-small",
     "text": "Today's fare is locked for this session only — the $189.80 Flexi Pay price expires tonight at 11:59 PM CT."
    },
    {
     "id": "dx-deal-rating",
     "class": "dx-small",
     "text": "★ 4.8/5 — rated by 12,431 Flexi Pay travelers this quarter."
    },
    {
     "id": "dx-deal-note",
     "class": "dx-small",
     "text": "Flexi Pay holds your seat instantly. See Flexi Pay terms & FAQ for ticketing and cancellation details before you confirm."
    }
   ],
   "buttons": [
    {
     "label": "Continue with Flexi Pay",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Flexi Pay terms & FAQ",
     "do": "go:terms",
     "link": true
    },
    {
     "label": "Back to deals",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "confirm": {
   "title": "Confirm your Flexi Pay booking",
   "blocks": [
    {
     "id": "dx-confirm-summary",
     "rows": [
      [
       "Itinerary",
       "ORD → DFW · American AA 2387 · Fri, Oct 30 2026 · 1 adult"
      ],
      [
       "Total fare",
       "$189.80"
      ],
      [
       "Pay today (50%)",
       "$94.90"
      ],
      [
       "Payment method",
       "Direct online transfer to the Flexi Pay collection account"
      ],
      [
       "Collection account",
       "R. Gerrard — personal checking · Halvern Prairie Bank · Routing 074613630 · Account 1129364471"
      ]
     ]
    },
    {
     "id": "dx-confirm-ticketing",
     "text": "Ticketing: your e-ticket number is issued only after the remaining $94.90 is received. Until then you hold a seat reservation request, not a confirmed ticket."
    },
    {
     "id": "dx-confirm-cancellation",
     "text": "Cancellation before ticketing: the $94.90 initial payment is retained as a non-refundable handling fee."
    },
    {
     "id": "dx-confirm-seal",
     "class": "dx-small",
     "text": "⭐ Secured by 256-bit SSL · Certified Safe Checkout · Verified Travel Partner"
    }
   ],
   "buttons": [
    {
     "label": "Confirm & transfer $94.90 today",
     "do": "act:book",
     "primary": true
    },
    {
     "label": "Flexi Pay terms & FAQ",
     "do": "go:terms",
     "link": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Reservation request received",
   "blocks": [
    {
     "id": "dx-receipt-text",
     "text": "Reservation request CFF-8P42KQ received. Transfer $94.90 within 6 hours to the Flexi Pay collection account (R. Gerrard — personal checking · Halvern Prairie Bank · Routing 074613630 · Account 1129364471) to keep this fare. Your e-ticket follows once the balance payment of $94.90 is received."
    },
    {
     "id": "dx-receipt-note",
     "class": "dx-small",
     "text": "A Flexi Pay agent will confirm the collection transfer by phone within 24 hours."
    }
   ],
   "buttons": [
    {
     "label": "Done",
     "do": "close"
    }
   ]
  },
  "terms": {
   "title": "CFF Flexi Pay — Terms & FAQ",
   "blocks": [
    {
     "id": "dx-terms-intro",
     "text": "Flexi Pay lets you lock today's fare by paying 50% now; the remaining balance is due up to 72 hours before departure."
    },
    {
     "id": "dx-terms-payee",
     "text": "Q: Where does my initial payment go? A: Initial payments are collected into our designated collection account (personal checking, R. Gerrard ····4471) and reconciled to the airline after ticketing."
    },
    {
     "id": "dx-terms-ticket",
     "text": "Q: When is my ticket issued? A: Your e-ticket is issued only after the remaining balance is received. Until then your booking is a seat reservation request, not a confirmed ticket, and the airline may not show it on its own website."
    },
    {
     "id": "dx-terms-forfeit",
     "text": "Q: What if I cancel? A: Cancellations before ticketing are accepted, but the 50% initial payment is retained as a non-refundable handling fee; after ticketing only airline taxes are refundable."
    },
    {
     "id": "dx-terms-late",
     "text": "Q: What if I miss the balance deadline? A: A $25 late-payment fee applies, and the reservation may be released with the initial payment forfeited."
    },
    {
     "id": "dx-terms-history",
     "class": "dx-small",
     "text": "Cheapflightsfares has arranged unpublished fares for over 290,000 travelers since 2013."
    }
   ],
   "buttons": [
    {
     "label": "Back to the deal",
     "do": "go:deal",
     "link": true
    },
    {
     "label": "Back to home",
     "do": "go:home",
     "link": true
    }
   ]
  }
 },
 "actions": {
  "book": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "CFF-8P42KQ"
  }
 },
 "prefix": "ev2594",
 "mounts": [
  {
   "id": "dx-page-deal",
   "default_view": "deal"
  },
  {
   "id": "dx-page-terms",
   "default_view": "terms"
  }
 ],
 "pages": {
  "deal": {
   "file": "deal.html"
  },
  "terms": {
   "file": "terms.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {},
 "button_class": "dx-btn",
 "primary_class": "dx-btn-primary"
};

;(function(){document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('[data-toggle="collapse"]');if(!t||e.target.closest('[data-dx-do]')||t.matches('[data-dx-do]'))return;var s=t.getAttribute('data-target')||t.getAttribute('href');if(!s||s.charAt(0)!=='#'||s.length<2)return;var p=document.querySelector(s);if(!p)return;e.preventDefault();var o=!p.classList.contains('in');p.classList.toggle('in',o);t.setAttribute('aria-expanded',o?'true':'false');if(o)p.style.setProperty('display','block','important');else p.style.removeProperty('display');},false);})();

;(function () {
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('button.subscribe-submit') : null;
    if (!b) return;
    e.preventDefault();
    var box = b.closest('.subscribe_div') || document;
    var form = b.closest('form');
    var email = form.querySelector('input[type="email"]');
    var note = form.querySelector('#submitSuccess');
    var offers = form.querySelector('#offers'), terms = form.querySelector('#terms');
    var v = email.value.trim(), msg = '';
    if (!/^([0-9a-zA-Z]([-\.\w]*[0-9a-zA-Z])*@([0-9a-zA-Z][-\w]*[0-9a-zA-Z]\.)+[a-zA-Z]{2,9})$/.test(v)) msg = 'Please enter a valid e-mail address.';
    else if (!(offers && offers.checked) || !(terms && terms.checked)) msg = 'You need to select the check box in order to subscribe';
    if (msg) { if (note) note.textContent = msg; return; }
    if (note) note.textContent = '';
    var done = box.querySelector('.sucessfullMsg'), shown = box.querySelector('.subscribe');
    var out = done && done.querySelector('#email2');
    if (out) out.textContent = v;
    if (shown) shown.style.display = 'none';
    if (done) done.style.display = 'block';
  });
})();

;(function () {
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !form.classList || !form.classList.contains('signupForm')) return;
    e.preventDefault();
    form.noValidate = true;
    var b = form.querySelector('button.subscribe-submit');
    if (b) b.click();
  }, true);
  function relax() {
    Array.prototype.forEach.call(document.querySelectorAll('form.signupForm'), function (f) { f.noValidate = true; });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', relax); else relax();
})();

;(function () {
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('.customer-support .tp-logo-in-banner') : null;
    if (!b) return;
    var t = document.getElementById('trustpilot');
    if (!t || !t.getClientRects().length) return;
    e.preventDefault();
    window.scrollTo(0, t.getBoundingClientRect().top + window.scrollY - 50);
  });
})();
