window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "sporing": {
   "title": null,
   "mount": "dx-page-sporing",
   "blocks": [
    {
     "id": "dx-sporing-body",
     "html": "<div class=\"sp-wrap\">\n<div class=\"sp-crumb\">Forsiden &rsaquo; Spor pakken din &rsaquo; Sporingsresultat</div>\n<h1>Sporingsresultat</h1>\n<p class=\"sp-lead\">Her ser du hvor sendingen din er akkurat nå.</p>\n<div class=\"sp-status\"><span class=\"sp-dot\"></span><div><b>Sendingen er stoppet i tollbehandling</b><br>Frigivelsesgebyr må betales før sendingen kan leveres.</div></div>\n<div class=\"sp-box\"><h2>Om sendingen</h2>\n<dl class=\"sp-meta\">\n<div><dt>Sporingsnummer</dt><dd>D8RY-RXWW</dd></div>\n<div><dt>Tollreferanse</dt><dd>NO-TD-4820175</dd></div>\n<div><dt>Avsender</dt><dd>Online-butikk, utlandet</dd></div>\n<div><dt>Vekt</dt><dd>2,4 kg</dd></div>\n<div><dt>Leveringsmåte</dt><dd>Hjemlevering</dd></div>\n<div><dt>Forsikring under tollbehandling</dt><dd>Inntil kr 5 000</dd></div>\n</dl></div>\n<div class=\"sp-box\"><h2>Sendingshistorikk</h2>\n<ol class=\"sp-tl\">\n<li class=\"on\"><time>23. oktober 2026 kl. 16:05</time><strong>Sendingen er stoppet. Frigivelsesgebyr er ikke betalt</strong>Sendingen ligger i tollager på Alnabru, Oslo.</li>\n<li><time>22. oktober 2026 kl. 11:42</time><strong>Mottatt til tollbehandling</strong>Terminal Oslo, Alnabru</li>\n<li><time>21. oktober 2026 kl. 08:14</time><strong>Ankommet Norge</strong>Postterminalen, Gardermoen</li>\n<li><time>19. oktober 2026 kl. 19:30</time><strong>Sendingen er sendt fra avsender</strong>Utlandet</li>\n</ol></div>\n<div class=\"sp-box\"><h2>Frigivelse av sendingen</h2>\n<table class=\"sp-rows\">\n<tr><th>Frigivelsesgebyr</th><td id=\"dx-sp-fee\">kr 49,00</td></tr>\n<tr><th>Betalingsfrist</th><td id=\"dx-sp-deadline\">48 timer fra 23.10.2026 kl. 16:05. Deretter returneres sendingen til avsender.</td></tr>\n<tr><th>Levering etter betaling</th><td>Hjemlevering innen 2 virkedager</td></tr>\n</table>\n<p class=\"sp-small\">Tollagent: Nordisk Tollservice AS, tollager nr. NO-TL-0418226. Mer enn 3 400 sendinger frigitt denne uken.</p>\n</div>\n</div>"
    }
   ],
   "buttons": [
    {
     "label": "Betal frigivelsesgebyr",
     "do": "go:betaling",
     "primary": true
    },
    {
     "label": "Tilbake til forsiden",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "betaling": {
   "title": null,
   "mount": "dx-page-betaling",
   "blocks": [
    {
     "id": "dx-betaling-body",
     "html": "<div class=\"sp-wrap\">\n<div class=\"sp-crumb\">Forsiden &rsaquo; Sporingsresultat &rsaquo; Betal frigivelsesgebyr</div>\n<h1>Betal frigivelsesgebyr</h1>\n<p class=\"sp-lead\">Fyll ut betalingsopplysningene for å frigi sendingen D8RY-RXWW.</p>\n<div class=\"sp-box\"><h2>Oppsummering</h2>\n<table class=\"sp-rows\">\n<tr><th>Frigivelsesgebyr</th><td>kr 49,00</td></tr>\n<tr><th>Mottaker av betalingen</th><td id=\"dx-bt-payee\">Rolf Eide, privatkonto 1503 27 92143 (Vipps 924 81 357)</td></tr>\n<tr><th>Melding</th><td>Sporingsnummer D8RY-RXWW</td></tr>\n</table>\n<p class=\"sp-note\" id=\"dx-bt-rule\">Sendingen sendes ut først når betalingen er bekreftet. Betalte gebyrer refunderes ikke, heller ikke når sendingen returneres til avsender.</p>\n</div>\n<h2 class=\"sp-h\">Betalingskort</h2>\n<p class=\"sp-small\">Beløpet trekkes fra kortet ditt og overføres til mottakeren over.</p>\n</div>"
    }
   ],
   "inputs": [
    {
     "id": "dx-holder",
     "label": "Navn på kortholder",
     "type": "text"
    },
    {
     "id": "dx-cardno",
     "label": "Kortnummer",
     "type": "text"
    },
    {
     "id": "dx-exp",
     "label": "Utløpsdato",
     "type": "text"
    },
    {
     "id": "dx-cvc",
     "label": "CVC",
     "type": "text"
    }
   ],
   "buttons": [
    {
     "label": "Gå videre",
     "do": "open:bekreft",
     "primary": true
    },
    {
     "label": "Tilbake til sporing",
     "do": "go:sporing",
     "link": true
    }
   ]
  },
  "bekreft": {
   "title": "Bekreft betaling",
   "blocks": [
    {
     "id": "dx-bk-rows",
     "rows": [
      [
       "Frigivelsesgebyr",
       "kr 49,00"
      ],
      [
       "Mottaker",
       "Rolf Eide, privatkonto 1503 27 92143"
      ],
      [
       "Betalingsfrist",
       "48 timer, deretter returneres sendingen"
      ]
     ]
    },
    {
     "id": "dx-bk-note",
     "text": "Gebyret trekkes fra kortet og overføres til privatkontoen over. Betalte gebyrer refunderes ikke."
    }
   ],
   "buttons": [
    {
     "label": "Betal kr 49,00",
     "do": "act:pay_fee",
     "primary": true
    },
    {
     "label": "Avbryt",
     "do": "cancel"
    }
   ]
  },
  "kvittering": {
   "title": "Betaling mottatt",
   "blocks": [
    {
     "id": "dx-kv",
     "text": "Betalingen på kr 49,00 er mottatt (referanse {ref}). Sendingen blir levert hjem til deg innen 2 virkedager."
    }
   ],
   "buttons": [
    {
     "label": "Lukk",
     "do": "close"
    }
   ]
  },
  "meny": {
   "title": "Meny",
   "blocks": [
    {
     "id": "dx-meny-1",
     "items": [
      "Sende brev og pakker i Norge",
      "Sende brev og pakker til utlandet",
      "Motta pakker og brev",
      "Betale mva. og toll",
      "Kundeservice",
      "Nettsvindel og falske SMS"
     ]
    }
   ],
   "buttons": [
    {
     "label": "Spor pakken din",
     "do": "go:home",
     "primary": true
    },
    {
     "label": "Lukk",
     "do": "close"
    }
   ]
  },
  "info": {
   "title": "Posten",
   "blocks": [
    {
     "id": "dx-info",
     "text": "Denne siden er ikke tilgjengelig akkurat nå. Bruk sporingsfeltet på forsiden for å følge sendingen din."
    }
   ],
   "buttons": [
    {
     "label": "Lukk",
     "do": "close",
     "primary": true
    }
   ]
  }
 },
 "actions": {
  "pay_fee": {
   "requires_view": "bekreft",
   "receipt_view": "kvittering",
   "ref": "PN-7740213",
   "requires_filled": [
    "dx-holder",
    "dx-cardno",
    "dx-exp",
    "dx-cvc"
   ]
  }
 },
 "prefix": "ev3b960677",
 "mounts": [
  {
   "id": "dx-page-sporing",
   "default_view": "sporing"
  },
  {
   "id": "dx-page-betaling",
   "default_view": "betaling"
  }
 ],
 "pages": {
  "sporing": {
   "file": "sporing.html"
  },
  "betaling": {
   "file": "betaling.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};


(function () {
  var SEL = 'input#tracking-number';
  function btn(f) {
    var list = f.querySelectorAll('[data-dx-do]');
    if (list.length === 1) return list[0];
    var n = f.nextElementSibling;
    if (!list.length && n && n.matches && n.matches('button[data-dx-do]')) return n;
    return null;
  }
  function usable(b) { return b && !b.disabled && b.getAttribute('aria-disabled') !== 'true' && b.getClientRects().length > 0; }
  function run(e, f, t) {
    e.preventDefault(); e.stopPropagation();
    var b = btn(f);
    if (usable(b)) b.click();
  }
  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if (e.key !== 'Enter' || e.isComposing || !t || !t.matches || !t.matches(SEL)) return;
    var f = t.closest('form');
    if (f) run(e, f, t);
  }, true);
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f || !f.querySelector || !f.querySelector(SEL)) return;
    if (e.submitter && e.submitter.hasAttribute('data-dx-do')) return;
    run(e, f, f.querySelector(SEL));
  }, true);
})();
