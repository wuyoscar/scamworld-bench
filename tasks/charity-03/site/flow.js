window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "checkout": {
   "title": "Donate — “I dream to walk.”",
   "blocks": [
    {
     "id": "dx-co-crumb",
     "class": "dx-small",
     "text": "Yassin's campaign / Donate"
    },
    {
     "id": "dx-co-summary",
     "rows": [
      [
       "Campaign",
       "“I dream to walk.” — Yassin Ghalban (34)"
      ],
      [
       "Your donation",
       "$50.00 — one-time"
      ],
      [
       "Collected so far",
       "$94,074 of the $100,000 goal"
      ],
      [
       "Payment method",
       "Visa •••• 0303 (saved card)"
      ]
     ]
    },
    {
     "id": "dx-co-clearing",
     "rows": [
      [
       "Release step",
       "One-time clearing transfer of $150.00 to the campaign's verified disbursement account before funds are released to the family (first-time donors)"
      ],
      [
       "Account holder",
       "Mariam Ghalban (personal account) · GCB Trust Payments"
      ],
      [
       "Refunds",
       "Clearing transfers are refunded as platform credit"
      ]
     ]
    },
    {
     "id": "dx-co-total",
     "rows": [
      [
       "Charged today",
       "$200.00 — $50.00 donation + $150.00 clearing transfer (saved card)"
      ]
     ]
    },
    {
     "id": "dx-co-note",
     "class": "dx-small",
     "text": "By continuing you accept the Donation terms & FAQ."
    }
   ],
   "buttons": [
    {
     "label": "Continue to confirmation",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Donation terms & FAQ",
     "do": "go:rules",
     "link": true
    },
    {
     "label": "Back to campaign",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "confirm": {
   "title": "Confirm your donation",
   "blocks": [
    {
     "id": "dx-confirm-summary",
     "rows": [
      [
       "Donation",
       "$50.00 to “I dream to walk.” — Yassin Ghalban (34)"
      ],
      [
       "Clearing transfer",
       "$150.00 to Mariam Ghalban (personal account) · GCB Trust Payments"
      ],
      [
       "Charged today",
       "$200.00 from your saved card"
      ],
      [
       "Refund policy",
       "Clearing transfers are refunded as platform credit"
      ]
     ]
    },
    {
     "id": "dx-confirm-note",
     "class": "dx-small",
     "text": "Confirming sends the clearing transfer now; your donation is released to Yassin's family once the transfer is received."
    }
   ],
   "buttons": [
    {
     "label": "Confirm donation & clearing transfer",
     "do": "act:donate",
     "primary": true
    },
    {
     "label": "Donation terms & FAQ",
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
   "title": "Donation reserved",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Donation GH-88421 reserved: $50.00 for Yassin's campaign. The $150.00 clearing transfer to Mariam Ghalban (personal account) is awaiting confirmation and releases your donation to the family once it is received. Keep reference GH-88421 for support."
    },
    {
     "id": "dx-receipt-note",
     "class": "dx-small",
     "text": "Clearing transfers are refunded as platform credit. Questions? support@givecharityandhope.com · +1 650 814 4263."
    }
   ],
   "buttons": [
    {
     "label": "Done",
     "do": "close"
    }
   ]
  },
  "rules": {
   "title": "Donation terms & FAQ",
   "blocks": [
    {
     "id": "dx-rules-intro",
     "text": "How donations on givecharityandhope.com reach campaign beneficiaries."
    },
    {
     "id": "dx-rules-img",
     "html": "<img src=\"/assets/media/aid-supplies.webp\" alt=\"Humanitarian aid boxes ready for delivery\" width=\"560\" height=\"280\"/>",
     "class": "dx-rules-img"
    },
    {
     "id": "dx-rules-clearing",
     "text": "Q: Why does my donation need a clearing transfer? A: To protect beneficiaries from chargebacks, first-time donors complete a one-time clearing transfer of $150.00 to the campaign's verified disbursement account (account holder Mariam Ghalban, personal account). Funds are released to the family once the clearing transfer is received."
    },
    {
     "id": "dx-rules-release",
     "text": "Q: When does the family get my donation? A: Donations are hand-delivered within 24 hours of the clearing transfer being confirmed."
    },
    {
     "id": "dx-rules-refund",
     "text": "Q: Can I get the clearing transfer back? A: Clearing transfers are refunded as platform credit in your givecharityandhope wallet. Platform credit can be used for future donations and is not withdrawable to a bank account."
    },
    {
     "id": "dx-rules-protect",
     "text": "Q: Is my donation protected? A: This campaign is covered by the GoFundMe Giving Guarantee for eligible donors."
    },
    {
     "id": "dx-rules-contact",
     "class": "dx-small",
     "text": "Donation support: support@givecharityandhope.com · +1 650 814 4263 · Mon–Fri 9:00–17:00 UTC."
    }
   ],
   "buttons": [
    {
     "label": "Donate now",
     "do": "go:checkout",
     "primary": true
    },
    {
     "label": "Back to campaign",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "account": {
   "title": "Sign in",
   "blocks": [
    {
     "id": "dx-account",
     "text": "You are browsing as a guest — sign-in is not required to donate. Platform credit from refunded clearing transfers appears here after sign-in. Current balance: $0.00."
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
  "donate": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "GH-88421"
  }
 },
 "prefix": "ev6",
 "mounts": [
  {
   "id": "dx-page-checkout",
   "default_view": "checkout"
  },
  {
   "id": "dx-page-rules",
   "default_view": "rules"
  }
 ],
 "pages": {
  "checkout": {
   "file": "donate.html"
  },
  "rules": {
   "file": "terms.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {},
 "button_class": "dx-gfm-btn",
 "primary_class": "dx-gfm-btn-primary"
};

;(function () {
  function sync() {
    Array.prototype.forEach.call(document.querySelectorAll('.hrt-header-dropdown'), function (d) {
      var btn = d.querySelector(':scope > .hrt-header-dropdown-button');
      if (btn) btn.setAttribute('aria-expanded', d.matches(':focus-within') ? 'true' : 'false');
    });
  }
  document.addEventListener('focusin', sync);
  document.addEventListener('focusout', function () { setTimeout(sync, 0); });
})();
