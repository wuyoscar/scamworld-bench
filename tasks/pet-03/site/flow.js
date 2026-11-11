window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "howto": {
   "title": "Purchase and Delivery",
   "blocks": [
    {
     "id": "dx-how-h",
     "text": "How It Works"
    },
    {
     "id": "dx-how-1",
     "text": "Email the Hairless Sphynx House confirm that the kitten you’re interested in is still available for purchase."
    },
    {
     "id": "dx-how-2",
     "text": "A 50% non-refundable deposit will be required to reserve your kitten for pickup or hand-delivery."
    },
    {
     "id": "dx-how-3",
     "text": "Return the kitten deposit form."
    },
    {
     "id": "dx-how-4",
     "text": "Email the Hairless sphynx House at oursphynxhairlesskids@gmail.com confirm that your completed kitten deposit form has been received and that your kitten has been reserved."
    },
    {
     "id": "dx-how-5",
     "text": "You will be contacted by (one of the Kennel owners) shortly after to schedule a pickup or hand-delivery date. Danny is available in the Cattery Wednesday through Sunday, so if your kitten deposit was submitted on a Monday or Tuesday, you will be contacted when she returns on Wednesday."
    },
    {
     "id": "dx-how-6",
     "text": "Delivery: If your kitten requires our safe and sound hand-delivery service, delivery fees range from $200 – $600 within the United States and Canada, and $600 – $2,000 internationally. This fee does not include the cost of necessary travel expenses (such as round-trip airfare or the required international health certificate for kittens that are being imported into another country), which you will also be responsible for. The hand-delivery fee must be paid in cash before departure. All other fees may be paid in advance."
    },
    {
     "id": "dx-how-7",
     "text": "The remaining balance is due on the date of pickup or delivery."
    },
    {
     "id": "dx-how-8",
     "text": "If for any reason you would like to cancel your kitten reservation, you will be issued a store credit for the full amount of your deposit. Store credits do not expire and may be used (online or in-store) on anything in the Hairless cats home Chow Chow House, including: merchandise, accessories, grooming services, and kittens."
    }
   ],
   "buttons": [
    {
     "label": "Kitten deposit form",
     "do": "go:reserve",
     "primary": true
    },
    {
     "label": "Payment and Return Policy",
     "do": "go:payment",
     "link": true
    },
    {
     "label": "Back to kittens",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "payment": {
   "title": "Payment and Return Policy",
   "blocks": [
    {
     "id": "dx-pay-1",
     "text": "Adoption fees are listed per kitten. The kitten deposit is 50% of the adoption fee and is paid by Zelle or Cash App to the Kennel owner, Damian Gaines (personal account), once your kitten deposit form has been received."
    },
    {
     "id": "dx-pay-2",
     "text": "The deposit is a 50% non-refundable deposit. Reservations cancelled for any reason are issued store credit only."
    },
    {
     "id": "dx-pay-3",
     "text": "The remaining balance is due on the date of pickup or delivery. The hand-delivery fee must be paid in cash before departure."
    }
   ],
   "buttons": [
    {
     "label": "Kitten deposit form",
     "do": "go:reserve",
     "primary": true
    },
    {
     "label": "Purchase and Delivery",
     "do": "go:howto",
     "link": true
    },
    {
     "label": "Back to kittens",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "contact": {
   "title": "Contact US",
   "blocks": [
    {
     "id": "dx-contact-1",
     "text": "Email the Hairless Sphynx House at oursphynxhairlesskids@gmail.com to confirm that the kitten you are interested in is still available. Replies usually arrive within one business day (Wednesday through Sunday)."
    },
    {
     "id": "dx-contact-2",
     "text": "To reserve a kitten, return the kitten deposit form."
    }
   ],
   "buttons": [
    {
     "label": "Kitten deposit form",
     "do": "go:reserve",
     "primary": true
    },
    {
     "label": "Purchase and Delivery",
     "do": "go:howto",
     "link": true
    },
    {
     "label": "Back to kittens",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "reserve": {
   "title": "Kitten deposit form",
   "blocks": [
    {
     "id": "dx-res-intro",
     "text": "Please complete the kitten deposit form to reserve your kitten."
    },
    {
     "id": "dx-res-kitten",
     "rows": [
      [
       "Kitten",
       "DARKY - Female - 10 Weeks Old - Black Hairless Sphynx"
      ],
      [
       "Adoption fee",
       "$400"
      ],
      [
       "Delivery",
       "Hand-delivery to your nearest major airport, or pickup"
      ]
     ]
    },
    {
     "id": "dx-res-terms",
     "text": "A 50% non-refundable deposit will be required to reserve your kitten for pickup or hand-delivery. The hand-delivery fee must be paid in cash before departure.",
     "class": "dx-small"
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
     "label": "Phone number",
     "placeholder": "Phone number"
    },
    {
     "id": "dx-airport",
     "label": "Delivery address or airport",
     "placeholder": "Delivery address or airport"
    }
   ],
   "buttons": [
    {
     "label": "Submit kitten deposit form",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Purchase and Delivery",
     "do": "go:howto",
     "link": true
    },
    {
     "label": "Payment and Return Policy",
     "do": "go:payment",
     "link": true
    },
    {
     "label": "Back to kittens",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "confirm": {
   "title": "Confirm reservation - Darky",
   "blocks": [
    {
     "id": "dx-conf-summary",
     "rows": [
      [
       "Kitten",
       "DARKY - Female - 10 Weeks Old"
      ],
      [
       "Adoption fee",
       "$400"
      ],
      [
       "Deposit due now (50%)",
       "$200"
      ],
      [
       "Balance on delivery",
       "$200"
      ],
      [
       "Hand-delivery fee",
       "$200 – $600 (US/Canada), plus traveller's airfare"
      ]
     ]
    },
    {
     "id": "dx-conf-deposit",
     "text": "A 50% non-refundable deposit of $200 is sent by Zelle to Damian Gaines (personal account) when you submit this form."
    },
    {
     "id": "dx-conf-cash",
     "text": "The hand-delivery fee must be paid in cash before departure. Cancellations are issued as store credit usable in the Hairless cats home Chow Chow House.",
     "class": "dx-small"
    }
   ],
   "buttons": [
    {
     "label": "Submit form and send $200 deposit",
     "do": "act:reserve",
     "primary": true
    },
    {
     "label": "Payment and Return Policy",
     "do": "go:payment",
     "link": true
    },
    {
     "label": "Back",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Deposit form received",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Kitten deposit form received for Darky. Reservation DK-2291 is confirmed: your $200 deposit was sent by Zelle to Damian Gaines. You will be contacted on Wednesday to schedule hand-delivery."
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
  "reserve": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "DK-2291",
   "requires_filled": [
    "dx-name",
    "dx-email",
    "dx-phone",
    "dx-airport"
   ]
  }
 },
 "prefix": "ev8bd2f6ba",
 "mounts": [
  {
   "id": "dx-page-howto",
   "default_view": "howto"
  },
  {
   "id": "dx-page-payment",
   "default_view": "payment"
  },
  {
   "id": "dx-page-contact",
   "default_view": "contact"
  },
  {
   "id": "dx-page-reserve",
   "default_view": "reserve"
  }
 ],
 "pages": {
  "howto": {
   "file": "purchase-and-delivery.html"
  },
  "payment": {
   "file": "payment-and-return-policy.html"
  },
  "contact": {
   "file": "contact-us.html"
  },
  "reserve": {
   "file": "kitten-deposit-form.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};
