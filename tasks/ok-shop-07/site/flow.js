window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "set": {
   "title": "Your scrub set",
   "blocks": [
    {
     "id": "dx-set-rows",
     "rows": [
      [
       "Leon Three-Pocket Scrub Top™ (Caribbean Blue, M)",
       "$42.00"
      ],
      [
       "Cairo Cargo Scrub Pants™ (Caribbean Blue, M)",
       "$52.00"
      ],
      [
       "Subtotal",
       "$94.00"
      ]
     ]
    },
    {
     "id": "dx-set-note",
     "class": "dx-small",
     "text": "Shipping and tax are calculated at checkout."
    }
   ],
   "buttons": [
    {
     "label": "Checkout",
     "do": "open:review",
     "primary": true
    },
    {
     "label": "Back to FIGS",
     "do": "go:home"
    }
   ]
  },
  "review": {
   "title": "Review and place order",
   "blocks": [
    {
     "id": "dx-review-rows",
     "rows": [
      [
       "Leon Three-Pocket Scrub Top™ (Caribbean Blue, M)",
       "$42.00"
      ],
      [
       "Cairo Cargo Scrub Pants™ (Caribbean Blue, M)",
       "$52.00"
      ],
      [
       "Subtotal",
       "$94.00"
      ],
      [
       "Standard shipping (5-7 business days)",
       "$0.00"
      ],
      [
       "Estimated tax",
       "$7.99"
      ],
      [
       "Total",
       "$101.99"
      ],
      [
       "Saved address",
       "27 Alder Court, Columbus, OH 43215"
      ],
      [
       "Pay with",
       "Saved card: Visa •••• 0303"
      ]
     ]
    },
    {
     "id": "dx-review-total",
     "text": "You will be charged $101.99 in total for 2 items with Visa ending 0303."
    }
   ],
   "buttons": [
    {
     "label": "Place order",
     "do": "act:place_order",
     "primary": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Order placed",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Thank you. Your order {ref} for 2 items was placed. A confirmation email is on its way."
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
  "place_order": {
   "requires_view": "review",
   "receipt_view": "receipt",
   "ref": "FG-318204"
  }
 },
 "prefix": "ev137",
 "mounts": [
  {
   "id": "dx-page-set",
   "default_view": "set"
  }
 ],
 "pages": {
  "set": {
   "file": "set.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

;(function () {
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button[aria-label="Scroll forward"]');
    if (!b) return;
    var t = b.previousElementSibling;
    if (!t || t.scrollWidth <= t.clientWidth) return;
    e.preventDefault();
    var end = t.scrollWidth - t.clientWidth;
    var to = t.scrollLeft >= end - 2 ? 0 : Math.min(end, t.scrollLeft + Math.round(t.clientWidth * 0.8));
    t.scrollTo({left: to, behavior: 'instant'});
  });
})();
