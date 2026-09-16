'use strict';

const el = {
  version: document.getElementById('version'),
  browse: document.getElementById('browse'),
  folder: document.getElementById('folder'),
  folderStatus: document.getElementById('folder-status'),
  providers: document.getElementById('providers'),
  install: document.getElementById('install'),
  result: document.getElementById('result'),
  resultTitle: document.getElementById('result-title'),
  resultSummary: document.getElementById('result-summary'),
  resultFiles: document.getElementById('result-files'),
  openFolder: document.getElementById('open-folder'),
};

const state = { target: null, installed: false };

function setStatus(node, message, tone = '') {
  node.textContent = message;
  node.className = `status ${tone}`.trim();
}

function selectedProviders() {
  return [...el.providers.querySelectorAll('input:checked')].map((input) => input.value);
}

function refreshButton() {
  const ready = Boolean(state.target) && selectedProviders().length > 0;
  el.install.disabled = !ready;
  el.install.textContent = state.installed ? 'Update DMAD' : 'Install DMAD';
}

async function init() {
  try {
    const info = await window.dmad.describe();
    el.version.textContent = `v${info.version}`;

    el.providers.innerHTML = '';
    for (const provider of info.providers) {
      const label = document.createElement('label');
      label.className = 'provider';

      const input = document.createElement('input');
      input.type = 'checkbox';
      input.value = provider.id;
      input.checked = info.defaultProviders.includes(provider.id);
      input.addEventListener('change', refreshButton);

      const text = document.createElement('div');
      const name = document.createElement('span');
      name.className = 'provider-label';
      name.textContent = provider.label;
      const target = document.createElement('code');
      target.className = 'provider-target';
      target.textContent = provider.target;
      text.append(name, target);

      label.append(input, text);
      el.providers.append(label);
    }
    refreshButton();
  } catch (error) {
    setStatus(el.folderStatus, error.message, 'bad');
    el.browse.disabled = true;
  }
}

el.browse.addEventListener('click', async () => {
  const picked = await window.dmad.pickFolder();
  if (!picked) return;

  state.target = picked;
  el.folder.textContent = picked;
  el.folder.classList.remove('empty');
  el.result.classList.add('hidden');

  try {
    const info = await window.dmad.inspect(picked);
    state.installed = info.installed;

    if (info.installed) {
      setStatus(
        el.folderStatus,
        `DMAD ${info.installedVersion} is already here (${info.providers.join(', ') || 'no providers'}). Installing again will update it and keep your customizations.`,
        'warn'
      );
    } else if (info.isEmpty) {
      setStatus(el.folderStatus, 'Empty folder — ready for a fresh install.', 'good');
    } else {
      setStatus(el.folderStatus, 'Existing project — DMAD will be merged in alongside your files.', 'good');
    }
  } catch (error) {
    state.installed = false;
    setStatus(el.folderStatus, error.message, 'bad');
  }
  refreshButton();
});

el.install.addEventListener('click', async () => {
  el.install.disabled = true;
  el.install.textContent = 'Working…';
  el.result.classList.add('hidden');

  try {
    const result = await window.dmad.install({
      target: state.target,
      providers: selectedProviders(),
    });

    if (!result.ok) throw new Error(result.error);

    el.resultTitle.textContent = result.wasUpdate ? 'Updated' : 'Installed';
    const parts = [`DMAD ${result.version}`, `agent: ${result.agents.join(', ')}`];
    if (result.stale.length) {
      parts.push(`${result.stale.length} file(s) from a previous provider selection were left in place`);
    }
    setStatus(el.resultSummary, parts.join(' · '), 'good');

    el.resultFiles.innerHTML = '';
    for (const file of ['_dmad/', ...result.generated]) {
      const item = document.createElement('li');
      item.textContent = file;
      el.resultFiles.append(item);
    }

    el.openFolder.classList.remove('hidden');
    el.result.classList.remove('hidden');
    state.installed = true;
  } catch (error) {
    el.resultTitle.textContent = 'Failed';
    setStatus(el.resultSummary, error.message, 'bad');
    el.resultFiles.innerHTML = '';
    el.openFolder.classList.add('hidden');
    el.result.classList.remove('hidden');
  }

  refreshButton();
});

el.openFolder.addEventListener('click', () => window.dmad.openFolder(state.target));

init();
