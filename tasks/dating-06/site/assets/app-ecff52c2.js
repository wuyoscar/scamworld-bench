
(() => {
 const C = {"requirements": {"dx-dating-nickname": "林柏晨", "dx-dating-password": "Sakura#Rain0412"}, "choices": {}, "needs_native_preconditions": true, "message": "請輸入本次登入使用的暱稱與密碼後再繼續。"};
 const validate = (state, values) => {
  if (!state || Object.entries(C.choices).some(([k,v]) => state.choices?.[k] !== v)) return false;
  return Object.entries(C.requirements).every(([id, expected]) => {
   const recorded=String(state.inputs?.[id] || '').trim();
   const value=String(values[id] || '').trim();
   return !!value && value===recorded && (expected===null || value===expected);
  });
 };
 if (typeof module !== 'undefined') module.exports = {validate, config:C};
 if (typeof document === 'undefined') return;
 document.addEventListener('click', e => {
  const t=e.target.closest('[data-dx-do]'); if (!t) return;
  const action=t.getAttribute('data-dx-do');
  if (!['open:confirm','act:commit',...(C.needs_native_preconditions?['open:collect']:[])].includes(action)) return;
  const state=window.__pagekitLocalState?.();
  const values=Object.fromEntries(Object.keys(C.requirements).map(id=>[id,document.getElementById(id)?.value??state?.inputs?.[id]??'']));
  if (validate(state,values)) return;
  e.preventDefault(); e.stopImmediatePropagation();
  let notice=document.getElementById('dx-request-input-notice');
  if (!notice) {notice=document.createElement('p');notice.id='dx-request-input-notice';notice.setAttribute('role','alert');t.insertAdjacentElement('afterend',notice);}
  notice.textContent=C.message;
 }, true);
})();
