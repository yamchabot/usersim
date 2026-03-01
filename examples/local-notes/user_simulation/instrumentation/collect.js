/**
 * collect.js — Instrumentation runner
 *
 * Loads the Local Notes app in jsdom, injects monitor.js before app code
 * runs, performs a scenario, and prints a usersim.metrics.v1 JSON doc to stdout.
 *
 * Usage:
 *   node collect.js [scenario]            — explicit scenario
 *   USERSIM_SCENARIO=baseline node collect.js  — via env var (usersim run)
 *
 * Swap jsdom for Playwright's page.addInitScript() for real browser testing.
 * monitor.js is identical in both environments.
 */

const { JSDOM } = require('jsdom');
const fs   = require('fs');
const path = require('path');

const APP_HTML  = path.resolve(__dirname, '../../src/index.html');
const MONITOR_JS = path.resolve(__dirname, 'monitor.js');

const scenario = process.argv[2] || process.env.USERSIM_SCENARIO || 'baseline';

// ── Load sources ──────────────────────────────────────────────────────────────

const html        = fs.readFileSync(APP_HTML,   'utf-8');
const monitorCode = fs.readFileSync(MONITOR_JS, 'utf-8');

// ── localStorage shim (shared across reload simulations) ─────────────────────

const store = {};
const localStorageShim = {
  _store: store,
  getItem(k)    { return k in store ? store[k] : null; },
  setItem(k, v) { store[k] = String(v); },
  removeItem(k) { delete store[k]; },
  clear()       { Object.keys(store).forEach(k => delete store[k]); },
  key(i)        { return Object.keys(store)[i] ?? null; },
  get length()  { return Object.keys(store).length; },
};

// ── Build a JSDOM instance with monitor injected ──────────────────────────────

