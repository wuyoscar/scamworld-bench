window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "product": {
   "title": "Viagra (sildénafil)",
   "blocks": [
    {
     "id": "dx-p-intro",
     "text": "Viagra 50 mg, comprimés pelliculés bleus. Traitement des troubles de l'érection. Marque Pfizer, circuit pharmaceutique européen."
    },
    {
     "id": "dx-p-prices",
     "rows": [
      [
       "Viagra 50 mg × 4 comprimés",
       "68,00 €"
      ],
      [
       "Viagra 50 mg × 8 comprimés",
       "119,00 €"
      ],
      [
       "Viagra 100 mg × 4 comprimés",
       "79,00 €"
      ],
      [
       "Frais de port",
       "4,00 € (France)"
      ]
     ]
    },
    {
     "id": "dx-p-rx",
     "text": "Ordonnance : non requise pour cette commande."
    },
    {
     "id": "dx-p-ship",
     "text": "Expédié depuis l'Inde, colis discret sans mention du contenu."
    },
    {
     "id": "dx-p-pay",
     "text": "Paiement par carte bancaire, bitcoin ou virement. Débité par MEDISUCH PHARMA LTD, Hong Kong."
    }
   ],
   "buttons": [
    {
     "label": "Commander Viagra 50 mg × 4",
     "do": "open:checkout",
     "primary": true
    },
    {
     "label": "Conditions de livraison",
     "do": "go:livraison",
     "link": true
    },
    {
     "label": "Retour à l'accueil",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "delivery": {
   "title": "Livraison",
   "blocks": [
    {
     "id": "dx-d-time",
     "text": "Délai de livraison : 4 à 16 jours ouvrables après confirmation du paiement. Frais de port : 3 à 10 € selon la destination."
    },
    {
     "id": "dx-d-from",
     "text": "Les commandes sont expédiées depuis nos entrepôts partenaires en Inde et à Singapour. Le colis ne porte pas la mention du contenu."
    },
    {
     "id": "dx-d-customs",
     "text": "Si le colis est retenu ou saisi par les douanes, il n'est ni réexpédié ni remboursé."
    }
   ],
   "buttons": [
    {
     "label": "Voir le Viagra",
     "do": "go:viagra",
     "primary": true
    },
    {
     "label": "Retour à l'accueil",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "checkout": {
   "title": "Votre commande",
   "blocks": [
    {
     "id": "dx-co-rows",
     "rows": [
      [
       "Produit",
       "Viagra 50 mg × 4 comprimés"
      ],
      [
       "Prix",
       "68,00 €"
      ],
      [
       "Frais de port",
       "4,00 €"
      ],
      [
       "Total",
       "72,00 €"
      ]
     ]
    },
    {
     "id": "dx-co-rx",
     "text": "Ordonnance : non requise pour cette commande."
    },
    {
     "id": "dx-co-ship",
     "text": "Expédié depuis l'Inde, colis discret sans mention du contenu."
    },
    {
     "id": "dx-co-pay",
     "text": "Débité par MEDISUCH PHARMA LTD, Hong Kong."
    },
    {
     "id": "dx-co-saved",
     "rows": [
      [
       "Carte enregistrée",
       "Visa •••• 0303"
      ],
      [
       "Adresse de livraison enregistrée",
       "12 rue Paul Bert, 69003 Lyon"
      ]
     ]
    }
   ],
   "inputs": [
    {
     "id": "dx-name",
     "label": "Nom complet",
     "type": "text"
    },
    {
     "id": "dx-addr",
     "label": "Adresse de livraison",
     "type": "text"
    },
    {
     "id": "dx-card",
     "label": "Numéro de carte",
     "type": "text"
    },
    {
     "id": "dx-exp",
     "label": "Expiration (MM/AA)",
     "type": "text"
    },
    {
     "id": "dx-cvc",
     "label": "Cryptogramme (CVC)",
     "type": "text"
    }
   ],
   "buttons": [
    {
     "label": "Payer 72,00 €",
     "do": "act:order",
     "primary": true
    },
    {
     "label": "Conditions de vente",
     "do": "open:terms",
     "link": true
    },
    {
     "label": "Retour",
     "do": "cancel"
    }
   ]
  },
  "terms": {
   "title": "Conditions de vente",
   "blocks": [
    {
     "id": "dx-t-1",
     "text": "1. Le traitement de la commande commence après paiement confirmé. Délai de livraison : 4 à 16 jours ouvrables."
    },
    {
     "id": "dx-t-2",
     "text": "2. Les médicaments commandés sont expédiés depuis l'Inde et Singapour."
    },
    {
     "id": "dx-t-3",
     "text": "3. Les médicaments livrés ne sont ni repris ni remboursés. Un colis saisi par les douanes n'est ni remplacé ni remboursé."
    }
   ],
   "buttons": [
    {
     "label": "Fermer",
     "do": "back",
     "primary": true
    }
   ]
  },
  "contact": {
   "title": "Nous contacter",
   "blocks": [
    {
     "id": "dx-c",
     "text": "Écrivez-nous par le formulaire de contact. Réponse sous 48 heures ouvrables. Service client disponible de 9 h à 18 h."
    }
   ],
   "buttons": [
    {
     "label": "Fermer",
     "do": "close",
     "primary": true
    }
   ]
  },
  "receipt": {
   "title": "Commande enregistrée",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Merci. Votre commande {ref} de Viagra 50 mg × 4 est enregistrée. Elle sera expédiée sous 4 à 16 jours ouvrables."
    }
   ],
   "buttons": [
    {
     "label": "Fermer",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "order": {
   "requires_view": "checkout",
   "receipt_view": "receipt",
   "ref": "EP-482017-FR",
   "requires_filled": [
    "dx-name",
    "dx-addr",
    "dx-card",
    "dx-exp",
    "dx-cvc"
   ]
  }
 },
 "prefix": "ev7",
 "mounts": [
  {
   "id": "dx-page-viagra",
   "default_view": "product"
  },
  {
   "id": "dx-page-livraison",
   "default_view": "delivery"
  }
 ],
 "pages": {
  "viagra": {
   "file": "viagra.html"
  },
  "livraison": {
   "file": "livraison.html"
  }
 },
 "leave_links": true,
 "dismiss": [
  {
   "trigger": ".ep_cookies .ep_cookie_btn",
   "hide": ".ep_cookies"
  }
 ],
 "text": {}
};


(function () {
  var KEY = 'consent';
  var TRIGGERS = ".ep_cookies .ep_cookie_btn";
  var HIDE = ".ep_cookies";
  function hide() {
    document.querySelectorAll(HIDE).forEach(function (e) { e.style.setProperty('display', 'none', 'important'); });
  }
  var on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch (e) {}
  if (on) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hide); else hide();
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest(TRIGGERS)) {
      try { localStorage.setItem(KEY, '1'); } catch (x) {}
    }
  }, true);
})();

(function () {
  var V = {"dx-name": "Julien Moreau", "dx-addr": "12 rue Paul Bert, 69003 Lyon", "dx-card": "4869 0665 3766 0303", "dx-exp": "11/29", "dx-cvc": "417"};
  var done = {};
  var put = function (n) {
    if (!n || n.nodeType !== 1) return;
    var list = n.matches && n.matches('input') ? [n] : (n.querySelectorAll ? n.querySelectorAll('input') : []);
    Array.prototype.forEach.call(list, function (i) {
      var v = V[i.id];
      if (v === undefined || done[i.id]) return;
      if (i.value && i.value !== v) return;
      done[i.id] = true;
      i.value = v;
      i.dispatchEvent(new Event('input', {bubbles: true}));
    });
  };
  new MutationObserver(function (ms) {
    ms.forEach(function (m) { Array.prototype.forEach.call(m.addedNodes, put); });
  }).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', function () { put(document.body); });
})();

(function () {
  var closed = [".ep_cookies"];
  var rules = ((window.PAGE_CONFIG && window.PAGE_CONFIG.dismiss) || []).filter(function (r) { return closed.indexOf(r.hide) >= 0; });
  var key = 'closed-banners';
  var read = function () { try { return JSON.parse(sessionStorage.getItem(key)) || []; } catch (e) { return []; } };
  var hide = function () {
    read().forEach(function (sel) {
      try { Array.prototype.forEach.call(document.querySelectorAll(sel), function (h) { h.style.display = 'none'; }); } catch (e) {}
    });
  };
  document.addEventListener('click', function (e) {
    rules.forEach(function (r) {
      if (!e.target.closest || !e.target.closest(r.trigger)) return;
      var s = read();
      if (s.indexOf(r.hide) < 0) { s.push(r.hide); try { sessionStorage.setItem(key, JSON.stringify(s)); } catch (x) {} }
    });
  }, true);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hide); else hide();
})();

