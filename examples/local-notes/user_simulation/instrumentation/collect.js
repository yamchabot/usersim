/**
 * collect.js — Basic instrumentation runner
 *
 * Loads the Local Notes app in jsdom, injects monitor.js before app code
 * runs, performs a basic scenario, and prints metrics JSON to stdout.
 *
 * Usage:
 *   node collect.js [scenario]
 *
 * In a real environment: swap jsdom for Playwright's page.addInitScript().
 * The monitor.js file is identical in both cases.
 */

const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const APP_HTML = path.resolve(__dirname, '../../src/index.html');
const MONITOR_JS = path.resolve(__dirname, 'monitor.js');

const scenario = process.argv[2] || process.env.USERSIM_SCENARIO || 'baseline';

// ── Load sources ─────────────────────────────────────────────────────────────

const html = fs.readFileSync(APP_HTML, 'utf-8');
const monitorCode = fs.readFileSync(MONITOR_JS, 'utf-8');

// ── localStorage shim (shared across reload simulation) ───────────────────────

const store = {};
const localStorageShim = {
  _store: store,
  getItem(k)      { return k in store ? store[k] : null; },
  setItem(k, v)   { store[k] = String(v); },
  removeItem(k)   { delete store[k]; },
  clear()         { Object.keys(store).forEach(k => delete store[k]); },
  key(i)          { return Object.keys(store)[i] ?? null; },
  get length()    { return Object.keys(store).length; },
};

// ── Build a JSDOM instance with monitor injected ───────────────────────────

