window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "terms": {
   "title": "Redelivery fee terms",
   "blocks": [
    {
     "id": "dx-terms-text",
     "text": "The fee covers one redelivery attempt. It is charged to the card you choose and refunded if the attempt fails."
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
     "text": "Your saved card will be charged once. You can cancel the redelivery up to one hour before the slot."
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
 "prefix": "pkokparcel01",
 "mounts": [],
 "pages": {},
 "leave_links": true,
 "dismiss": [],
 "text": {}
};