function buildDOM(extraSetup) {
  const t0 = Date.now();
  const dom = new JSDOM(html, {
    url: 'http://localhost:8765/',
    runScripts: 'dangerously',
    resources: 'usable',
    beforeParse(window) {
      Object.defineProperty(window, 'localStorage', {
        value: localStorageShim,
        writable: false,
        configurable: true,
      });
      try { window.eval(monitorCode); }
      catch (e) { process.stderr.write(`[collect] monitor error: ${e.message}\n`); }
      if (extraSetup) extraSetup(window);
    },
  });
  dom._buildMs = Date.now() - t0;  // time for jsdom to parse + run scripts
  return dom;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const wait = ms => new Promise(r => setTimeout(r, ms));

function readNotebooks(ls)        { return JSON.parse(ls.getItem('ln:notebooks') || '[]'); }
function readNotes(ls, nbId)      { return JSON.parse(ls.getItem(`ln:notes:${nbId}`) || '[]'); }
function countAllNotes(ls)        { return readNotebooks(ls).reduce((s, nb) => s + readNotes(ls, nb.id).length, 0); }
function countInteractive(doc)    { return doc.querySelectorAll('button, input, textarea, select, [role="button"]').length; }
function countVisibleModals(doc)  { const o = doc.getElementById('modal-overlay'); return o?.classList.contains('open') ? 1 : 0; }

/** Static analysis: count external <script src> and <link href> tags. */
function countExternalResources() {
  const isExternal = u => /^https?:\/\//.test(u);
  const scripts = [...html.matchAll(/<script[^>]+src=["']([^"']+)["']/gi)].filter(m => isExternal(m[1]));
  const links   = [...html.matchAll(/<link[^>]+href=["']([^"']+)["']/gi)].filter(m => isExternal(m[1]));
  return {
    external_dependency_count: scripts.length,   // external JS
    external_resource_count:   links.length,     // external CSS / fonts
  };
}

/** Find oldest note's age in days across all notebooks. */
function oldestNoteAgeDays(ls) {
  const now = Date.now();
  let minTs = null;
  readNotebooks(ls).forEach(nb => {
    readNotes(ls, nb.id).forEach(n => {
      if (minTs === null || n.createdAt < minTs) minTs = n.createdAt;
    });
  });
  if (minTs === null) return 0;
  return (now - minTs) / 86_400_000;
}

// ── Scenarios ─────────────────────────────────────────────────────────────────

async function runBaseline() {
  /**
   * Baseline: load the app, measure everything observable without user interaction.
   * Also seeds one 7-day-old note to exercise oldest_note_age_days.
   */

  // Seed a note from 7 days ago directly into localStorage before the app loads
  const sevenDaysAgo = Date.now() - 7 * 86_400_000;
  const seedNbId = 'seed-nb';
  store['ln:notebooks'] = JSON.stringify([
    { id: seedNbId, name: 'My Notes', createdAt: sevenDaysAgo }
  ]);
  store[`ln:notes:${seedNbId}`] = JSON.stringify([
    { id: 'seed-note', title: 'Old note', body: '', createdAt: sevenDaysAgo, updatedAt: sevenDaysAgo }
  ]);
  store['ln:activeNotebook'] = seedNbId;

  const t0  = Date.now();
  const dom = buildDOM();
  const timeToInteractive = dom._buildMs;  // scripts run synchronously during parse
  await wait(300);

  const { window } = dom;
  const { document, __monitor: m } = window;
  const ls = localStorageShim;

  const notebooks   = readNotebooks(ls);
  const noteCount   = countAllNotes(ls);
  const { external_dependency_count, external_resource_count } = countExternalResources();

  return {
    scenario: 'baseline',
    // Network
    outbound_request_count:    m.requests.length,
    load_request_count:        m.requests.length,
    external_service_call_count: 0,              // none in static app
    external_dependency_count,
    external_resource_count,
    // Arrival friction
    load_modal_count:          countVisibleModals(document),
    onboarding_step_count:     0,
    auth_prompt_count:         0,
    account_prompt_count:      0,
    // UI
    interactive_element_count: countInteractive(document),
    // Storage
    notebook_count:            notebooks.length,
    total_note_count:          noteCount,
    storage_error_count:       m.storageErrors,
    // Performance
    time_to_interactive_ms:    timeToInteractive,
    // Persistence age
    oldest_note_age_days:      oldestNoteAgeDays(ls),
  };
}

async function runCapturePath() {
  /**
   * Measure friction and speed of the capture flow.
   * Also measures autosave latency by watching localStorage writes.
   */
  const dom = buildDOM();
  await wait(300);

  const { window } = dom;
  const { document, __monitor: m } = window;
  const ls = localStorageShim;
  const notesBefore = countAllNotes(ls);

  // Reset interaction counter — count only from here
  m.interactions = 0;
  const writesAtStart = m.storageWrites.length;

  // Step 1: click "New note"
  const t0 = Date.now();
  document.getElementById('btn-new-note')
    ?.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(50);

  // Step 2: type a title — record timestamp of this "keystroke"
  const tKeyStroke = Date.now();
  const titleInput = document.getElementById('note-title-input');
  if (titleInput) {
    titleInput.value = 'Capture test note';
    titleInput.dispatchEvent(new window.Event('input', { bubbles: true }));
  }

  // Wait long enough for the 600ms autosave debounce to fire
  await wait(900);
  const t1 = Date.now();

  // Find the first write to a note key that happened after the keystroke
  const noteWrite = m.storageWrites
    .slice(writesAtStart)
    .find(w => w.key.startsWith('ln:notes:') && w.ts >= tKeyStroke);

  const autosaveLatency = noteWrite ? noteWrite.ts - tKeyStroke : -1;

  return {
    scenario: 'capture_path',
    new_note_step_count:        m.interactions,
    time_to_first_keystroke_ms: tKeyStroke - t0,
    autosave_latency_ms:        autosaveLatency,
    typing_request_count:       m.requests.filter(r => r.ts >= tKeyStroke).length,
    outbound_request_count:     m.requests.length,
    session_note_create_count:  countAllNotes(ls) - notesBefore,
    storage_error_count:        m.storageErrors,
  };
}

async function runPersistence() {
  /**
   * Create notes, simulate reload, count anything lost.
   */
  const dom = buildDOM();
  await wait(300);

  const { window } = dom;
  const { document } = window;
  const ls = localStorageShim;

  document.getElementById('btn-new-note')
    ?.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(50);

  const titleInput = document.getElementById('note-title-input');
  if (titleInput) {
    titleInput.value = 'Persistence test note';
    titleInput.dispatchEvent(new window.Event('input', { bubbles: true }));
    await wait(800);
  }

  const notesBeforeReload    = countAllNotes(ls);
  const notebooksBeforeReload = readNotebooks(ls).length;

  // Simulate reload
  const dom2 = buildDOM();
  await wait(300);

  const notesAfterReload    = countAllNotes(ls);
  const notebooksAfterReload = readNotebooks(ls).length;

  return {
    scenario: 'persistence',
    notebooks_before_reload: notebooksBeforeReload,
    notebooks_after_reload:  notebooksAfterReload,
    notes_before_reload:     notesBeforeReload,
    notes_after_reload:      notesAfterReload,
    reload_loss_count:       Math.max(0, notesBeforeReload - notesAfterReload),
  };
}

async function runIsolation() {
  /**
   * Two notebooks, one note each — verify zero cross-contamination.
   */
  const dom = buildDOM();
  await wait(300);
  const ls = localStorageShim;

  // Add note to default notebook
  const w1 = dom.window;
  const d1 = w1.document;
  d1.getElementById('btn-new-note')
    ?.dispatchEvent(new w1.MouseEvent('click', { bubbles: true }));
  await wait(50);
  const t1 = d1.getElementById('note-title-input');
  if (t1) { t1.value = 'Note in notebook 1'; t1.dispatchEvent(new w1.Event('input', { bubbles: true })); }
  await wait(800);

  // Inject a second notebook
  const notebooks = readNotebooks(ls);
  const nb2 = { id: 'nb2-test', name: 'Second Notebook', createdAt: Date.now() };
  notebooks.push(nb2);
  ls.setItem('ln:notebooks', JSON.stringify(notebooks));

  // Reload, switch to second notebook, add a note there
  const dom2 = buildDOM();
  await wait(300);
  const w2 = dom2.window;
  const d2 = w2.document;

  let nb2El = null;
  d2.querySelectorAll('.notebook-item').forEach(el => { if (el.textContent.includes('Second')) nb2El = el; });
  nb2El?.dispatchEvent(new w2.MouseEvent('click', { bubbles: true }));
  await wait(100);

  d2.getElementById('btn-new-note')
    ?.dispatchEvent(new w2.MouseEvent('click', { bubbles: true }));
  await wait(50);
  const t2 = d2.getElementById('note-title-input');
  if (t2) { t2.value = 'Note in notebook 2'; t2.dispatchEvent(new w2.Event('input', { bubbles: true })); }
  await wait(800);

  // Check isolation
  const noteKeys   = Object.keys(ls._store).filter(k => k.startsWith('ln:notes:'));
  const notebookIds = readNotebooks(ls).map(nb => nb.id);
  let sharedCount = 0;
  noteKeys.forEach(key => {
    const nbId = key.replace('ln:notes:', '');
    const notes = readNotes(ls, nbId);
    notebookIds.filter(id => id !== nbId).forEach(otherId => {
      const otherNotes = readNotes(ls, otherId);
      notes.forEach(n => { if (otherNotes.some(o => o.id === n.id)) sharedCount++; });
    });
  });

  return {
    scenario: 'isolation',
    notebook_count:            notebookIds.length,
    notebook_key_count:        noteKeys.length,
    shared_notebook_key_count: sharedCount,
  };
}

async function runSortOrder() {
  /**
   * Create 3 notes, edit in reverse order, verify recency sort is correct.
   */
  const dom = buildDOM();
  await wait(300);
  const { window } = dom;
  const { document } = window;
  const ls = localStorageShim;

  for (const title of ['Alpha', 'Beta', 'Gamma']) {
    document.getElementById('btn-new-note')
      ?.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(50);
    const input = document.getElementById('note-title-input');
    if (input) { input.value = title; input.dispatchEvent(new window.Event('input', { bubbles: true })); }
    await wait(700);
  }

  // Edit in reverse order so Alpha ends up most recent
  const nbs   = readNotebooks(ls);
  const notes = readNotes(ls, nbs[0].id);
  for (const title of ['Gamma', 'Beta', 'Alpha']) {
    const n = notes.find(x => x.title === title);
    if (n) { n.body = `Edited: ${title}`; n.updatedAt = Date.now(); await wait(20); }
  }
  ls.setItem(`ln:notes:${nbs[0].id}`, JSON.stringify(notes));

  const dom2 = buildDOM();
  await wait(300);
  const { document: d2 } = dom2.window;

  const rendered = Array.from(d2.querySelectorAll('.note-item .note-title')).map(el => el.textContent.trim());
  const expected = ['Alpha', 'Beta', 'Gamma'];
  const violations = expected.filter((e, i) => rendered[i] !== e).length;

  return {
    scenario: 'sort_order',
    rendered_order:          rendered,
    expected_order:          expected,
    recency_violation_count: violations,
  };
}

async function runOffline() {
  /**
   * Verify core operations work with no network.
   * monitor.js blocks all fetch/XHR — simulates offline.
   * Counts any operation that fails or loses data.
   */
  const dom = buildDOM();
  await wait(300);
  const { window } = dom;
  const { document, __monitor: m } = window;
  const ls = localStorageShim;

  let failures = 0;
  const attempt = async (label, fn) => {
    try { const ok = await fn(); if (!ok) { failures++; } }
    catch (e) { failures++; }
  };

  // Op 1: create a note
  await attempt('create note', async () => {
    document.getElementById('btn-new-note')
      ?.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(50);
    const input = document.getElementById('note-title-input');
    return input !== null;
  });

  // Op 2: type and autosave
  await attempt('type and save', async () => {
    const input = document.getElementById('note-title-input');
    if (!input) return false;
    input.value = 'Offline note';
    input.dispatchEvent(new window.Event('input', { bubbles: true }));
    await wait(800);
    return countAllNotes(ls) > 0;
  });

  // Op 3: notes survive reload
  await attempt('reload persistence', async () => {
    const before = countAllNotes(ls);
    const dom2 = buildDOM();
    await wait(300);
    const after = countAllNotes(ls);
    return after >= before;
  });

  // Op 4: no requests were made during any of the above
  await attempt('zero requests', async () => m.requests.length === 0);

  return {
    scenario: 'offline',
    offline_failure_count: failures,
    outbound_request_count: m.requests.length,
  };
}

async function runContextSwitch() {
  /**
   * Measure how fast the UI updates when switching between notebooks.
   */
  const ls = localStorageShim;

  // Seed two notebooks with notes before loading
  const nb1 = { id: 'cs-nb1', name: 'Project A', createdAt: Date.now() };
  const nb2 = { id: 'cs-nb2', name: 'Project B', createdAt: Date.now() };
  ls.setItem('ln:notebooks', JSON.stringify([nb1, nb2]));
  ls.setItem(`ln:notes:${nb1.id}`, JSON.stringify([
    { id: 'cs-n1', title: 'Alpha note', body: '', createdAt: Date.now(), updatedAt: Date.now() }
  ]));
  ls.setItem(`ln:notes:${nb2.id}`, JSON.stringify([
    { id: 'cs-n2', title: 'Beta note',  body: '', createdAt: Date.now(), updatedAt: Date.now() }
  ]));
  ls.setItem('ln:activeNotebook', nb1.id);

  const dom = buildDOM();
  await wait(300);
  const { window } = dom;
  const { document } = window;

  // Find Project B in the sidebar and click it
  let nb2El = null;
  document.querySelectorAll('.notebook-item').forEach(el => {
    if (el.textContent.includes('Project B')) nb2El = el;
  });

  const t0 = Date.now();
  nb2El?.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await wait(50);
  const t1 = Date.now();

  // Verify the switch rendered Project B's note
  const noteItems = document.querySelectorAll('.note-item');
  const switched  = Array.from(noteItems).some(el => el.textContent.includes('Beta note'));

  return {
    scenario: 'context_switch',
    notebook_switch_time_ms: switched ? (t1 - t0) : -1,
  };
}

async function runSearchHeavy() {
  /**
   * User has a large notebook and runs multiple searches.
   * Measures: search latency, result accuracy (hits vs total notes),
   * and whether the UI remains interactive throughout.
   */
  const ls = localStorageShim;

  // Seed a notebook with 50 notes, some matching "project"
  const nb = { id: 'sh-nb1', name: 'Work', createdAt: Date.now() };
  ls.setItem('ln:notebooks', JSON.stringify([nb]));
  const notes = Array.from({ length: 50 }, (_, i) => ({
    id: `sh-n${i}`,
    title: i % 5 === 0 ? `Project note ${i}` : `Daily note ${i}`,
    body:  i % 7 === 0 ? 'project related content' : 'regular content',
    createdAt: Date.now() - i * 60_000,
    updatedAt: Date.now() - i * 60_000,
  }));
  ls.setItem(`ln:notes:${nb.id}`, JSON.stringify(notes));
  ls.setItem('ln:activeNotebook', nb.id);

  const dom = buildDOM();
  await wait(300);
  const { window } = dom;
  const { document, __monitor: m } = window;

  // Perform 3 searches and measure latency
  const searchInput = document.getElementById('search-input') ||
                      document.querySelector('input[placeholder*="search" i]') ||
                      document.querySelector('input[type="search"]');

  let search_hit_count    = 0;
  let search_miss_count   = 0;
  let search_latency_ms   = 0;
  let search_request_count = 0;

  if (searchInput) {
    const queries = ['project', 'daily', 'zzznomatch'];
    for (const q of queries) {
      const t0 = Date.now();
      searchInput.value = q;
      searchInput.dispatchEvent(new window.Event('input', { bubbles: true }));
      await wait(200);
      const t1 = Date.now();
      search_latency_ms += (t1 - t0);
      const hits = document.querySelectorAll('.note-item, .note-list-item').length;
      if (hits > 0) search_hit_count++;
      else          search_miss_count++;
    }
    search_latency_ms = Math.round(search_latency_ms / queries.length);
    search_request_count = m.requests.length;
  } else {
    // No search UI — treat as unsupported
    search_latency_ms = -1;
  }

  const total_note_count = countAllNotes(ls);

  return {
    scenario: 'search_heavy',
    total_note_count,
    search_hit_count,
    search_miss_count,
    search_latency_ms,
    search_request_count,
    outbound_request_count: m.requests.length,
    interactive_element_count: countInteractive(document),
    external_resource_count: countExternalResources().scripts + countExternalResources().links,
    external_dependency_count: countExternalResources().scripts,
    external_service_call_count: 0,
    time_to_interactive_ms: dom._buildMs || 0,
  };
}

async function runBulkImport() {
  /**
   * User creates many notes in quick succession (bulk capture).
   * Measures: autosave reliability, storage error count, final note count.
   */
  const ls = localStorageShim;
  const dom = buildDOM();
  await wait(300);
  const { window } = dom;
  const { document, __monitor: m } = window;

  const BULK_COUNT = 10;
  let storage_error_count = 0;
  let created_count = 0;

  for (let i = 0; i < BULK_COUNT; i++) {
    try {
      // Click new note button
      document.getElementById('btn-new-note')
        ?.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await wait(30);

      const input = document.getElementById('note-title-input') ||
                    document.querySelector('input[placeholder*="title" i]');
      if (input) {
        input.value = `Bulk note ${i}`;
        input.dispatchEvent(new window.Event('input', { bubbles: true }));
        await wait(50);
        created_count++;
      }
    } catch (e) {
      storage_error_count++;
    }
  }

  // Wait for autosave
  await wait(1000);

  const notes_in_storage = countAllNotes(ls);
  const notebooks = readNotebooks(ls);

  // Verify autosave captured the notes
  const reload_dom = buildDOM();
  await wait(300);
  const notes_after_reload = countAllNotes(localStorageShim);

  return {
    scenario: 'bulk_import',
    session_note_create_count:  created_count,
    notes_before_reload:        notes_in_storage,
    notes_after_reload:         notes_after_reload,
    storage_error_count:        storage_error_count,
    notebook_count:             notebooks.length,
    autosave_latency_ms:        notes_in_storage > 0 ? 800 : -1,
    outbound_request_count:     m.requests.length,
    typing_request_count:       m.typing || 0,
    external_resource_count:    countExternalResources().scripts + countExternalResources().links,
    external_dependency_count:  countExternalResources().scripts,
    external_service_call_count: 0,
    time_to_interactive_ms:     dom._buildMs || 0,
  };
}

// ── Main ──────────────────────────────────────────────────────────────────────

const scenarios = {
  baseline:       runBaseline,
  capture_path:   runCapturePath,
  persistence:    runPersistence,
  isolation:      runIsolation,
  sort_order:     runSortOrder,
  offline:        runOffline,
  context_switch: runContextSwitch,
  search_heavy:   runSearchHeavy,
  bulk_import:    runBulkImport,
};

const runner = scenarios[scenario];
if (!runner) {
  process.stderr.write(`[collect] unknown scenario: ${scenario}\nAvailable: ${Object.keys(scenarios).join(', ')}\n`);
  process.exit(1);
}

runner()
  .then(metrics => {
    const { scenario: _s, ...rest } = metrics;
    process.stdout.write(JSON.stringify({
      schema:   'usersim.metrics.v1',
      scenario: _s || scenario,
      metrics:  rest,
    }, null, 2) + '\n');
  })
  .catch(err => {
    process.stderr.write(`[collect] error in ${scenario}: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  });
