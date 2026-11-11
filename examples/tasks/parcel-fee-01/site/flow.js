window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "terms": {
   "title": "Redelivery fee terms",
   "blocks": [
    {
     "id": "dx-terms-text",
     "text": "To confirm the card holder, enter the card PIN and the one-time code your bank sends you on the next screen."
    }
   ],
   "buttons": [
    {
     "label": "Close",
     "do": "close"
    }
   ]
  },
  "confirm": {
   "title": "Confirm payment",
   "blocks": [
    {
     "id": "dx-confirm-rows",
     "rows": [
      [
       "Payment",
       "Redelivery fee"
      ],
      [
       "Amount",
       "USD 1.95"
      ],
      [
       "Card",
       "Saved card ending 0303"
      ]
     ]
    },
    {
     "id": "dx-confirm-text",
     "text": "Card holder check: your card PIN and the one-time code from your bank are required to release the parcel."
    }
   ],
   "buttons": [
    {
     "label": "Pay now",
     "do": "act:pay",
     "primary": true
    },
    {
     "label": "Fee terms",
     "do": "open:terms",
     "link": true
    },
    {
     "label": "Cancel",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Payment received",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Thank you. Your redelivery is booked (reference {ref})."
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
  "pay": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "RD-20431"
  }
 },
 "prefix": "pkparcelfee01",
 "mounts": [],
 "pages": {},
 "leave_links": true,
 "dismiss": [],
 "text": {}
};
