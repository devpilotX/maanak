// Account: profile, password change, own sessions.
import { requireAuth, currentUser } from '../workspace.js';
import { mountAppChrome } from '../layout.js';
import { api, ApiError } from '../api.js';
import { $, el, clear, fmtDate, labelize, setStatus, applyFieldErrors, clearFieldErrors, NOT_RECORDED } from '../util.js';
import { confirmDialog } from '../dialog.js';

async function main() {
  mountAppChrome();
  const me = await requireAuth();
  if (!me) return;
  renderProfile(me);
  loadPolicy();
  loadSessions();
  wirePassword();
  wireSecondFactor();
}

function renderProfile(me) {
  const box = $('#profile');
  const dl = el('dl', { class: 'defs' });
  const add = (k, v) => { dl.append(el('dt', { text: k }), el('dd', { text: v || NOT_RECORDED })); };
  add('Name', me.name);
  add('Email', me.email);
  add('Role', labelize(me.role));
  add('Designation', me.designation);
  add('Jurisdiction', me.jurisdiction_name || me.jurisdiction_code);
  box.appendChild(el('div', { class: 'panel' }, [dl]));
  if (me.must_change_password) {
    box.appendChild(el('div', { class: 'notice notice-warn' }, [el('p', { text: 'You are required to change your password.' })]));
  }
}

async function loadPolicy() {
  try { const pol = await api.get('/auth/password-policy'); $('#pw-policy').textContent = (pol.requirements || []).join(' ') || `Minimum ${pol.min_length} characters.`; }
  catch { $('#pw-policy').textContent = 'Choose a strong password.'; }
}

function wirePassword() {
  const form = $('#pw-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors(form); setStatus($('#pw-status'), '');
    try {
      await api.post('/auth/me/password', {
        current_password: form.elements['current_password'].value,
        new_password: form.elements['new_password'].value,
      });
      setStatus($('#pw-status'), 'Password changed.', 'ok');
      form.reset();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) applyFieldErrors(form, err);
      setStatus($('#pw-status'), err instanceof ApiError ? err.message : 'Could not change the password.', 'error');
    }
  });
}

async function loadSessions() {
  const box = $('#sessions');
  clear(box);
  try {
    const res = await api.get('/auth/me/sessions');
    const items = res.items || res || [];
    if (!items.length) { box.appendChild(el('p', { class: 'muted', text: 'No active sessions.' })); return; }
    const table = el('table', { class: 'register' });
    table.appendChild(el('caption', { text: 'Active sessions' }));
    table.appendChild(el('thead', {}, [el('tr', {}, [
      el('th', { scope: 'col', text: 'Device / agent' }),
      el('th', { scope: 'col', text: 'IP' }),
      el('th', { scope: 'col', text: 'Last seen' }),
      el('th', { scope: 'col', text: '' }),
    ])]));
    const tbody = el('tbody');
    for (const s of items) {
      const revoke = el('button', { class: 'btn btn-sm btn-danger', type: 'button', text: s.is_current ? 'This device' : 'Revoke', disabled: !!s.is_current });
      if (!s.is_current) revoke.addEventListener('click', async () => {
        if (!(await confirmDialog('Revoke session', 'Sign out this session?', { danger: true, confirmLabel: 'Revoke' }))) return;
        try { await api.del(`/auth/me/sessions/${s.id}`); loadSessions(); } catch (err) { setStatus($('#page-status'), err instanceof ApiError ? err.message : 'Could not revoke.', 'error'); }
      });
      tbody.appendChild(el('tr', {}, [
        el('th', { scope: 'row', text: s.user_agent || 'unknown' }),
        el('td', { text: s.ip_address || NOT_RECORDED }),
        el('td', { text: s.last_seen_at ? fmtDate(s.last_seen_at) : NOT_RECORDED }),
        el('td', {}, [revoke]),
      ]));
    }
    table.appendChild(tbody);
    box.appendChild(el('div', { class: 'table-wrap' }, [table]));
  } catch (err) {
    box.appendChild(el('div', { class: 'notice notice-error', role: 'alert' }, [el('p', { text: err instanceof ApiError ? err.message : 'Could not load sessions.' })]));
  }
}

