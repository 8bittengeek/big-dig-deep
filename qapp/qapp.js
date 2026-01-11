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

/**
 * Applies theme variables from the parent window to the current document.
 * Retrieves Material Design Color (MDC) theme variables from the parent's computed styles
 * and applies them to the current document's root element to maintain visual consistency.
 * 
 * @function applyHubTheme
 * @returns {void}
 */
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

/**
 * Validates whether a given string is a valid URL.
 * 
 * @function isValidUrl
 * @param {string} string - The string to validate as a URL
 * @returns {boolean} True if the string is a valid URL, false otherwise
 */
function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch (err) {
    return false;
  }
}

document.getElementById('submitJob').onclick = async () => {
  const payload = {
    op: "new",
    url: document.getElementById('url').value,
    depth: Number(document.getElementById('depth').value),
    assets: document.getElementById('assets').checked
  };

  if ( isValidUrl(payload.url) )
  {
    const res = await fetch(`${API}/job`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  }
  else 
  {
    alert("Invalid URL " + payload.url);
  }

  loadJobs();
};

/**
 * Fetches all jobs from the API and populates the jobs table with the results.
 * Clears the existing table body and creates table rows for each job with click handlers.
 * 
 * @async
 * @function loadJobs
 * @returns {Promise<void>}
 */
async function loadJobs() {
  const res = await fetch(`${API}/job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ op: "jobs" })
  });
  const jobsObj = await res.json();
  const jobs = Object.values(jobsObj);

  const tbody = document.querySelector('#jobsTable tbody');
  tbody.innerHTML = '';

  jobs.forEach(job => {
    const row = document.createElement('tr');
    row.className = 'job-row';

    row.innerHTML = `
      <td>${job.id}</td>
      <td>${job.status ?? ''}</td>
      <td>${job.domain ?? ''}</td>
    `;

    const detailRow = document.createElement('tr');
    detailRow.className = 'job-detail';
    detailRow.style.display = 'none';

    detailRow.innerHTML = `
      <td colspan="3">
        <div class="detail-grid">
          <div><strong>URL</strong><br>${job.domain ?? ''}</div>
          <div><strong>URL</strong><br>${job.url ?? ''}</div>
          <div><strong>URL Hash</strong><br>${job.url_hash ?? ''}</div>
          <div><strong>Status</strong><br>${job.status ?? ''}</div>
          <div><strong>Message</strong><br>${job.message ?? ''}</div>
          <!-- add as many fields as you want -->
        </div>
        <button onclick="loadLogs('${job.id}')">View Logs</button>
        <button onclick="getArchive('${job.url}')">Get Archive</button>
      </td>
    `;

    row.onclick = () => {
      const isOpen = detailRow.style.display === 'table-row';
      document.querySelectorAll('.job-detail').forEach(r => r.style.display = 'none');
      detailRow.style.display = isOpen ? 'none' : 'table-row';
    };

    tbody.appendChild(row);
    tbody.appendChild(detailRow);
  });
}

/**
 * Fetches and displays the log output for a specific job.
 * Retrieves the job details from the API and populates the log display element.
 * 
 * @async
 * @function loadLogs
 * @param {string|number} id - The ID of the job to fetch logs for
 * @returns {Promise<void>}
 */
async function loadLogs(id) {
  const res = await fetch(`${API}/job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ op: "job", id: id })
  });
  const job = await res.json();
  document.getElementById('log').textContent = JSON.stringify(job, null, 2);
}

/**
 * Fetches and displays the archive path for a given URL.
 * 
 * @async
 * @function getArchive
 * @param {string} url - The URL to get the archive for
 * @returns {Promise<void>}
 */
async function getArchive(url) {
  const res = await fetch(`${API}/job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ op: "get", url: url })
  });
  const result = await res.json();
  if (result.path) {
    document.getElementById('log').textContent = `Archive extracted to: ${result.path}`;
  } else {
    document.getElementById('log').textContent = "No archive found for this URL";
  }
}

// Apply immediately
applyHubTheme();

// Reapply if theme changes (Hub may dispatch event)
window.addEventListener('message', e => {
  if (e.data?.type === 'themeChange') applyHubTheme();
});

loadJobs();
setInterval(loadJobs, 3000);
