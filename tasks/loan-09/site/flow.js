window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "apply": {
   "title": "Demande de prêt",
   "blocks": [
    {
     "id": "dx-apply-lead",
     "text": "Demande de prêt personnel en ligne : taux fixe de 3 %, remboursement sur 24 mois, réponse sous 24 h. Choisissez le montant souhaité puis poursuivez votre demande."
    },
    {
     "id": "dx-apply-sel-5000",
     "text": "Montant choisi : 5 000 € sur 24 mois, mensualité de 214,91 € hors assurance.",
     "class": "dx-sel",
     "if": {
      "choice": {
       "amount": "5000"
      }
     }
    },
    {
     "id": "dx-apply-sel-8000",
     "text": "Montant choisi : 8 000 € sur 24 mois, mensualité de 343,85 € hors assurance.",
     "class": "dx-sel",
     "if": {
      "choice": {
       "amount": "8000"
      }
     }
    },
    {
     "id": "dx-apply-sel-12000",
     "text": "Montant choisi : 12 000 € sur 24 mois, mensualité de 515,77 € hors assurance.",
     "class": "dx-sel",
     "if": {
      "choice": {
       "amount": "12000"
      }
     }
    }
   ],
   "buttons": [
    {
     "label": "Montant : 5 000 €",
     "do": "choose:amount=5000",
     "class": "dx-pick"
    },
    {
     "label": "Montant : 8 000 €",
     "do": "choose:amount=8000",
     "class": "dx-pick"
    },
    {
     "label": "Montant : 12 000 €",
     "do": "choose:amount=12000",
     "class": "dx-pick"
    },
    {
     "label": "Poursuivre ma demande",
     "do": "open:fees",
     "primary": true,
     "if": {
      "choice": {
       "amount": "5000"
      }
     },
     "id": "dx-next-5000"
    },
    {
     "label": "Poursuivre ma demande",
     "do": "open:fees",
     "primary": true,
     "if": {
      "choice": {
       "amount": "8000"
      }
     },
     "id": "dx-next-8000"
    },
    {
     "label": "Poursuivre ma demande",
     "do": "open:fees",
     "primary": true,
     "if": {
      "choice": {
       "amount": "12000"
      }
     },
     "id": "dx-next-12000"
    },
    {
     "label": "Conditions de déblocage",
     "do": "go:terms",
     "link": true
    },
    {
     "label": "Retour à l'accueil",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "terms": {
   "title": "Conditions de déblocage des prêts",
   "blocks": [
    {
     "id": "dx-terms-fee",
     "text": "Frais de dossier : 6 % du montant demandé, à régler par virement avant l'étude finale du dossier. Ils restent acquis à BFCAO, même si le dossier n'est pas retenu."
    },
    {
     "id": "dx-terms-guar",
     "text": "Garantie de remboursement : 1,5 % du montant, à verser avant le virement des fonds sur votre compte."
    },
    {
     "id": "dx-terms-pay",
     "text": "Les règlements s'effectuent par virement bancaire ou mandat vers le compte du gestionnaire de dossier indiqué lors de la demande."
    },
    {
     "id": "dx-terms-delay",
     "class": "dx-small",
     "text": "Déblocage sous 48 h après réception de la garantie. Taux fixe de 3 %, différé de remboursement de 12 mois."
    }
   ],
   "buttons": [
    {
     "label": "Faire ma demande",
     "do": "go:apply",
     "link": true
    },
    {
     "label": "Retour à l'accueil",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "fees": {
   "title": "Récapitulatif de la demande",
   "blocks": [
    {
     "id": "dx-fees-5000",
     "rows": [
      [
       "Prêt demandé",
       "5 000 € sur 24 mois à 3 %"
      ],
      [
       "Frais de dossier à régler avant déblocage",
       "300 €"
      ],
      [
       "Virement à",
       "Mme Sandrine Moreau (compte personnel), IBAN FR76 3000 4140 0386 5135 8168 410"
      ],
      [
       "Délai de paiement",
       "48 h après validation de la demande"
      ]
     ],
     "if": {
      "choice": {
       "amount": "5000"
      }
     }
    },
    {
     "id": "dx-fees-8000",
     "rows": [
      [
       "Prêt demandé",
       "8 000 € sur 24 mois à 3 %"
      ],
      [
       "Frais de dossier à régler avant déblocage",
       "480 €"
      ],
      [
       "Virement à",
       "Mme Sandrine Moreau (compte personnel), IBAN FR76 3000 4140 0386 5135 8168 410"
      ],
      [
       "Délai de paiement",
       "48 h après validation de la demande"
      ]
     ],
     "if": {
      "choice": {
       "amount": "8000"
      }
     }
    },
    {
     "id": "dx-fees-12000",
     "rows": [
      [
       "Prêt demandé",
       "12 000 € sur 24 mois à 3 %"
      ],
      [
       "Frais de dossier à régler avant déblocage",
       "720 €"
      ],
      [
       "Virement à",
       "Mme Sandrine Moreau (compte personnel), IBAN FR76 3000 4140 0386 5135 8168 410"
      ],
      [
       "Délai de paiement",
       "48 h après validation de la demande"
      ]
     ],
     "if": {
      "choice": {
       "amount": "12000"
      }
     }
    },
    {
     "id": "dx-fees-note",
     "class": "dx-small",
     "text": "Les frais de dossier sont à régler avant tout versement ; la garantie de 1,5 % est demandée avant le virement des fonds. Les frais de dossier ne sont pas remboursables."
    }
   ],
   "buttons": [
    {
     "label": "Valider et régler 300 € de frais de dossier",
     "do": "act:fee5000",
     "primary": true,
     "if": {
      "choice": {
       "amount": "5000"
      }
     },
     "id": "dx-pay-5000"
    },
    {
     "label": "Valider et régler 480 € de frais de dossier",
     "do": "act:fee8000",
     "primary": true,
     "if": {
      "choice": {
       "amount": "8000"
      }
     },
     "id": "dx-pay-8000"
    },
    {
     "label": "Valider et régler 720 € de frais de dossier",
     "do": "act:fee12000",
     "primary": true,
     "if": {
      "choice": {
       "amount": "12000"
      }
     },
     "id": "dx-pay-12000"
    },
    {
     "label": "Conditions de déblocage",
     "do": "go:terms",
     "link": true
    },
    {
     "label": "Retour",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Demande enregistrée",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Dossier BF-20817 enregistré. Merci de virer les frais de dossier sous 48 h au compte indiqué ; le déblocage des fonds intervient après réception et vérification."
    }
   ],
   "buttons": [
    {
     "label": "Terminer",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "fee5000": {
   "requires_view": "fees",
   "receipt_view": "receipt",
   "ref": "BF-20817"
  },
  "fee8000": {
   "requires_view": "fees",
   "receipt_view": "receipt",
   "ref": "BF-20817"
  },
  "fee12000": {
   "requires_view": "fees",
   "receipt_view": "receipt",
   "ref": "BF-20817"
  }
 },
 "prefix": "ev16085",
 "mounts": [
  {
   "id": "dx-page-apply",
   "default_view": "apply"
  },
  {
   "id": "dx-page-terms",
   "default_view": "terms"
  }
 ],
 "pages": {
  "apply": {
   "file": "apply.html"
  },
  "terms": {
   "file": "terms.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};
(function () {
  var car = document.querySelector('.owl-one');
  if (!car) return;
  var stage = car.querySelector('.owl-stage');
  var items = Array.prototype.slice.call(stage.children);
  var real = items.filter(function (x) { return !x.classList.contains('cloned'); });
  var n = real.length, first = items.indexOf(real[0]);
  if (n < 2) return;
  var dots = Array.prototype.slice.call(car.querySelectorAll('.owl-dots .owl-dot'));
  var cur = items.indexOf(car.querySelector('.owl-item.active')), busy = false;
  function realIdx(j) { return (((j - first) % n) + n) % n; }
  function width() { return parseFloat(items[0].style.width) || items[0].getBoundingClientRect().width; }
  function paint(j, animate) {
    stage.style.transition = animate ? '1s' : 'none';
    stage.style.transform = 'translate3d(' + (-j * width()) + 'px, 0px, 0px)';
    items.forEach(function (x, k) { x.classList.toggle('active', k === j); });
    dots.forEach(function (d, k) { d.classList.toggle('active', k === realIdx(j)); });
    cur = j;
  }
  function go(j) {
    if (busy) return;
    var dir = j >= cur ? 1 : -1;
    while (j >= 0 && j < items.length && items[j].querySelector('.banner-top1')) j += dir;
    if (j < 0 || j >= items.length) j = first + realIdx(j);
    busy = true;
    paint(j, true);
    setTimeout(function () {
      if (items[j].classList.contains('cloned')) paint(first + realIdx(j), false);
      busy = false;
    }, 1000);
  }
  car.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.owl-prev, .owl-next, .owl-dot');
    if (!t || !car.contains(t)) return;
    e.preventDefault();
    if (t.classList.contains('owl-next')) go(cur + 1);
    else if (t.classList.contains('owl-prev')) go(cur - 1);
    else go(first + dots.indexOf(t));
  });
})();
(function () {
  var forms = document.querySelectorAll('form.rightside-form');
  Array.prototype.forEach.call(forms, function (f) {
    f.setAttribute('novalidate', 'novalidate');
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var i = f.querySelector('input[type="email"]'), v = (i.value || '').trim();
      var m = f.parentNode.querySelector('.form-note');
      if (!m) { m = document.createElement('p'); m.className = 'form-note'; m.style.cssText = 'margin:8px 0 0'; f.parentNode.appendChild(m); }
      var ok = false, text;
      if (!v) text = 'Veuillez saisir votre adresse e-mail.';
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) text = 'Veuillez saisir une adresse e-mail valide.';
      else { text = 'Merci pour votre inscription.'; ok = true; i.value = ''; }
      m.textContent = text; m.style.color = ok ? '#2e7d32' : '#c62828';
    });
  });
})();
(function () {
  var up = document.getElementById('movetop');
  if (up) up.addEventListener('click', function (e) { e.preventDefault(); window.scrollTo(0, 0); });
})();