main();

// Second factor. Enrolment is two steps on purpose: the secret is stored when it is
// generated but the factor is not active until a code proves the officer holds it, so a
// failed scan cannot lock an account out of its own protection.
let enrolSecret = null;

async function wireSecondFactor() {
  await renderMfaState();

  const enrol = $('#mfa-enrol-form');
  const remove = $('#mfa-remove-form');

  $('#mfa-cancel').addEventListener('click', () => { enrol.hidden = true; enrolSecret = null; renderMfaState(); });
  $('#mfa-remove-cancel').addEventListener('click', () => { remove.hidden = true; renderMfaState(); });

  enrol.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors(enrol);
    try {
      await api.post('/auth/mfa/confirm', { code: $('#mfa-code').value.trim() });
      enrol.hidden = true;
      enrolSecret = null;
      $('#mfa-code').value = '';
      setStatus($('#mfa-status'), 'A second factor is now required to sign in.', 'ok');
      await renderMfaState();
    } catch (err) {
      if (err instanceof ApiError && err.details) applyFieldErrors(enrol, err.details);
      setStatus($('#mfa-status'), err instanceof ApiError ? err.message : 'Could not confirm the code.', 'error');
    }
  });

  remove.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors(remove);
    try {
      await api.post('/auth/mfa/remove', {
        password: $('#mfa-password').value,
        code: $('#mfa-remove-code').value.trim(),
      });
      remove.hidden = true;
      $('#mfa-password').value = '';
      $('#mfa-remove-code').value = '';
      setStatus($('#mfa-status'), 'The second factor has been removed.', 'ok');
      await renderMfaState();
    } catch (err) {
      setStatus($('#mfa-status'), err instanceof ApiError ? err.message : 'Could not remove the second factor.', 'error');
    }
  });
}

async function renderMfaState() {
  const box = $('#mfa-state');
  clear(box);
  let enrolled = false;
  try {
    const state = await api.get('/auth/mfa');
    enrolled = Boolean(state.enrolled);
  } catch (err) {
    setStatus($('#mfa-status'), err instanceof ApiError ? err.message : 'Could not read the second-factor state.', 'error');
    return;
  }

  box.appendChild(el('p', { text: enrolled
    ? 'A second factor is enrolled on this account. Signing in needs a code as well as your password.'
    : 'No second factor is enrolled. Signing in needs only your password.' }));

  const row = el('div', { class: 'btn-row' });
  if (enrolled) {
    const off = el('button', { class: 'btn', type: 'button', text: 'Remove the second factor' });
    off.addEventListener('click', () => { $('#mfa-remove-form').hidden = false; $('#mfa-password').focus(); });
    row.appendChild(off);
  } else {
    const on = el('button', { class: 'btn btn-primary', type: 'button', text: 'Set up a second factor' });
    on.addEventListener('click', beginEnrolment);
    row.appendChild(on);
  }
  box.appendChild(row);
}

async function beginEnrolment() {
  setStatus($('#mfa-status'), '');
  try {
    const started = await api.post('/auth/mfa/begin', {});
    enrolSecret = started.secret;
    const qr = $('#mfa-qr');
    // A data URI: the secret must not be written to object storage, and it is only needed
    // for the seconds the officer spends scanning it.
    qr.src = `data:image/png;base64,${started.qr_png_base64}`;
    qr.hidden = false;
    $('#mfa-secret').textContent = started.secret;
    $('#mfa-enrol-form').hidden = false;
    $('#mfa-code').focus();
  } catch (err) {
    setStatus($('#mfa-status'), err instanceof ApiError ? err.message : 'Could not start enrolment.', 'error');
  }
}