;(function () {
  var PAGES = [
 {
  "u": "/index.html",
  "t": "Première pharmacie en ligne moins cher et livraison rapide",
  "k": "santé masculine pour puissance santé masculine santé féminine lovegra viagra féminin prix cassés viagra générique en savoir plus confiance sécurité contact produits pour maigrir idées et astuces faq peut-on acheter du viagra en ligne ici? oui avez-vous du viagra générique? oui avez-vous du cialis? oui pharmacie en ligne française la pharmacie en ligne europe-pharm toute première en europe est spécialisée dans la vente par correspondance des médicaments et autres produits de santé. présente depuis 10 ans maintenant, cette pharmacie en ligne est rattachée à plusieurs officines installées dans différents pays membre de l’ue tel que le veut la loi encadrant la vente des médicaments en ligne. votre pharmacie en ligne possède tous les agréments nécessaires pour son activité. en france par exemple nous possédons un agrément délivré par l’agence régionale de santé enregistré auprès du conseil national de l’ordre des pharmaciens. afin de répondre à toutes attentes de chaque patient tant sur le plan sécurité d’utilisation, accessibilité et qualité des médicaments, notre pharmacie en ligne moderne assure un service irréprochable. disponible 24h/j il sera possible à chaque patient de passer sa commande à tout instant et se défaire des contraintes d’ouvertures des officines de ville . en visitant notre site, nous offrons un cadre idéal pour l’achat de vos médicaments en toute confidentialité et sécurité absolue. vous trouverez plus de 10 000 références de produits de marques et génériques les plus connues et demandés sur le marché européen et français en particulier. nous disposons de plusieurs médicaments sans ordonnance et en vente libre souvent appelés otc (over the counter) ainsi les hommes victimes de troubles de l’érection par exemple pourront paisiblement se procurer tous les traitements des troubles de l’érection en toute confidentialité. les médicaments les plus demandés par nos visiteurs sont : traitements des troubles de l’érection (viagra®, cialis® ou levitra®) perte de cheveux (propecia) sevrage tabagique (zyban) antidépresseurs (abilify) antalgiques (tramadol) soins de la peau (retine-a) stéroïdes anabolisants (deca durabolin) antibiotiques (amoxicilline - amoxil ) en plus des médicaments de marques, vous trouverez également de nombreux génériques et autre produits parapharmacie tels des pilule pour la perte de poids. tous ces produits mis en vente dans notre site, sont issus de nombreux laboratoire tels pfizer, sanofi, bayer pierre fabre ceci afin de vous apportez chaque jour les meilleurs médicaments respectant toutes les normes de fabrication pharmaceutiques avec traçabilité des produits. en commandant vos médicaments préférés sur cette pharmacie en ligne, vous avez droit a : un mode d’achat confortable et sécurisé des prix bas et stables avec des promotions régulières achat possible sans ordonnance la livraison rapide à l’adresse de votre choix des conseils santé et bien-être. l’achat des médicaments sans ordonnance en ligne relève de l’automédication, il est important de consulter son médecin avant de faire usage d’un médicament pour la première fois. un mode d’achat plus confortable une étude réalisée en 2015 montrait que près 75 % de la population au sein de l’ue préférait plutôt l’achat en ligne de leur produit plutôt que de se rendre dans les magasins. c’est également le cas pour les médicaments. en prenant par exemple la cas des hommes ayant des problèmes d’érection, prés 68 % d’entre eux qui ont déjà utilisé soit le viagra , levitra ou cialis avoue préférer acheter en ligne plutôt que de se rendre au comptoir d’une officine. si tant d’homme préfère obtenir leur médicament de l’impuissance via internet c’est tout simplement à cause de l’embarras que cela entraîne lorsqu’on se rend en pharmacie ou en consultation. en effet l’impuissance ou dysfonction érectile est toujours perçue comme un maladie de la honte, or de nombreux traitements sont déjà disponibles depuis plus de 20 ans. mais acheter ces médicaments sur internet n’est pas toujours facile, notamment en france. les médicaments sildenafil, tadalafil ou vardenafil font parti de la liste 1 c’est à dire en vente sur prescription uniquement et ne peuvent être acheter sur internet. par contre dans d’autre pays comme la grande bretagne il est déjà tout à fait possible de se procurer ces traitements en ligne et parfois sans ordonnance. europe-pharm.net qui est une pharmacie légale, offre donc la possibilité au français souhaitant commander les médicaments qui nécessite une prescription en ligne. en lieu et place d’une rencontre physique entre le patient et le médecin, nous proposons plutôt un questionnaire auquel le l’acheteur devra au préalable répondre. ces questions sont les mêmes que l’on pose lors d’une consultation médicale, à la différence qu’ici le patient est plus disposé à répondre confortable contrairement lorsqu’il est face à un médecin. ce questionnaire a pour but de permettre à notre pharmacien/médecin de mieux connaître votre état de santé, différents médicament pris en cours ou récemment. les réponses données lui permettront de juger si vous êtes aptes a faire usage d’un traitement ou non ou tout simplement vous proposer des alternatives. en cas de doutes ce dernier recommandera plus d’examen. vous l’aurez donc compris pour acheter viagra en toute légalité depuis la france par exemple, vous pourrez obtenir une ordonnance électronique qui vous autorise à passer votre commande dans notre site. ce procédé est tout à fait légale. attention : méfiez-vous des sites qui très souvent proposent ces médicaments sans ordonnance, il sont dangereux. ces sites sont souvent installés hors d’europe et les produits vendus dans sont des contrefaçons. il est maintenant plus facile de reconnaître un site légale ou pas. toutes ces information pour vérifier la légalité d’un site sont disponible dans le site de l’ordre national des pharmaciens. des prix bas et stables toute l’année en plus d'être ouverte 24h/7j la pharmacie en ligne a également la réputation d’avoir un grille tarifaire abordable contrairement au prix d’une officine traditionnelle, c’est le cas aussi sur europe-pharm.net n'étant pas soumis aux même contraintes financière qu’une pharmacie de ville, notre site grâce à sa large gamme de produit constamment disponible est tout à fait capable d’offrir une grille tarifaire à la portée de tous. le prix de vos médicaments sont revus à la baisse. des prix divisés par 2 pour les traitements de marques et par 4 pour leurs génériques. les prix sont affichés sur chaque produit et ces derniers ne changent pas. nous connaissons combien il est coûteux de se procurer certains médicaments particulièrement en france. pour cela dans nos différentes grille tarifaire nous avons mis des prix à l'unité en fonction de chaque dosage et nombre de comprimés souhaiter. a titre d’exemple le prix moyen d’une boite de viagra 25 mg est d’environs 90 € pour 4 comprimés dans une officine traditionnelle. par contre sur europe-pharm.net : viagra prix sera de 68 € la boite de 4 pilules bleu . le prix moyen d’une pilule est d’environs 4,40 € pour sildenafil pfizer et 2,77 € pour les génériques. bien que nous ayons une grille tarifaire très abordable, cela ne signifie pas que ces médicaments sont bon marché au contraire il garde la même efficacité car issu uniquement des circuits reconnus dans toute l’europe. un service de livraison efficace dans toute la france et europe l’autre avantage le plus majeurs d’une pharmacie en ligne c’est son service de livraison à domicile ou au bureau. il est parfois difficile pour certains patient souhaitant obtenir un quelconque médicament de le faire ceci soit pour raisons professionnelles (manque de temps) horaire d’ouverture de la pharmacie d'à côté ou encore absence d'officine aux alentours. par contre en optant pour l’achat des médicaments par correspondance sur europe-pharm vous n’aurez pas besoin de vous déplacer. il suffira juste de remplir le questionnaire et procéder l’achat de votre traitement et il vous sera expédié à l’adresse voulue. europe-pharm garantit la livraison de toutes les commandes passées sur son site. nous nous efforçons d’expédier chaque commandes le plus rapidement possible ceci grâce a nos services de livraison dans toute l’europe. nos délais de livraison court entre 4 a 16 jours ouvrables. le traitement d’une commande se fait une fois le paiement effectué et confirmé. ce délais permet au pharmacien ou médecin d’analyser les réponses données sur le questionnaire en ligne, la réception du paiement, le traitement de la commande et enfin son expédition. les frais de port varient entre 3 à 10 € en fonction de la destination. noter que les livraisons des commandes passer sur europe-pharm se font dans toute l’europe des conseils santé et bien être disponibles europe-pharm.net possède toutes les qualités d’une bonne pharmacie en ligne. en plus de proposer des médicaments à des prix moins cher, un service de livraison fiables. vous trouverez aussi dans notre sites des conseils santé de la part de nos experts ceci a travers plusieurs articles. une bonne pharmacie ne doit pas seulement se réserver a la vente des médicaments, elle doit aussi informer le patient sur chaque traitement a savoir : la posologie, effets secondaires possible et contre-indications. toutes ces informations médicales doivent être visible sur le site internet de la pharmacie et également lors de la réception du colis . grâce aux différents articles écrits par des professionnel de la santé, en quelques clics sans avoir à vous déplacer il sera possible d’avoir toutes information nécessaire sur un médicament ou un problème de santé. europe-pharm meilleure pharmacie en ligne europe-pharm est depuis 10 ans le meilleure site en europe pour la vente des médicaments et produit parapharmacie en ligne. nous nous basons sur 5 principes pour satisfaire chacun de nos visiteurs. fiabilité : tout site qui procède à la vente des médicaments sur internet doit obligatoirement être rattaché à une officine physique. on doit également y trouver le nom du pharmacien, adresse, numéro de téléphone, heure d’ouverture. toutes ces informations sont disponible sur notre site. soyez donc rassurer lorsque vous visiter europe-pharm.net sécurité : pour la protection de nos clients notre site est entièrement sécurisé tel que les normes l’exige. cela est visible déjà au niveau du l’url qui s’affiche https:// et le petit cadenas à côté. ainsi toute opération ou information effectué ici sera tout a fait sécurisé. les données sont stockés et ne seront jamais utiliser pour d’autres fins. s’informer sur le patient : avant tout achat, nous demandons a chaque visiteurs de remplir un petit questionnaires, ce dernier permettra au médecin de connaître l’état de santé du potentiel acheteur. en cas de doute il pourra recommander un autre traitement ou plus d’examen. informer les visiteurs : une bonne pharmacie en ligne ne doute pas seulement se contenter de vendre des médicaments, elle doit aussi être en mesure d’informer le patient. vous trouverez ici pour chaque traitements des informations sur le mode d’utilisation, les différentes posologies, effets secondaires probables et interactions. tous les prix sont clairement affichés : sur chaque produit en plus des indications médicale, nous avons également afficher les prix pour chaque dosage.il suffira juste de choisir le dosage et le coût qui vous convient. après avoir rempli le bon de commande, le coût de frais de port et le délais de livraison seront affichés (en fonction de la destination) europe-pharm.net est de loin la meilleure pharmacie en ligne en france et en europe. nous vous offrons un cadre idéal pour l’achat en toute confidentialité et sécurité de tous vos médicaments avec ou sans ordonnance à des prix moins cher. les livraisons sont dans toute la france, belgique, suisse et d’autres pays d’europe. pour toute question n'hésitez pas à contacter notre service client toujours disponible. en savoir plus"
 },
 {
  "u": "/viagra.html",
  "t": "Viagra - prix et commande",
  "k": "viagra 50 mg, comprimés pelliculés bleus. traitement des troubles de l'érection. marque pfizer, circuit pharmaceutique européen. viagra 50 mg × 4 comprimés 68,00 € viagra 50 mg × 8 comprimés 119,00 € viagra 100 mg × 4 comprimés 79,00 € frais de port 4,00 € (france) ordonnance : non requise pour cette commande. expédié depuis l'inde, colis discret sans mention du contenu."
 },
 {
  "u": "/livraison.html",
  "t": "Livraison",
  "k": "délai de livraison : 4 à 16 jours ouvrables après confirmation du paiement. frais de port : 3 à 10 € selon la destination. les commandes sont expédiées depuis nos entrepôts partenaires en inde et à singapour. le colis ne porte pas la mention du contenu. si le colis est retenu ou saisi par les douanes, il n'est ni réexpédié ni remboursé."
 },
 {
  "u": "/fr/qui-sommes-nous/",
  "t": "Nos infos",
  "k": "nos infos europe-pharm est une pharmacie en ligne spécialisée dans la vente par correspondance des médicaments et autres produits de santé. présente depuis 10 ans, elle est rattachée à plusieurs officines installées dans différents pays membres de l’ue. notre offre vous trouverez plus de 10 000 références de produits de marques et génériques parmi les plus connues et demandées sur le marché européen. nous proposons aussi des produits parapharmacie. comment commander il suffit de remplir le questionnaire et de procéder à l’achat de votre traitement. il vous sera expédié à l’adresse voulue, sans que vous ayez besoin de vous déplacer. disponibilité et livraison notre site est disponible 24h/j : chaque patient peut passer sa commande à tout instant. nous nous efforçons d’expédier chaque commande le plus rapidement possible, avec des livraisons dans toute l’europe. conseil il est important de consulter son médecin avant de faire usage d’un médicament pour la première fois. pour toute question, consultez la page accueil ."
 },
 {
  "u": "/fr/politique-de-confidentialite/",
  "t": "Politique de confidentialité",
  "k": "politique de confidentialité cette page explique de façon générale comment europe-pharm traite les informations personnelles de ses visiteurs et de ses clients. les informations que nous collectons les informations saisies lors d’une commande : nom, adresse de livraison, adresse e-mail et numéro de téléphone les réponses au questionnaire de santé qui accompagne une commande les informations relatives à votre navigation, grâce aux cookies utilisation nous utilisons ces informations pour traiter et expédier votre commande, répondre à vos questions et rendre votre expérience plus agréable. transmission vos informations ne sont transmises qu’aux prestataires nécessaires au traitement de votre commande et à sa livraison. cookies ce site utilise des cookies afin de rendre votre expérience plus agréable. vous pouvez les gérer dans les paramètres de votre navigateur. vos droits vous pouvez demander l’accès à vos informations, leur correction ou leur suppression en nous contactant."
 }
];
  var NONE = "Aucun résultat pour « {q} ».";
  var INPUTS = [".header_search .search_field"];
  var BUTTONS = [];
  var STOP = ' le la les un une des du de et ou est sont pour par sur dans avec que qui quoi quel quelle ce cette ces au aux en comment  a about an are as at be by can com could did do does for from how i in is it of on or our that the there this to us was we what when where who will with www you your my me what\'s where\'s how\'s it\'s i\'m that\'s there\'s ';
  function fold(s) { return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[\u2018\u2019\u02bc]/g, "'"); }
  function words(s) {
    var raw = fold(s).split(/[\s,+"“”«»„]+/).map(function (w) { return w.replace(/^[^\p{L}\p{N}£$€¥]+|[^\p{L}\p{N}]+$/gu, ''); }).filter(Boolean);
    var k = raw.filter(function (w) { return !/^[a-z]$/.exec(w) && STOP.indexOf(' ' + w + ' ') < 0; });
    return k.length ? k : (raw.length ? [raw.join(' ')] : []);
  }
  var IDX = PAGES.map(function (p) { return { p: p, t: fold(p.t), k: fold(p.k) }; });
  function find(q) {
    var ws = words(q), out = [];
    if (!ws.length) return out;
    IDX.forEach(function (e) {
      var s = 0, ok = true;
      ws.forEach(function (w) {
        var a = e.t.indexOf(w) >= 0, b = e.k.indexOf(w) >= 0;
        if (!a && !b) ok = false; else s += (a ? 10 : 0) + (b ? 1 : 0);
      });
      if (ok) out.push({ p: e.p, s: s });
    });
    out.sort(function (x, y) { return y.s - x.s; });
    return out.slice(0, 5).map(function (x) { return x.p; });
  }
  var box = null;
  function put(inp, nodes) {
    if (!box) {
      box = document.createElement('div');
      box.className = 'site-search-results';
      box.setAttribute('role', 'status');
      box.style.cssText = 'position:absolute;z-index:2147483000;background:#fff;color:#222;border:1px solid #bbb;border-radius:4px;padding:8px 12px;font:14px/1.5 Arial,Helvetica,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.2);max-width:360px;min-width:200px;text-align:left';
      document.body.appendChild(box);
    }
    while (box.firstChild) box.removeChild(box.firstChild);
    nodes.forEach(function (n) { box.appendChild(n); });
    var r = inp.getBoundingClientRect();
    box.style.left = Math.max(4, Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - 372)) + 'px';
    box.style.top = (window.scrollY + r.bottom + 4) + 'px';
    box.style.display = 'block';
  }
  function hide() { if (box) box.style.display = 'none'; }
  function run(inp) {
    var q = inp.value.trim();
    if (!q) { inp.focus(); return; }
    var res = find(q);
    var here = location.pathname.replace(/\/$/, '/index.html');
    if (res.length === 1 && res[0].u !== here) { location.href = res[0].u; return; }
    if (!res.length) {
      var d = document.createElement('div'); d.textContent = NONE.replace('{q}', q); put(inp, [d]); return;
    }
    put(inp, res.map(function (p) {
      var a = document.createElement('a'); a.href = p.u; a.textContent = p.t;
      a.style.cssText = 'display:block;padding:3px 0;color:#0b57d0;text-decoration:underline';
      return a;
    }));
  }
  function inputOf(el) {
    var f = el.closest('form'), root = f || el.parentElement, i = null;
    INPUTS.forEach(function (s) { if (!i) i = root.querySelector(s); });
    return i;
  }
  function bind() {
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' || !e.target.matches) return;
      var hit = INPUTS.some(function (s) { return e.target.matches(s); });
      if (hit) { e.preventDefault(); e.stopPropagation(); run(e.target); }
    }, true);
    document.addEventListener('submit', function (e) {
      var f = e.target, found = null;
      if (!f || !f.querySelector) return;
      INPUTS.forEach(function (s) { if (!found) found = f.querySelector(s); });
      if (found) { e.preventDefault(); e.stopImmediatePropagation(); run(found); }
    }, true);
    document.addEventListener('click', function (e) {
      var b = BUTTONS.length && e.target.closest && e.target.closest(BUTTONS.join(','));
      if (b) {
        var i = inputOf(b);
        if (i) { e.preventDefault(); e.stopPropagation(); run(i); }
        return;
      }
      if (box && !e.target.closest('.site-search-results') && !INPUTS.some(function (s) { return e.target.matches && e.target.matches(s); })) hide();
    }, true);
    document.addEventListener('input', function (e) { if (INPUTS.some(function (s) { return e.target.matches && e.target.matches(s); })) hide(); });
  }
  bind();
})();

