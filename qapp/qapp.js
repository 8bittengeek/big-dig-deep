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

document.getElementById('submitJob').onclick = async () => {
  const payload = {
    url: document.getElementById('url').value,
    depth: Number(document.getElementById('depth').value),
    assets: document.getElementById('assets').checked
  };

  const res = await fetch(`${API}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  loadJobs();
};

async function loadJobs() {
  const res = await fetch(`${API}/jobs`);
  const jobs = await res.json();

  const tbody = document.querySelector('#jobsTable tbody');
  tbody.innerHTML = '';

  jobs.forEach(job => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${job.id}</td>
      <td>${job.status}</td>
      <td>${job.progress || 0}%</td>
    `;
    tr.onclick = () => loadLogs(job.id);
    tbody.appendChild(tr);
  });
}

async function loadLogs(id) {
  const res = await fetch(`${API}/jobs/${id}/log`);
  document.getElementById('log').textContent = await res.text();
}

loadJobs();
setInterval(loadJobs, 5000);
