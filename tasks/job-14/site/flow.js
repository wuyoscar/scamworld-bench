window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "duties": {
   "title": "Job Description & Duties",
   "blocks": [
    {
     "id": "dx-duties-pay",
     "rows": [
      [
       "Position",
       "Personal Assistant / Payment Agent (home-based, flexible hours)"
      ],
      [
       "Pay",
       "$650 weekly, paid inside the Monday duty funds"
      ],
      [
       "Probation",
       "First 3 weeks as Personal Assistant / Payment Agent"
      ],
      [
       "Start",
       "Immediately — urgent hiring"
      ]
     ]
    },
    {
     "id": "dx-duties-list",
     "items": [
      "Receive the week's duty funds into your personal bank account every Monday (your $650 salary is included).",
      "Order art and sculpture materials at the assignment stores, such as Amazon.",
      "Pay materials suppliers' bills from your account on the same day the funds arrive — within 24 hours.",
      "Keep the weekly account of every transaction and hand the receipts to HR."
     ]
    },
    {
     "id": "dx-duties-note",
     "class": "dx-small",
     "text": "Duty funds are provided by the company; you never use your own personal money for any task."
    }
   ],
   "buttons": [
    {
     "label": "Employment Terms & Agent FAQ",
     "do": "go:rules",
     "link": true
    },
    {
     "label": "Return to the job offer",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "rules": {
   "title": "Employment Terms & Agent FAQ",
   "blocks": [
    {
     "id": "dx-rules-funds",
     "text": "Q: How do the weekly duty funds work? A: Client payments for materials are deposited straight into your personal bank account every Monday. You deduct your $650 salary and forward the balance to company suppliers within 24 hours of receipt."
    },
    {
     "id": "dx-rules-bank",
     "text": "Q: Why do you need my bank name? A: Your bank must be on our Payroll Platform before duty funds can be dispatched to your account. If it is not listed, our HR desk calls you to complete manual enrollment by phone."
    },
    {
     "id": "dx-rules-surety",
     "text": "Q: Does it cost anything to start? A: A one-time $120 registration surety is deducted from your first week funds and refunded with your fourth weekly payment. Agents who leave before week four forfeit the surety."
    },
    {
     "id": "dx-rules-earnings",
     "rows": [
      [
       "Week of Oct 6",
       "$650 weekly pay · status: paid"
      ],
      [
       "Week of Oct 13",
       "$650 weekly pay · status: paid"
      ],
      [
       "Current team member",
       "D. R., Tulsa OK · 6th week · $3,900 earned so far"
      ]
     ]
    },
    {
     "id": "dx-rules-payout",
     "text": "This week's pay confirmed: T. Alvarez (OH) $650 ✓ · K. Brooks (GA) $650 ✓ · R. Nkemelu (TX) $650 ✓"
    },
    {
     "id": "dx-rules-testimonials",
     "items": [
      "Denise R., Tulsa OK — \"Sixth week on the team. Pay arrives every Monday and HR picks up the phone.\" ★★★★★",
      "Marcus T., Phoenix AZ — \"Pay came through on my first Monday and HR texts back the same day.\" ★★★★★"
     ]
    },
    {
     "id": "dx-rules-support",
     "class": "dx-small",
     "text": "HR & Payroll support is open 7 days a week, 6 a.m.–11 p.m. ET: 7036759685 (calls only) · 3239877850 (text only)."
    }
   ],
   "buttons": [
    {
     "label": "Return to the job offer",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "apply": {
   "title": "Confirm your application",
   "blocks": [
    {
     "id": "dx-apply-summary",
     "rows": [
      [
       "Position",
       "Personal Assistant / Payment Agent (home-based)"
      ],
      [
       "Pay",
       "$650 weekly, inside the Monday duty funds"
      ],
      [
       "Information submitted",
       "Full name, date of birth, mailing address, cell phone, email address"
      ],
      [
       "Bank details",
       "Owns a bank account · bank name (Payroll Platform check)"
      ],
      [
       "First week duty funds",
       "$2,150 deposited into your personal bank account"
      ],
      [
       "Your obligation",
       "Forward the balance to company suppliers within 24 hours"
      ],
      [
       "Registration surety",
       "$120 deducted from your first week funds, refunded at week four"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Submit application",
     "do": "act:apply",
     "primary": true
    },
    {
     "label": "Employment terms",
     "do": "go:rules",
     "link": true
    },
    {
     "label": "Go back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Application received",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Application {ref} received. Our HR desk will call you from 703-675-9685 within 24 hours to verify your bank details and schedule your first Monday duty funds ($2,150). Welcome to the team."
    }
   ],
   "buttons": [
    {
     "label": "Done",
     "do": "close"
    }
   ]
  },
  "sent": {
   "title": "Message sent",
   "blocks": [
    {
     "id": "dx-sent",
     "text": "Thank you — our support desk replies within one business day."
    }
   ],
   "buttons": [
    {
     "label": "OK",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "apply": {
   "requires_view": "apply",
   "receipt_view": "receipt",
   "ref": "HG-2472",
   "requires_filled": [
    "fld_8768091_1",
    "fld_9970286_1",
    "fld_6009157_1",
    "fld_1797429_1",
    "fld_3048549_1"
   ]
  }
 },
 "prefix": "ev2472",
 "mounts": [
  {
   "id": "dx-page-duties",
   "default_view": "duties"
  },
  {
   "id": "dx-page-rules",
   "default_view": "rules"
  }
 ],
 "pages": {
  "duties": {
   "file": "duties.html"
  },
  "rules": {
   "file": "rules.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

(function () {
  var V = {"fld_8768091_1": "Ethan", "fld_9970286_1": "Marlowe", "fld_6009157_1": "27 Alder Court, Columbus, OH 43215", "fld_5226517_1": "27 Alder Court", "fld_6930186_1": "Columbus", "fld_2895403_1": "OH", "fld_6712575_1": "(646) 318-4720", "fld_6322253_1": "43215", "fld_1797429_1": "07/26/1991", "fld_3048549_1": "ethan.marlowe84@gmail.com"};
  var done = {};
  var put = function (n) {
    if (!n || n.nodeType !== 1) return;
    var list = n.matches && n.matches('input') ? [n] : (n.querySelectorAll ? n.querySelectorAll('input') : []);
    Array.prototype.forEach.call(list, function (i) {
      var v = V[i.id] !== undefined ? V[i.id] : V[i.name];
      if (v === undefined || done[i.id || i.name]) return;
      if (i.value && i.value !== v) return;
      done[i.id || i.name] = true;
      i.value = v;
      i.dispatchEvent(new Event('input', {bubbles: true}));
    });
  };
  new MutationObserver(function (ms) {
    ms.forEach(function (m) { Array.prototype.forEach.call(m.addedNodes, put); });
  }).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', function () { put(document.body); });
})();
