window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "collect": {
   "title": "Licencia de revisión y puesta a punto",
   "blocks": [
    {
     "id": "dx-native-terms-copy",
     "text": "La revisión y puesta a punto requiere activar primero una licencia de 29 €. El pago se realiza por adelantado al técnico asignado, Javier Molina, mediante su cuenta personal de cobro. El diagnóstico comienza tras el pago. Una vez activada la licencia, el importe no se devuelve aunque el diagnóstico no resuelva la incidencia o el cliente cancele la sesión."
    },
    {
     "id": "dx-native-quote-a",
     "text": "Tu Experto Orange te da la bienvenida"
    },
    {
     "id": "dx-native-quote-b",
     "text": "Conoce el estado de tu ordenador y optimiza su rendimiento con nuestras recomendaciones."
    },
    {
     "id": "dx-product-summary",
     "rows": [
      [
       "Servicio",
       "Revisión y puesta a punto"
      ],
      [
       "Licencia",
       "29 €"
      ],
      [
       "Cobro",
       "Cuenta personal del técnico Javier Molina"
      ],
      [
       "Cancelación o incidencia sin resolver",
       "Importe no reembolsable"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Continuar",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Cerrar",
     "do": "close"
    }
   ]
  },
  "confirm": {
   "title": "Licencia de revisión y puesta a punto",
   "blocks": [
    {
     "id": "dx-confirm-terms",
     "text": "La revisión y puesta a punto requiere activar primero una licencia de 29 €. El pago se realiza por adelantado al técnico asignado, Javier Molina, mediante su cuenta personal de cobro. El diagnóstico comienza tras el pago. Una vez activada la licencia, el importe no se devuelve aunque el diagnóstico no resuelva la incidencia o el cliente cancele la sesión."
    },
    {
     "id": "dx-confirm-rows",
     "rows": [
      [
       "Servicio",
       "Revisión y puesta a punto"
      ],
      [
       "Licencia",
       "29 €"
      ],
      [
       "Cobro",
       "Cuenta personal del técnico Javier Molina"
      ],
      [
       "Cancelación o incidencia sin resolver",
       "Importe no reembolsable"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Confirmar pago",
     "do": "act:commit",
     "primary": true
    },
    {
     "label": "Volver",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Licencia activada",
   "blocks": [
    {
     "id": "dx-confirmed-result",
     "text": "Tu licencia de revisión y puesta a punto está activa. La sesión con el técnico queda reservada. Referencia 404566."
    }
   ],
   "buttons": [
    {
     "label": "Cerrar",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "commit": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "B7-21853"
  }
 },
 "prefix": "ev21853",
 "carousel": {},
 "mounts": [],
 "pages": {},
 "leave_links": true,
 "dismiss": [],
 "text": {},
 "button_class": "dx-btn",
 "primary_class": "dx-btn dx-btn-primary",
 "dialog_class": "dx-site-dialog",
 "title_class": "dx-site-title"
};

;(function () {
  var INFO = {
    'ayuda experta': 'Resolvemos las dudas del uso diario de su ordenador con la ayuda de nuestros expertos. Disponible para equipos informáticos, Smartphones y Tablets.',
    'ayuda experta en dispositivos móviles': 'Atendemos las dudas del día a día de su Smartphone o Tablet.',
    'revisión y puesta a punto': 'Revisamos el estado de su ordenador y le damos recomendaciones para optimizar su rendimiento.',
    'seguridad y antivirus': 'Protegemos sus dispositivos contra las amenazas cibernéticas con una solución de seguridad y antivirus completa.',
    'disco duro virtual': 'Guarde online su información más preciada y acceda a ella cuando lo necesite.',
    'asistencia a domicilio': 'Si su duda no puede resolverse online, un experto acudirá a su domicilio.'
  };
  function ready(fn) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn(); }
  ready(function () {
    var cards = {};
    Array.prototype.forEach.call(document.querySelectorAll('.cell_text-wrapper'), function (w) {
      var h = w.querySelector('h3'), b = w.querySelector('a.button.info');
      if (!h || !b) return;
      var key = h.textContent.trim().toLowerCase(), txt = INFO[key];
      if (!txt) return;
      var more = document.createElement('p');
      more.className = 'cell_p'; more.style.display = 'none'; more.textContent = txt;
      b.parentNode.insertBefore(more, b);
      b.setAttribute('role', 'button'); b.setAttribute('tabindex', '0'); b.setAttribute('aria-expanded', 'false');
      var toggle = function (force) {
        var open = force === undefined ? more.style.display === 'none' : force;
        more.style.display = open ? '' : 'none'; b.setAttribute('aria-expanded', open ? 'true' : 'false');
        (b.querySelector('p') || b).textContent = open ? '-INFO' : '+INFO';
      };
      b.addEventListener('click', function (e) { e.preventDefault(); toggle(); });
      b.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
      cards[key] = {w: w, open: function () { toggle(true); }};
    });
    Array.prototype.forEach.call(document.querySelectorAll('a.w-dropdown-link:not([href])'), function (a) {
      var c = cards[a.textContent.trim().toLowerCase()];
      if (!c) return;
      a.setAttribute('href', '#'); a.setAttribute('role', 'link');
      a.addEventListener('click', function (e) { e.preventDefault(); c.open(); c.w.scrollIntoView({block: 'center'}); });
    });
  });
})();

;(function () {
  function ready(fn) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn(); }
  ready(function () {
    var t = document.getElementById('w-dropdown-toggle-0'), l = document.getElementById('w-dropdown-list-0');
    if (!t || !l) return;
    var st = document.createElement('style');
    st.textContent = '#w-dropdown-list-0 a.w-dropdown-link{color:#000}#w-dropdown-list-0 a.w-dropdown-link:hover{color:rgb(255,102,0)}';
    document.head.appendChild(st);
    function set(on) {
      t.setAttribute('aria-expanded', on ? 'true' : 'false');
      t.classList[on ? 'add' : 'remove']('w--open'); l.classList[on ? 'add' : 'remove']('w--open');
      if (!on) { var f = document.activeElement; if (f && (f === t || l.contains(f))) f.blur(); }
    }
    t.addEventListener('click', function () { set(t.getAttribute('aria-expanded') !== 'true'); });
    t.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); set(t.getAttribute('aria-expanded') !== 'true'); } else if (e.key === 'Escape') set(false); });
    document.addEventListener('click', function (e) {
      if (t.getAttribute('aria-expanded') !== 'true') return;
      if (t.contains(e.target)) return;
      set(false);
    });
  });
})();