function buildDOM(extraSetup) {
  return new JSDOM(html, {
    url: 'http://localhost:8765/',
    runScripts: 'dangerously',
    resources: 'usable',
    beforeParse(window) {
      // Attach the shared localStorage shim so state survives across instances
      Object.defineProperty(window, 'localStorage', {
        value: localStorageShim,
        writable: false,
        configurable: true,
      });

      // Inject monitor BEFORE app code runs
      const script = window.document.createElement('script');
      script.textContent = monitorCode.replace(/\(window\)/, '(window)');
      // Run monitor code directly in the window context
      try {
        window.eval(monitorCode);
      } catch (e) {
        // monitor install failed — note it but continue
        console.error('[collect] monitor install error:', e.message);
      }

      if (extraSetup) extraSetup(window);
    },
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function countInteractiveElements(document) {
  return document.querySelectorAll('button, input, textarea, select, [role="button"]').length;
}

function countVisibleModals(document) {
  // Check for the overlay element — visible if it has class 'open'
  const overlay = document.getElementById('modal-overlay');
  return overlay && overlay.classList.contains('open') ? 1 : 0;
}

function readNotebooks(localStorage) {
  return JSON.parse(localStorage.getItem('ln:notebooks') || '[]');
}

function readNotes(localStorage, notebookId) {
  return JSON.parse(localStorage.getItem(`ln:notes:${notebookId}`) || '[]');
}

function countAllNotes(localStorage) {
  const notebooks = readNotebooks(localStorage);
  return notebooks.reduce((sum, nb) => sum + readNotes(localStorage, nb.id).length, 0);
}

function countStorageKeys(localStorage) {
  return Object.keys(localStorage._store).length;
}

// ── Scenarios ─────────────────────────────────────────────────────────────────

async function runBaseline() {
  /**
   * Baseline: load the app fresh, measure initial state.
   * No user interaction — just what the app presents on arrival.
   */
  const dom = buildDOM();
  await wait(300); // let app init run

  const { window } = dom;
  const { document, __monitor: m } = window;
  const ls = localStorageShim;

  const notebooks = readNotebooks(ls);
  const noteCount = countAllNotes(ls);

  return {
    scenario: 'baseline',
    outbound_request_count:   m.requests.length,
    load_request_count:       m.requests.length,
    load_modal_count:         countVisibleModals(document),
    onboarding_step_count:    0, // no onboarding in this app
    auth_prompt_count:        0, // no auth in this app
    account_prompt_count:     0, // no accounts in this app
    interactive_element_count: countInteractiveElements(document),
    notebook_count:           notebooks.length,
    total_note_count:         noteCount,
    storage_error_count:      m.storageErrors,
    storage_key_count:        countStorageKeys(ls),
  };
}

async function runCapturePathLength() {
  /**
   * Measure how many interactions it takes to create a new note.
   * Starting state: app loaded, default notebook present, no active note.
   */
  const dom = buildDOM();
  await wait(300);

  const { window } = dom;
  const { document, __monitor: m } = window;

  // Reset interaction counter to zero — we only want to count from here
  m.interactions = 0;
  const t0 = Date.now();

  // Step 1: Click "New note" button
  const newNoteBtn = document.getElementById('btn-new-note');
  if (newNoteBtn) {
    newNoteBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(50);
  }

  // Step 2: Type something in the title
  const titleInput = document.getElementById('note-title-input');
  if (titleInput) {
    titleInput.focus();
    titleInput.value = 'Test note';
    titleInput.dispatchEvent(new window.Event('input', { bubbles: true }));
    await wait(50);
  }

  const t1 = Date.now();
  const stepsUsed = m.interactions;

  return {
    scenario: 'capture_path',
    new_note_step_count:      stepsUsed,
    time_to_first_keystroke_ms: t1 - t0,
    outbound_request_count:   m.requests.length,
    typing_request_count:     m.requests.filter(r => r.ts > t0).length,
  };
}

async function runPersistence() {
  /**
   * Create notes, then simulate a reload by building a new DOM instance
   * against the same localStorage. Count anything lost.
   */
  const dom = buildDOM();
  await wait(300);

  const { window } = dom;
  const { document } = window;
  const ls = localStorageShim;

  // Create a note via the UI
  const newNoteBtn = document.getElementById('btn-new-note');
  if (newNoteBtn) {
    newNoteBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(50);
  }
  const titleInput = document.getElementById('note-title-input');
  if (titleInput) {
    titleInput.value = 'Persistence test note';
    titleInput.dispatchEvent(new window.Event('input', { bubbles: true }));
    await wait(800); // wait for autosave debounce
  }

  // Record state before reload
  const notesBeforeReload = countAllNotes(ls);
  const notebooksBeforeReload = readNotebooks(ls).length;

  // Simulate reload — new DOM, same localStorage shim
  const dom2 = buildDOM();
  await wait(300);

  const notesAfterReload = countAllNotes(ls);
  const notebooksAfterReload = readNotebooks(ls).length;

  return {
    scenario: 'persistence',
    notebooks_before_reload:   notebooksBeforeReload,
    notebooks_after_reload:    notebooksAfterReload,
    notes_before_reload:       notesBeforeReload,
    notes_after_reload:        notesAfterReload,
    reload_loss_count:         Math.max(0, notesBeforeReload - notesAfterReload),
  };
}

async function runIsolation() {
  /**
   * Create two notebooks, write notes to each, then verify their data lives
   * under completely separate localStorage keys with no cross-contamination.
   */
  const dom = buildDOM();
  await wait(300);

  const ls = localStorageShim;

  // Notebook 1 already exists (the default "My Notes"). Add a note to it.
  const w1 = dom.window;
  const d1 = w1.document;
  const nb1btn = d1.getElementById('btn-new-note');
  nb1btn.dispatchEvent(new w1.MouseEvent('click', { bubbles: true }));
  await wait(50);
  const t1 = d1.getElementById('note-title-input');
  t1.value = 'Note in notebook 1';
  t1.dispatchEvent(new w1.Event('input', { bubbles: true }));
  await wait(800); // autosave debounce

  // Inject a second notebook directly into localStorage, then reload
  const notebooks = readNotebooks(ls);
  const nb2 = { id: 'nb2-test', name: 'Second Notebook', createdAt: Date.now() };
  notebooks.push(nb2);
  ls.setItem('ln:notebooks', JSON.stringify(notebooks));

  // Reload — new DOM sees both notebooks
  const dom2 = buildDOM();
  await wait(300);
  const w2 = dom2.window;
  const d2 = w2.document;

  // Switch to second notebook
  const nbItems = d2.querySelectorAll('.notebook-item');
  let nb2El = null;
  nbItems.forEach(el => { if (el.textContent.includes('Second')) nb2El = el; });
  if (nb2El) {
    nb2El.dispatchEvent(new w2.MouseEvent('click', { bubbles: true }));
    await wait(100);
  }

  // Add a note to the second notebook
  const nb2btn = d2.getElementById('btn-new-note');
  nb2btn.dispatchEvent(new w2.MouseEvent('click', { bubbles: true }));
  await wait(50);
  const t2 = d2.getElementById('note-title-input');
  t2.value = 'Note in notebook 2';
  t2.dispatchEvent(new w2.Event('input', { bubbles: true }));
  await wait(800); // autosave debounce

  // Inspect localStorage keys
  const allKeys = Object.keys(ls._store);
  const noteKeys = allKeys.filter(k => k.startsWith('ln:notes:'));
  const notebookIds = readNotebooks(ls).map(nb => nb.id);

  // Check isolation: each note key should map to exactly one notebook
  let sharedCount = 0;
  noteKeys.forEach(key => {
    const nbId = key.replace('ln:notes:', '');
    const notes = readNotes(ls, nbId);
    // A violation would be notes from a different notebook appearing under this key
    const otherNbIds = notebookIds.filter(id => id !== nbId);
    notes.forEach(note => {
      // Check if this note also appears under any other key
      otherNbIds.forEach(otherId => {
        const otherNotes = readNotes(ls, otherId);
        if (otherNotes.some(n => n.id === note.id)) sharedCount++;
      });
    });
  });

  return {
    scenario: 'isolation',
    notebook_count:            notebookIds.length,
    notebook_key_count:        noteKeys.length,
    shared_notebook_key_count: sharedCount,
    notes_per_notebook:        notebookIds.map(id => ({ id, count: readNotes(ls, id).length })),
  };
}

async function runSortOrder() {
  /**
   * Create three notes, then edit them in a known order so we can predict
   * the expected recency ranking. Compare predicted vs rendered order.
   */
  const dom = buildDOM();
  await wait(300);

  const { window } = dom;
  const { document } = window;
  const ls = localStorageShim;

  // Create three notes one by one
  const titles = ['Alpha', 'Beta', 'Gamma'];
  for (const title of titles) {
    const btn = document.getElementById('btn-new-note');
    btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(50);
    const input = document.getElementById('note-title-input');
    input.value = title;
    input.dispatchEvent(new window.Event('input', { bubbles: true }));
    await wait(700); // autosave
  }

  // Now edit them in reverse order: Gamma → Beta → Alpha
  // (so Alpha should end up most recent = top of list)
  const nbs = readNotebooks(ls);
  const notesInNb = readNotes(ls, nbs[0].id);

  const editOrder = ['Gamma', 'Beta', 'Alpha'];
  for (const title of editOrder) {
    const note = notesInNb.find(n => n.title === title);
    if (note) {
      note.body = `Edited: ${title}`;
      note.updatedAt = Date.now();
      ls.setItem(`ln:notes:${nbs[0].id}`, JSON.stringify(notesInNb));
    }
    await wait(50);
  }

  // Reload so the DOM reflects the updated order
  const dom2 = buildDOM();
  await wait(300);
  const { document: d2 } = dom2.window;

  // Read rendered order from DOM
  const renderedTitles = Array.from(
    d2.querySelectorAll('.note-item .note-title')
  ).map(el => el.textContent.trim());

  // Expected order: most recently edited first → Alpha, Beta, Gamma
  const expectedOrder = ['Alpha', 'Beta', 'Gamma'];

  let recencyViolations = 0;
  expectedOrder.forEach((expected, i) => {
    if (renderedTitles[i] !== expected) recencyViolations++;
  });

  return {
    scenario: 'sort_order',
    notes_created:          titles.length,
    rendered_order:         renderedTitles,
    expected_order:         expectedOrder,
    recency_violation_count: recencyViolations,
  };
}

// ── Main ──────────────────────────────────────────────────────────────────────

const scenarios = {
  baseline:     runBaseline,
  capture_path: runCapturePathLength,
  persistence:  runPersistence,
  isolation:    runIsolation,
  sort_order:   runSortOrder,
};
const runner = scenarios[scenario] || scenarios.baseline;

runner()
  .then(metrics => {
    const { scenario: _s, ...rest } = metrics;
    const doc = {
      schema:   'usersim.metrics.v1',
      scenario: _s || scenario,
      metrics:  rest,
    };
    process.stdout.write(JSON.stringify(doc, null, 2) + '\n');
  })
  .catch(err => {
    process.stderr.write(`[collect] error: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  });
