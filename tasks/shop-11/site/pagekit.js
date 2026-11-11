
(() => {
  const F = window.PAGE_CONFIG;
  if (!F) return;
  const KEY = 'pagekit:' + F.prefix + ':page';
  const QKEY = 'pagekit:' + F.prefix + ':pending_events';
  const readQ = () => { try { return JSON.parse(sessionStorage.getItem(QKEY)) || []; } catch (e) { return []; } };
  const writeQ = (q) => { try { sessionStorage.setItem(QKEY, JSON.stringify(q)); } catch (e) {} };
  window.__pagekitDrainSiteEvents = () => { const q = readQ(); writeQ([]); return q; };
  const emit = (id, payload) => { const q = readQ(); q.push({event_id: F.prefix + '.' + id, payload: payload || {}}); writeQ(q); };
  const INITIAL = {view: F.initial || null, history: [], commits: [], safe: [], choices: {}, inputs: {}, notice: null};
  if (F.devices) {
    INITIAL.devices = JSON.parse(JSON.stringify(F.devices));
    INITIAL.downloads = {};
  }
  let state;
  try { state = Object.assign({}, INITIAL, JSON.parse(sessionStorage.getItem(KEY)) || {}); }
  catch (e) { state = Object.assign({}, INITIAL); }
  const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };

  let dialog = document.getElementById('dx-dialog');
  if (!dialog) {
    dialog = document.createElement('div'); dialog.id = 'dx-dialog'; dialog.hidden = true;
    document.body.appendChild(dialog);
  }
  dialog.setAttribute('role', 'dialog'); dialog.setAttribute('aria-modal', 'true');

  const fill = (text) => String(text).replace(/\{(\w+)\}/g, (m, k) => {
    const last = state.commits[state.commits.length - 1] || state.safe[state.safe.length - 1] || {};
    if (k === 'ref') return last.ref || '';
    if (k.startsWith('download_') && last.download_job) return String(last.download_job[k.slice(9)] ?? '');
    if (k in state.choices) return state.choices[k];
    return m;
  });
  const visibleIf = (item) => {
    if (!item.if) return true;
    const c = item.if;
    if (c.committed !== undefined && (state.commits.length > 0) !== c.committed) return false;
    if (c.safe_done !== undefined && (state.safe.length > 0) !== c.safe_done) return false;
    if (c.choice) { for (const [k, v] of Object.entries(c.choice)) if (state.choices[k] !== v) return false; }
    return true;
  };
  const el = (tag, attrs, text) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v !== undefined && v !== null) n.setAttribute(k, v);
    if (text !== undefined) n.textContent = fill(text);
    return n;
  };

  const T = {
    en: ['Something went wrong. Please try again.', 'This has already been submitted.', 'Please complete the required fields.'],
    zh: ['出了点问题，请重试。', '该内容已提交，请勿重复提交。', '请填写所有必填项。'],
    zt: ['發生錯誤，請再試一次。', '此內容已提交，請勿重複提交。', '請填寫所有必填欄位。'],
    ja: ['問題が発生しました。もう一度お試しください。', 'すでに送信済みです。', '必須項目をすべて入力してください。'],
    ko: ['문제가 발생했습니다. 다시 시도해 주세요.', '이미 제출되었습니다.', '필수 항목을 모두 입력해 주세요.'],
    de: ['Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.', 'Dies wurde bereits übermittelt.', 'Bitte füllen Sie alle Pflichtfelder aus.'],
    fr: ['Une erreur s’est produite. Veuillez réessayer.', 'Ceci a déjà été envoyé.', 'Veuillez remplir tous les champs obligatoires.'],
    es: ['Algo salió mal. Inténtalo de nuevo.', 'Esto ya se ha enviado.', 'Completa los campos obligatorios.'],
    pt: ['Algo deu errado. Tente novamente.', 'Isto já foi enviado.', 'Preencha os campos obrigatórios.'],
    it: ['Qualcosa è andato storto. Riprova.', 'Questo è già stato inviato.', 'Compila tutti i campi obbligatori.'],
    nl: ['Er is iets misgegaan. Probeer het opnieuw.', 'Dit is al verzonden.', 'Vul alle verplichte velden in.'],
    ru: ['Что-то пошло не так. Попробуйте ещё раз.', 'Это уже отправлено.', 'Заполните все обязательные поля.'],
    bg: ['Нещо се обърка. Опитайте отново.', 'Това вече е изпратено.', 'Моля, попълнете всички задължителни полета.'],
    pl: ['Coś poszło nie tak. Spróbuj ponownie.', 'To zostało już wysłane.', 'Wypełnij wszystkie wymagane pola.'],
    tr: ['Bir şeyler ters gitti. Lütfen tekrar deneyin.', 'Bu zaten gönderildi.', 'Lütfen zorunlu alanları doldurun.'],
    vi: ['Đã xảy ra lỗi. Vui lòng thử lại.', 'Nội dung này đã được gửi.', 'Vui lòng điền đầy đủ các trường bắt buộc.'],
    id: ['Terjadi kesalahan. Silakan coba lagi.', 'Ini sudah dikirim.', 'Harap lengkapi semua kolom yang wajib diisi.'],
    th: ['เกิดข้อผิดพลาด โปรดลองอีกครั้ง', 'ส่งข้อมูลนี้ไปแล้ว', 'โปรดกรอกข้อมูลที่จำเป็นให้ครบ'],
    fa: ['مشکلی پیش آمد. لطفاً دوباره تلاش کنید.', 'این مورد قبلاً ارسال شده است.', 'لطفاً همه فیلدهای الزامی را پر کنید.'],
    sv: ['Något gick fel. Försök igen.', 'Detta har redan skickats.', 'Fyll i alla obligatoriska fält.'],
    da: ['Noget gik galt. Prøv igen.', 'Dette er allerede sendt.', 'Udfyld alle obligatoriske felter.'],
    no: ['Noe gikk galt. Prøv igjen.', 'Dette er allerede sendt.', 'Fyll ut alle obligatoriske felt.'],
    hr: ['Nešto je pošlo po zlu. Pokušajte ponovno.', 'Ovo je već poslano.', 'Ispunite sva obavezna polja.'],
    sk: ['Niečo sa pokazilo. Skúste to znova.', 'Toto už bolo odoslané.', 'Vyplňte všetky povinné polia.'],
    ro: ['Ceva nu a funcționat. Încearcă din nou.', 'Acesta a fost deja trimis.', 'Completează toate câmpurile obligatorii.'],
    hu: ['Hiba történt. Kérjük, próbálja újra.', 'Ez már el lett küldve.', 'Kérjük, töltse ki a kötelező mezőket.']
  };
  const FAM = {zh: 1, ja: 1, ko: 1, th: 1, fa: 1, ru: 1, bg: 1};
  const msg = (i) => {
    const tag = (document.documentElement.lang || '').toLowerCase();
    let l = tag.split(/[-_]/)[0];
    if (l === 'nb' || l === 'nn') l = 'no';
    const s = (document.body.innerText || '').slice(0, 3000);
    const n = (re) => (s.match(re) || []).length;
    const t = n(/\p{L}/gu) || 1;
    if (!FAM[l]) {
      const g = n(/[\u3040-\u30ff]/g) > t * 0.1 ? 'ja' : n(/[\uac00-\ud7af]/g) > t * 0.3 ? 'ko' : n(/[\u4e00-\u9fff]/g) > t * 0.4 ? 'zh'
        : n(/[\u0e00-\u0e7f]/g) > t * 0.4 ? 'th' : n(/[\u0600-\u06ff]/g) > t * 0.4 ? 'fa' : n(/[\u0400-\u04ff]/g) > t * 0.4 ? 'ru' : '';
      if (g) l = g;
    }
    if (l === 'zh') l = /hant|tw|hk|mo/.test(tag) || (!/hans|cn|sg/.test(tag) && n(/[這們與為個於問開關無網請費說點選擇確認資訊]/g) > n(/[这们与为个于问开关无网请费说点选择确认资讯]/g)) ? 'zt' : 'zh';
    return (T[l] || T.en)[i];
  };
  const renderView = (name) => {
    const v = F.views[name];
    const box = el('div', {class: 'dx-view ' + (v.class || ''), 'data-dx-view': name});
    if (v.title) box.appendChild(el(v.title_tag || 'h3', {class: 'dx-title ' + (F.title_class || ''), id: v.title_id}, v.title));
    if (state.notice === 'failed') box.appendChild(el('p', {id: 'dx-notice-failed', class: 'dx-notice'}, (F.text && F.text.failed) || msg(0)));
    if (state.notice === 'duplicate') box.appendChild(el('p', {id: 'dx-notice-duplicate', class: 'dx-notice'}, (F.text && F.text.duplicate) || msg(1)));
    for (const b of v.blocks || []) {
      if (!visibleIf(b)) continue;
      if (b.html) { const d = el('div', {id: b.id, class: 'dx-block ' + (b.class || '')}); d.innerHTML = b.html; box.appendChild(d); continue; }
      if (b.rows) {
        const t = el('table', {id: b.id, class: 'dx-table ' + (b.class || '')});
        for (const [k, val] of b.rows) { const tr = el('tr'); tr.appendChild(el('th', {scope: 'row'}, k)); tr.appendChild(el('td', {}, val)); t.appendChild(tr); }
        box.appendChild(t); continue;
      }
      if (b.items) { const ul = el('ul', {id: b.id, class: 'dx-list ' + (b.class || '')}); for (const it of b.items) ul.appendChild(el('li', {}, it)); box.appendChild(ul); continue; }
      box.appendChild(el(b.tag || 'p', {id: b.id, class: 'dx-text ' + (b.class || '')}, b.text));
    }
    for (const f of v.inputs || []) {
      const wrap = el('label', {class: 'dx-field', for: f.id}); wrap.appendChild(el('span', {class: 'dx-field-label'}, f.label));
      const inp = el('input', {id: f.id, type: f.type || 'text', 'aria-label': f.label, autocomplete: 'off', placeholder: f.placeholder || ''});
      inp.value = (state.inputs || {})[f.id] || '';
      inp.addEventListener('input', () => { state.inputs = Object.assign({}, state.inputs, {[f.id]: inp.value}); save(); });
      wrap.appendChild(inp); box.appendChild(wrap);
    }
    if (state.notice === 'missing') box.appendChild(el('p', {id: 'dx-notice-missing', class: 'dx-notice'}, (F.text && F.text.missing) || msg(2)));
    const row = el('div', {class: 'dx-actions'});
    for (const b of v.buttons || []) {
      if (!visibleIf(b)) continue;
      const kind = b.do.split(':')[0];
      const cls = (b.class || F.button_class || '') + ' dx-button' + (b.primary ? ' dx-primary ' + (F.primary_class || '') : '');
      if (b.link) row.appendChild(el('a', {href: '#', role: 'link', class: cls, 'data-dx-do': b.do, id: b.id}, b.label));
      else row.appendChild(el('button', {type: 'button', class: cls, 'data-dx-do': b.do, 'data-dx-kind': kind, id: b.id}, b.label));
    }
    box.appendChild(row);
    return box;
  };

  const render = () => {
    for (const m of F.mounts || []) {
      const host = document.getElementById(m.id);
      if (!host) continue;
      host.replaceChildren();
      const name = (state.view && F.views[state.view] && F.views[state.view].mount === m.id) ? state.view : m.default_view;
      if (name) host.appendChild(renderView(name));
    }
    const v = state.view && F.views[state.view];
    if (v && (v.mount || 'dialog') === 'dialog') {
      dialog.replaceChildren();
      const inner = el('div', {class: 'dx-dialog-inner ' + (F.dialog_class || '')});
      inner.appendChild(renderView(state.view));
      dialog.appendChild(inner);
      dialog.setAttribute('aria-label', v.title || F.dialog_label || 'Dialog');
      dialog.hidden = false;
    } else {
      dialog.hidden = true; dialog.replaceChildren();
    }
  };

  const go = (view) => {
    if (state.view && state.view !== view) state.history.push(state.view);
    state.view = view;
  };

  const handle = (doit, source) => {
    const [kind, arg] = [doit.split(':')[0], doit.slice(doit.indexOf(':') + 1)];
    state.notice = null;
    if (kind === 'open' && F.views[arg]) {
      go(arg); emit('open_' + arg, {source});
    } else if (kind === 'close') {
      state.view = null; state.history = []; emit('close');
    } else if (kind === 'back') {
      state.view = state.history.pop() || null; emit('back');
    } else if (kind === 'cancel') {
      state.view = state.history.pop() || null; emit('cancel', {from: source});
    } else if (kind === 'go' && ((F.pages && F.pages[arg]) || arg === 'home')) {
      state.view = null; state.history = []; emit('goto_' + arg, {source}); save();
      window.location.href = arg === 'home' ? '/index.html' : '/' + F.pages[arg].file; return;
    } else if (kind === 'leave') {
      emit('leave_site', {target: arg || source}); save(); return;
    } else if (kind === 'choose') {
      const [k, val] = arg.split('='); state.choices[k] = val; emit('choose', {key: k, value: val});
    } else if (kind === 'act' && F.actions[arg]) {
      const a = F.actions[arg];
      if (a.requires_view && state.view !== a.requires_view) return;
      if (a.install) {
        const d = state.devices?.[a.install.device_id];
        if (!d?.paired || !d.session_ready || d.store !== a.install.store) {
          state.notice = 'failed'; emit('act_failed', {action: arg, reason: 'device_session_unavailable'}); save(); render(); return;
        }
      }
      const missing = (a.requires_filled || []).filter((id) => !((state.inputs || {})[id] || '').trim());
      if (missing.length && !state.commits.some((c) => c.action === arg)) {
        state.notice = 'missing'; emit('act_missing', {action: arg, missing}); save(); render(); return;
      }
      if (state.commits.some((c) => c.action === arg)) {
        state.notice = 'duplicate'; emit('act_repeat', {action: arg});
      } else if (window.__pagekitMode === 'effect_failed') {
        state.notice = 'failed'; if (a.failed_view) go(a.failed_view);
        emit('act_failed', {action: arg});
      } else {
        const rec = Object.assign({action: arg, ref: a.ref || ('RF-' + (4400 + state.commits.length))}, a.payload || {}, {choices: Object.assign({}, state.choices), fields_submitted: Object.keys(state.inputs || {}).filter((k) => (state.inputs[k] || '').trim())});
        if (a.keep_inputs) {
          rec.submitted_inputs = Object.fromEntries(a.keep_inputs.map((id) => [id, String(document.getElementById(id)?.value || '')]));
        }
        if (a.install) {
          const job = {job_id: rec.ref + ':download', app: a.install.app,
            device_id: a.install.device_id, store: a.install.store,
            status: 'downloaded'};
          state.downloads[arg] = Object.assign({}, job);
          const device = state.devices[job.device_id];
          device.downloaded_apps = [...new Set([...(device.downloaded_apps || []), job.app])];
          rec.download_job = Object.assign({}, job);
        }
        state.commits.push(rec);
        emit('act_attempt', {action: arg});
        emit('act_commit', rec);
        if (a.receipt_view) go(a.receipt_view);
      }
    } else if (kind === 'alt' && F.actions[arg]) {
      const a = F.actions[arg];
      if (a.requires_view && state.view !== a.requires_view) return;
      if (state.safe.some((c) => c.action === arg)) {
        state.notice = 'duplicate'; emit('act_repeat', {action: arg});
      } else {
        const rec = Object.assign({action: arg, ref: a.ref || ('RF-' + (2200 + state.safe.length))}, a.payload || {});
        state.safe.push(rec); emit('alt_' + arg, rec);
        if (a.receipt_view) go(a.receipt_view);
      }
    } else {
      return;
    }
    save(); render();
  };

  const onActivate = (e) => {
    const t = e.target.closest('[data-dx-do]');
    if (!t) return;
    e.preventDefault(); e.stopPropagation();
    handle(t.getAttribute('data-dx-do'), t.id || t.getAttribute('data-dx-source') || null);
  };
  document.addEventListener('click', onActivate, true);
  document.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.closest && e.target.closest('[data-dx-do]') && e.target.tagName !== 'BUTTON') onActivate(e);
  }, true);
  for (const r of F.dismiss || []) {
    document.querySelectorAll(r.trigger).forEach((t) => t.addEventListener('click', (e) => {
      e.preventDefault(); document.querySelectorAll(r.hide).forEach((h) => { h.style.display = 'none'; });
      emit('ui_dismiss', {trigger: r.trigger});
    }));
  }
  if (F.leave_links) {
    document.querySelectorAll('a[href]').forEach((a) => {
      if (a.hasAttribute('data-dx-do')) return;
      let u; try { u = new URL(a.getAttribute('href'), window.location.href); } catch (e) { return; }
      if (!/^https?:$/.test(u.protocol) || u.hostname === window.location.hostname) return;
      a.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); emit('leave_site', {target: u.hostname}); }, true);
    });
  }
  document.addEventListener('input', (e) => {
    const t = e.target;
    if (!t || !t.id || !/^(INPUT|TEXTAREA)$/.test(t.tagName) || t.closest('.dx-view')) return;
    state.inputs = Object.assign({}, state.inputs, {[t.id]: t.value}); save();
  }, true);
  window.__pagekitLocalState = () => JSON.parse(JSON.stringify(state));
  render();
})();
