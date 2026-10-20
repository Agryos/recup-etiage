/* WebUI Recup-Etiage — logique frontend (vanilla JS, sans build). */

const state = {
    types: {},
    currentJobId: null,
    eventSource: null,
    jobFinished: false,
};

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

async function init() {
    try {
        const res = await fetch('/api/types');
        state.types = await res.json();
    } catch (err) {
        console.error('Impossible de charger les types', err);
        return;
    }
    populateTypeSelector();
    setupTabs();
    setupForm();
    loadJobs();
}

// ---------------------------------------------------------------------------
// Formulaire
// ---------------------------------------------------------------------------

function populateTypeSelector() {
    const select = $('type');
    select.innerHTML = '';
    for (const [key, type] of Object.entries(state.types)) {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = type.label;
        select.appendChild(opt);
    }
    select.addEventListener('change', renderDynamicFields);
    renderDynamicFields();
}

function renderDynamicFields() {
    const typeKey = $('type').value;
    const type = state.types[typeKey];
    $('type-description').textContent = type.description || '';
    const container = $('dynamic-fields');
    container.innerHTML = '';
    for (const field of type.fields) {
        container.appendChild(renderField(field));
    }
    if (typeKey === 'meteo') {
        const freq = $('meteo_freq');
        if (freq) {
            freq.addEventListener('change', adaptMeteoDates);
            adaptMeteoDates();
        }
    }
    updatePreview();
}

function renderField(field) {
    const div = document.createElement('div');
    div.className = 'field' + (field.type === 'checkbox' ? ' checkbox-field' : '');

    const label = document.createElement('label');
    label.htmlFor = field.name;
    label.textContent = field.label;

    let input;
    if (field.type === 'select') {
        input = document.createElement('select');
        input.id = field.name;
        input.name = field.name;
        for (const opt of field.options) {
            const o = document.createElement('option');
            o.value = opt;
            o.textContent = opt;
            input.appendChild(o);
        }
        input.value = field.default;
    } else if (field.type === 'checkbox') {
        input = document.createElement('input');
        input.type = 'checkbox';
        input.id = field.name;
        input.name = field.name;
        input.checked = !!field.default;
    } else {
        input = document.createElement('input');
        input.type = field.type; // text | date | month
        input.id = field.name;
        input.name = field.name;
        input.value = field.default || '';
        if (field.placeholder) input.placeholder = field.placeholder;
    }

    input.addEventListener('change', schedulePreview);
    input.addEventListener('input', schedulePreview);

    div.appendChild(label);
    div.appendChild(input);

    if (field.help) {
        const help = document.createElement('p');
        help.className = 'help';
        help.textContent = field.help;
        div.appendChild(help);
    }
    return div;
}

// Pour la météo : MENS => saisie par mois, QUOT => saisie par jour.
function adaptMeteoDates() {
    const freq = $('meteo_freq').value;
    const isMens = freq === 'MENS';
    for (const name of ['start_date', 'end_date']) {
        const el = $(name);
        if (!el) continue;
        const current = el.value;
        el.type = isMens ? 'month' : 'date';
        // Ajuste la valeur au nouveau format si nécessaire.
        if (isMens && current.length === 10) el.value = current.slice(0, 7);
        if (!isMens && current.length === 7) el.value = current + '-01';
    }
}

function setupForm() {
    $('config-form').addEventListener('submit', onLaunch);
    $('reset-btn').addEventListener('click', () => {
        renderDynamicFields();
    });
    $('cancel-btn').addEventListener('click', cancelCurrentJob);
}

async function onLaunch(e) {
    e.preventDefault();
    const { type: typeKey, params } = collectParams();

    const btn = $('launch-btn');
    btn.disabled = true;
    try {
        const res = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: typeKey, params }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert('Erreur : ' + (err.detail || res.status));
            return;
        }
        const job = await res.json();
        switchTab('logs');
        connectToJob(job.id);
        loadJobs();
    } catch (err) {
        alert('Erreur réseau : ' + err.message);
    } finally {
        btn.disabled = false;
    }
}

// ---------------------------------------------------------------------------
// Aperçu de la commande (temps réel)
// ---------------------------------------------------------------------------

