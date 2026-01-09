//*******************************************************************************
//         ___  _     _ _                  _                 _                  *
//        / _ \| |   (_) |                | |               | |                 *
//       | (_) | |__  _| |_ __ _  ___  ___| | __  _ __   ___| |_                *
//        > _ <| '_ \| | __/ _` |/ _ \/ _ \ |/ / | '_ \ / _ \ __|               *
//       | (_) | |_) | | || (_| |  __/  __/   < _| | | |  __/ |_                *
//        \___/|_.__/|_|\__\__, |\___|\___|_|\_(_)_| |_|\___|\__|               *
//                          __/ |                                               *
//                         |___/                                                *
//                                                                              *
//******************************************************************************/
const API = 'http://localhost:8000';

function applyHubTheme() {
  // Get computed variables from the parent
  const parentStyles = getComputedStyle(window.parent.document.documentElement);
  
  const vars = [
    '--mdc-theme-background',
    '--mdc-theme-on-background',
    '--mdc-theme-surface',
    '--mdc-theme-on-surface',
    '--mdc-theme-primary',
    '--mdc-theme-on-primary',
    '--mdc-theme-outline',
    '--mdc-theme-secondary-container'
  ];
  
  vars.forEach(name => {
    const value = parentStyles.getPropertyValue(name);
    if (value) {
      document.documentElement.style.setProperty(name, value);
    }
  });
}

document.getElementById('submitJob').onclick = async () => {
  const payload = {
    url: document.getElementById('url').value,
    depth: Number(document.getElementById('depth').value),
    assets: document.getElementById('assets').checked
  };

  const res = await fetch(`${API}/job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  // alert(JSON.stringify(payload))

  loadJobs();
};

async function loadJobs() {
  const res = await fetch(`${API}/jobs`);
  const jobsObj = await res.json();
  const jobs = Object.values(jobsObj);

  const tbody = document.querySelector('#jobsTable tbody');
  tbody.innerHTML = '';

  jobs.forEach(job => {
    const tr = document.createElement('tr');

    tr.innerHTML = `
      <td>${job.id}</td>
      <td>${job.status}</td>
      <td>${job.domain ?? ''}</td>
      <td>${job.url_hash.hex ?? ''}</td>
      <td>${job.url ?? ''}</td>
    `;

    tr.onclick = () => loadLogs(job.id);
    tbody.appendChild(tr);
  });

}

async function loadLogs(id) {
  const res = await fetch(`${API}/job/${id}`);
  document.getElementById('log').textContent = await res.text();
}

// Apply immediately
applyHubTheme();

// Optional: reapply if theme changes (Hub may dispatch event)
window.addEventListener('message', e => {
  if (e.data?.type === 'themeChange') applyHubTheme();
});

loadJobs();
setInterval(loadJobs, 5000);
