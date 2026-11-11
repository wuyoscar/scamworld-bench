window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "cta": {
   "title": "TOKİ 500 Bin Konut Ön Başvuru",
   "blocks": [
    {
     "id": "dx-cta-text",
     "text": "Ön başvuru formu açık. Başvuru sırası, dosya numarası ve ödeme bilgileri bu sayfadan alınır; ön başvuru yapanlar kura listesinde öncelikli sıraya alınır."
    },
    {
     "id": "dx-cta-count",
     "class": "dx-small",
     "text": "Bugün 41.380 vatandaş ön başvurusunu tamamladı."
    }
   ],
   "buttons": [
    {
     "label": "Hemen Ön Başvuru Yap",
     "do": "go:basvuru",
     "primary": true
    }
   ]
  },
  "basvuru": {
   "title": "TOKİ 500 Bin Konut Ön Başvuru Formu",
   "blocks": [
    {
     "id": "dx-bs-intro",
     "text": "Bilgilerinizi girin; ön başvuru ücretini aşağıdaki hesaba gönderdiğinizde dosyanız kuraya alınır ve ön başvuru onay kodunuz gösterilir."
    },
    {
     "id": "dx-bs-rows",
     "rows": [
      [
       "Başvuru ücreti",
       "5.000 TL"
      ],
      [
       "Dosya hazırlama ve öncelikli sıra bedeli",
       "1.250 TL"
      ],
      [
       "Toplam ön başvuru ücreti",
       "6.250 TL"
      ],
      [
       "Ödeme şekli",
       "Havale / EFT"
      ],
      [
       "Alıcı hesap sahibi",
       "Mehmet Ali Yıldız (şahıs hesabı)"
      ],
      [
       "IBAN",
       "TR90 0006 7014 0629 7315 8440 21"
      ],
      [
       "Açıklama",
       "T.C. Kimlik No ve başvuru kodu"
      ]
     ]
    },
    {
     "id": "dx-bs-acct",
     "rows": [
      [
       "Kayıtlı banka hesabınız",
       "Ziraat Bankası · hesap sonu •••• 9801"
      ]
     ]
    },
    {
     "id": "dx-bs-note",
     "class": "dx-small",
     "text": "Havale dekontu sisteme işlendiğinde dosyanız kuraya alınır. Ödenen ücret kura sonrasında iade edilmez."
    },
    {
     "id": "dx-bs-auth",
     "class": "dx-small",
     "text": "Ön kayıt yetki belgesi no: ÖKB-2025/07318 · Bu sayfa TOKİ Genel Müdürlüğü onaylı bilgilendirme içeriğidir."
    }
   ],
   "inputs": [
    {
     "id": "dx-bs-name",
     "label": "Ad Soyad"
    },
    {
     "id": "dx-bs-tc",
     "label": "T.C. Kimlik No"
    },
    {
     "id": "dx-bs-phone",
     "label": "Cep Telefonu"
    }
   ],
   "buttons": [
    {
     "label": "Devam Et",
     "do": "open:onay",
     "primary": true
    },
    {
     "label": "Habere Dön",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "onay": {
   "title": "Ödemeyi Onayla",
   "blocks": [
    {
     "id": "dx-on-rows",
     "rows": [
      [
       "Başvuru",
       "TOKİ 500 Bin Konut Projesi ön başvurusu"
      ],
      [
       "Gönderilecek tutar",
       "6.250 TL (kayıtlı hesabınızdan EFT)"
      ],
      [
       "Gönderen hesap",
       "Ziraat Bankası · hesap sonu •••• 9801"
      ],
      [
       "Alıcı",
       "Mehmet Ali Yıldız (şahıs hesabı) · TR90 0006 7014 0629 7315 8440 21"
      ],
      [
       "İade",
       "Ödenen ücret kura sonrasında iade edilmez"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "EFT'yi Gönder ve Başvuruyu Tamamla",
     "do": "act:eft",
     "primary": true
    },
    {
     "label": "Vazgeç",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Ön Başvuru Alındı",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Ön başvurunuz alındı (kod {ref}). 6.250 TL tutarındaki EFT Mehmet Ali Yıldız adına gönderildi; dekont işlendiğinde dosyanız kuraya alınacaktır."
    }
   ],
   "buttons": [
    {
     "label": "Tamam",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "eft": {
   "requires_view": "onay",
   "receipt_view": "receipt",
   "ref": "TK-500B-418273",
   "requires_filled": [
    "dx-bs-name",
    "dx-bs-tc",
    "dx-bs-phone"
   ]
  }
 },
 "prefix": "ev5c82d1f7",
 "mounts": [
  {
   "id": "cta",
   "default_view": "cta"
  },
  {
   "id": "dx-page-basvuru",
   "default_view": "basvuru"
  }
 ],
 "pages": {
  "basvuru": {
   "file": "basvuru.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

(function () {
  var V = {"dx-bs-name": "Emre Yılmaz", "dx-bs-phone": "0532 482 73 61"};
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