function collectParams() {
    const typeKey = $('type').value;
    const type = state.types[typeKey];
    const params = {};
    for (const field of type.fields) {
        const el = $(field.name);
        if (!el) continue;
        params[field.name] = field.type === 'checkbox' ? el.checked : el.value;
    }
    return { type: typeKey, params };
}

let previewTimer = null;
function schedulePreview() {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(updatePreview, 200);
}

async function updatePreview() {
    const box = $('command-preview');
    if (!box) return;
    const { type, params } = collectParams();
    try {
        const res = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, params }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            box.innerHTML = `<span class="preview-error">${escapeHtml(err.detail || 'Paramètres incomplets')}</span>`;
            return;
        }
        const data = await res.json();
        box.innerHTML = data.commands
            .map((c) => `<div class="preview-cmd"><span class="prompt">$</span>${escapeHtml(c)}</div>`)
            .join('');
    } catch (err) {
        box.innerHTML = '<span class="preview-error">Aperçu indisponible</span>';
    }
}

// ---------------------------------------------------------------------------
// Flux de logs (SSE)
// ---------------------------------------------------------------------------

function connectToJob(jobId) {
    if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
    }
    state.currentJobId = jobId;
    state.jobFinished = false;
    $('log-console').textContent = '';
    $('cancel-btn').classList.remove('hidden');
    updateLogStatus('running');

    const es = new EventSource(`/api/jobs/${jobId}/events`);
    state.eventSource = es;

    es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'log') {
            const console = $('log-console');
            console.textContent += data.line;
            console.scrollTop = console.scrollHeight;
        } else if (data.type === 'status') {
            updateLogStatus(data.status);
            if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                state.jobFinished = true;
                es.close();
                state.eventSource = null;
                $('cancel-btn').classList.add('hidden');
                loadJobs();
            }
        }
    };

    es.onerror = () => {
        es.close();
        state.eventSource = null;
        if (!state.jobFinished && state.currentJobId === jobId) {
            setTimeout(() => {
                if (!state.jobFinished && state.currentJobId === jobId) {
                    connectToJob(jobId);
                }
            }, 1000);
        }
    };
}

function updateLogStatus(status) {
    const badge = $('log-status');
    const labels = {
        running: 'En cours…',
        completed: 'Terminé avec succès',
        failed: 'Échec',
        cancelled: 'Annulé',
        idle: 'Aucun job actif',
    };
    badge.textContent = labels[status] || status;
    badge.className = 'status-badge ' + status;
}

async function cancelCurrentJob() {
    if (!state.currentJobId) return;
    try {
        await fetch(`/api/jobs/${state.currentJobId}/cancel`, { method: 'POST' });
    } catch (err) {
        console.error('Annulation impossible', err);
    }
}

// ---------------------------------------------------------------------------
// Liste des jobs
// ---------------------------------------------------------------------------

async function loadJobs() {
    try {
        const res = await fetch('/api/jobs');
        const jobs = await res.json();
        const list = $('jobs-list');
        list.innerHTML = '';
        if (jobs.length === 0) {
            const li = document.createElement('li');
            li.className = 'job-item';
            li.style.cursor = 'default';
            li.innerHTML = '<span class="job-label" style="color:var(--text-muted)">Aucun job pour le moment.</span>';
            list.appendChild(li);
            return;
        }
        for (const job of jobs) {
            const li = document.createElement('li');
            li.className = 'job-item';
            const cmd = (job.commands && job.commands[0]) || '';
            li.innerHTML = `
                <span class="status-badge ${job.status}">${job.status}</span>
                <div style="flex:1">
                    <div class="job-label">${escapeHtml(job.label)}</div>
                    <div class="job-cmd">${escapeHtml(cmd)}</div>
                </div>
                <span class="job-time">${formatTime(job.created_at)}</span>
            `;
            li.addEventListener('click', () => {
                switchTab('logs');
                connectToJob(job.id);
            });
            list.appendChild(li);
        }
    } catch (err) {
        console.error('Chargement des jobs impossible', err);
    }
}

// ---------------------------------------------------------------------------
// Onglets
// ---------------------------------------------------------------------------

function setupTabs() {
    document.querySelectorAll('.tab').forEach((tab) => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
}

function switchTab(name) {
    document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
    document.querySelectorAll('.tab-content').forEach((c) => c.classList.toggle('active', c.id === 'tab-' + name));
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

document.addEventListener('DOMContentLoaded', init);
