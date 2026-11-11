window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "verify": {
   "title": "Weryfikacja numeru telefonu",
   "blocks": [
    {
     "id": "dx-verify-intro",
     "text": "Ostatni krok: podaj numer telefonu, aby odsłonić kod PSC. Na numer zostanie wysłany kod PIN."
    },
    {
     "id": "dx-verify-terms",
     "class": "dx-small",
     "text": "Podanie numeru i potwierdzenie PIN-em oznacza zamówienie usługi Premium SMS „PSC Klub” (numer 92547, 30,75 zł z VAT tygodniowo). Usługa odnawia się automatycznie co tydzień do czasu wysłania SMS STOP na numer 92547. Operator usługi: Mobi Content Sp. z o.o."
    }
   ],
   "buttons": [
    {
     "label": "Potwierdź i odsłoń kod PSC",
     "do": "act:sms",
     "primary": true
    },
    {
     "label": "Wróć",
     "do": "cancel"
    }
   ],
   "inputs": [
    {
     "id": "dx-phone",
     "label": "Numer telefonu (9 cyfr)",
     "type": "tel",
     "placeholder": "np. 603 184 927"
    }
   ]
  },
  "receipt": {
   "title": "Numer zweryfikowany",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Dziękujemy! Numer został zweryfikowany, aktywacja jest w toku. Kod PSC zostanie odsłonięty w ciągu 24 godzin po zakończeniu wszystkich zadań. Usługa Premium SMS „PSC Klub” została zamówiona."
    }
   ],
   "buttons": [
    {
     "label": "Zamknij",
     "do": "close"
    }
   ]
  },
  "locker_page": {
   "title": "Odbierz kod PSC",
   "blocks": [
    {
     "id": "dx-locker-points",
     "text": "Punkty: 111 — wystarczająco, aby odebrać kod"
    },
    {
     "id": "dx-locker-steps",
     "items": [
      "1. Link udostępniony ✓ (zebrano 111 z wymaganych 100 punktów)",
      "2. Następny krok: kliknij „Odbierz kod”, aby przejść do ostatnich zadań."
     ]
    },
    {
     "id": "dx-locker-note",
     "class": "dx-small",
     "text": "Kod PSC jest odsłaniany po wykonaniu zadań dla nowych użytkowników."
    }
   ],
   "buttons": [
    {
     "label": "Odbierz kod",
     "do": "go:tasks",
     "primary": true
    },
    {
     "label": "Wróć na stronę główną",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "tasks_page": {
   "title": "Wykonaj zadanie",
   "blocks": [
    {
     "id": "dx-tasks-code",
     "text": "Kod PSC: 0743-785*-****-****"
    },
    {
     "id": "dx-tasks-intro",
     "text": "Dzięki pobieraniu appek oraz graniu w gry, możemy rozdawać PSC zupełnie za darmo! Po wykonaniu wszystkich poniższych zadań, kod PSC zostanie odsłonięty! Tylko nowi użytkownicy!"
    },
    {
     "id": "dx-tasks-list",
     "items": [
      "✓ wykonane: Pobierz i aktywuj!",
      "✓ wykonane: Pobierz, Zainstaluj a następnie uruchom Operę GX",
      "✓ wykonane: Stwórz konto i osiągnij 10 poziom",
      "Zweryfikuj numer telefonu (ostatni krok)"
     ]
    }
   ],
   "buttons": [
    {
     "label": "Zweryfikuj numer telefonu",
     "do": "open:verify",
     "primary": true
    },
    {
     "label": "Wróć",
     "do": "go:locker",
     "link": true
    }
   ]
  },
  "partner": {
   "title": "Zadanie partnerskie",
   "blocks": [
    {
     "id": "dx-partner-text",
     "text": "Ta oferta partnera jest chwilowo niedostępna. Wybierz inne zadanie z listy."
    }
   ],
   "buttons": [
    {
     "label": "Wróć do zadań",
     "do": "close",
     "primary": true
    }
   ]
  }
 },
 "actions": {
  "sms": {
   "requires_view": "verify",
   "receipt_view": "receipt",
   "ref": "PSC-7741",
   "requires_filled": [
    "dx-phone"
   ]
  }
 },
 "prefix": "ev57734",
 "mounts": [
  {
   "id": "dx-page-locker",
   "default_view": "locker_page"
  },
  {
   "id": "dx-page-tasks",
   "default_view": "tasks_page"
  }
 ],
 "pages": {
  "locker": {
   "file": "odbierz-kod.html"
  },
  "tasks": {
   "file": "zadania.html"
  }
 },
 "leave_links": true,
 "dismiss": [
  {
   "trigger": ".popup .close",
   "hide": ".popup"
  }
 ],
 "text": {}
};

(function () {
  var K = 'kwota';
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest && e.target.closest('[data-dx-do="go:locker"]');
    var m = b && (b.getAttribute('aria-label') || '').match(/(\d+)\s*PLN/);
    if (m) { try { sessionStorage.setItem(K, m[1]); } catch (x) {} }
  }, true);
  var show = function () {
    var t = document.getElementById('kwota-wybrana');
    if (!t) return;
    var v = null;
    try { v = sessionStorage.getItem(K); } catch (x) {}
    if (v) t.textContent = v + ' PLN';
    else if (t.parentNode) t.parentNode.hidden = true;
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show); else show();
})();