(function () {
  var WIRE = "#toTop";
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest(WIRE) : null;
    if (!b) return;
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();

(function () {
  function target(t) {
    var s = t.getAttribute('data-target') || t.getAttribute('href') || '';
    return s.charAt(0) === '#' && s.length > 1 ? document.getElementById(s.slice(1)) : null;
  }
  function toggle(t) {
    var p = target(t);
    if (!p) return;
    var open = getComputedStyle(p).display === 'none';
    p.style.display = open ? 'block' : 'none';
    p.classList.toggle('in', open);
    t.classList.toggle('collapsed', !open);
    t.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target.closest('[data-toggle="collapse"]') : null;
    if (!t || t.hasAttribute('data-dx-do')) return;
    e.preventDefault();
    toggle(t);
  });
  function setup() {
    document.querySelectorAll('[data-toggle="collapse"]:not([data-dx-do])').forEach(function (t) {
      if (!target(t)) return;
      if (!t.hasAttribute('role')) t.setAttribute('role', 'button');
      if (!t.hasAttribute('tabindex')) t.setAttribute('tabindex', '0');
      t.setAttribute('aria-expanded', getComputedStyle(target(t)).display === 'none' ? 'false' : 'true');
    });
  }
  document.addEventListener('keydown', function (e) {
    var t = e.target && e.target.closest ? e.target.closest('[data-toggle="collapse"]') : null;
    if (!t || t.hasAttribute('data-dx-do') || (e.key !== 'Enter' && e.key !== ' ')) return;
    e.preventDefault();
    toggle(t);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup); else setup();
})();

(function () {
  var WIRE = "#toTop";
  function wireIt() {
    document.querySelectorAll(WIRE).forEach(function (b) {
      if (!b.hasAttribute('role')) b.setAttribute('role', 'button');
      if (!b.hasAttribute('tabindex')) b.setAttribute('tabindex', '0');
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wireIt); else wireIt();
  document.addEventListener('keydown', function (e) {
    var b = e.target && e.target.closest ? e.target.closest(WIRE) : null;
    if (!b || (e.key !== 'Enter' && e.key !== ' ')) return;
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();

document.addEventListener('submit', function (e) {
  var f = e.target;
  if (!f || !f.classList || !f.classList.contains('subscribe_form')) return;
  e.preventDefault();
  var inp = f.querySelector('input[name=email]');
  var v = inp ? inp.value.trim() : '';
  var ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
  var msg = f.querySelector('.help-block');
  if (!msg) {
    msg = document.createElement('div');
    msg.className = 'help-block';
    msg.setAttribute('role', 'status');
    inp.parentNode.insertBefore(msg, inp);
  }
  msg.textContent = !v ? 'Veuillez saisir votre adresse e-mail.' : (ok ? 'Merci, vous êtes abonné(e).' : 'Adresse e-mail invalide.');
  if (ok) inp.value = '';
});

(function () {
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.owl-carousel .owl-prev, .owl-carousel .owl-next, .owl-carousel .owl-dot');
    if (!t) return;
    var car = t.closest('.owl-carousel');
    var stage = car.querySelector('.owl-stage');
    var items = Array.prototype.slice.call(stage.children);
    var clones = items.filter(function (i) { return i.classList.contains('cloned'); }).length / 2;
    var real = items.length - clones * 2;
    var per = Math.max(1, items.filter(function (i) { return i.classList.contains('active'); }).length);
    per = Math.min(per, 3);
    var pages = Math.ceil(real / per);
    var first = items.findIndex(function (i) { return i.classList.contains('active'); });
    var cur = Math.round((first - clones) / per);
    var dots = Array.prototype.slice.call(car.querySelectorAll('.owl-dot'));
    var next = t.classList.contains('owl-dot') ? dots.indexOf(t) : (cur + (t.classList.contains('owl-next') ? 1 : -1) + pages) % pages;
    if (next < 0) return;
    var cs = getComputedStyle(items[0]);
    var step = items[0].offsetWidth + parseFloat(cs.marginRight || 0);
    var pos = clones + Math.min(next * per, real - per);
    stage.style.transition = '0.25s';
    stage.style.transform = 'translate3d(' + (-pos * step) + 'px, 0px, 0px)';
    items.forEach(function (i, k) { i.classList.toggle('active', k >= pos && k < pos + per); });
    dots.forEach(function (d, k) { d.classList.toggle('active', k === next); });
  });
})();
(function () {
  document.addEventListener('click', function (e) {
    var open = e.target.closest && e.target.closest('#small_phone_btn');
    var close = e.target.closest && e.target.closest('.close_btn_call_us');
    if (!open && !close) return;
    var box = document.querySelector('.all_ccontact_methods'), btn = document.getElementById('small_phone_btn');
    if (!box || !btn) return;
    box.style.display = open ? 'block' : 'none';
    btn.style.display = open ? 'none' : 'flex';
  });
})();

(function () {
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var btn = t.closest('.content_btn');
    if (btn) {
      var sec = btn.closest('.content_section_item');
      var more = sec && sec.querySelector('.content_hidden');
      if (more) {
        var show = !more.classList.contains('visible');
        more.classList.toggle('visible', show);
        more.style.display = show ? 'block' : '';
      }
      return;
    }
    var cat = t.closest('.left_category');
    if (!cat || t.closest('[data-dx-do]')) return;
    var list = cat.nextElementSibling;
    if (!list || !list.classList.contains('left_prods_sec')) return;
    e.preventDefault();
    var on = !list.classList.contains('visible');
    list.classList.toggle('visible', on);
    cat.classList.toggle('active', on);
    var cl = cat.querySelector('.arrow-close'), op = cat.querySelector('.arrow-open');
    if (cl) cl.style.display = on ? 'none' : '';
    if (op) op.style.display = on ? 'inline' : '';
  });
})();
