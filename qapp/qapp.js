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

// Global state for archive tabs
let archiveTabs = new Map(); // tabId -> { url, timestamp, path, element }
let activeArchiveTab = null;
let tabCounter = 0;

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
 * Initializes tab switching functionality.
 * Sets up event listeners for tab buttons and handles tab content display.
 * 
 * @function initTabs
 * @returns {void}
 */
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetTab = button.getAttribute('data-tab');
      
      // Remove active class from all buttons and panes
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabPanes.forEach(pane => pane.classList.remove('active'));
      
      // Add active class to clicked button and corresponding pane
      button.classList.add('active');
      document.getElementById(`${targetTab}-tab`).classList.add('active');
      
      // Clear active archive tab when switching to controls
      if (targetTab === 'controls') {
        activeArchiveTab = null;
      }
    });
  });
}

/**
 * Creates a new archive tab for a given URL.
 * 
 * @function createArchiveTab
 * @param {string} url - The URL being archived
 * @param {string} path - The local path to the extracted archive
 * @returns {string} The tab ID
 */
function createArchiveTab(url, path) {
  const tabId = `archive-${++tabCounter}`;
  const domain = new URL(url).hostname;
  const tabTitle = domain.length > 20 ? domain.substring(0, 17) + '...' : domain;
  
  // Create tab button
  const tabButton = document.createElement('button');
  tabButton.className = 'archive-tab';
  tabButton.setAttribute('data-tab', tabId);
  tabButton.innerHTML = `
    <span class="archive-tab-title" title="${url}">${tabTitle}</span>
    <button class="archive-tab-close" onclick="closeArchiveTab('${tabId}', event)">×</button>
  `;
  
  // Add click handler for tab switching
  tabButton.addEventListener('click', (e) => {
    if (!e.target.classList.contains('archive-tab-close')) {
      switchToArchiveTab(tabId);
    }
  });
  
  // Create tab content
  const tabContent = document.createElement('div');
  tabContent.id = `${tabId}-tab`;
  tabContent.className = 'tab-pane';
  tabContent.innerHTML = `
    <div class="archive-viewer">
      <div class="archive-header">
        <h2>Archive Viewer</h2>
        <div class="archive-info">
          <span class="archive-url" title="${url}">${url}</span>
          <span class="archive-timestamp">${new Date().toLocaleString()}</span>
        </div>
      </div>
      
      <div class="archive-controls">
        <button class="refresh-archive" onclick="refreshArchive('${tabId}')">Refresh</button>
        <button class="open-new-window" onclick="openArchiveInNewWindow('${tabId}')">Open in New Window</button>
      </div>

      <div class="archive-content">
        <iframe 
          class="archive-frame" 
          sandbox="allow-same-origin allow-scripts allow-forms"
          security="restricted"
          src="about:blank"
        ></iframe>
      </div>
    </div>
  `;
  
  // Add to DOM
  document.getElementById('archiveTabs').appendChild(tabButton);
  document.getElementById('archiveTabContent').appendChild(tabContent);
  
  // Store tab data
  archiveTabs.set(tabId, {
    url,
    path,
    timestamp: new Date().toISOString(),
    element: tabButton,
    contentElement: tabContent
  });
  
  return tabId;
}

/**
 * Switches to a specific archive tab.
 * 
 * @function switchToArchiveTab
 * @param {string} tabId - The ID of the tab to switch to
 * @returns {void}
 */
function switchToArchiveTab(tabId) {
  // Remove active class from all tabs
  document.querySelectorAll('.tab-button, .archive-tab').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
  
  // Add active class to selected tab
  const tabData = archiveTabs.get(tabId);
  if (tabData) {
    tabData.element.classList.add('active');
    tabData.contentElement.classList.add('active');
    activeArchiveTab = tabId;
  }
}

/**
 * Closes an archive tab.
 * 
 * @function closeArchiveTab
 * @param {string} tabId - The ID of the tab to close
 * @param {Event} event - The click event
 * @returns {void}
 */
function closeArchiveTab(tabId, event) {
  event.stopPropagation();
  
  const tabData = archiveTabs.get(tabId);
  if (tabData) {
    // Remove from DOM
    tabData.element.remove();
    tabData.contentElement.remove();
    
    // Remove from state
    archiveTabs.delete(tabId);
    
    // If closing the active tab, switch to controls
    if (activeArchiveTab === tabId) {
      const controlsTab = document.querySelector('[data-tab="controls"]');
      controlsTab.click();
    }
  }
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
        <button class="view-logs-btn" data-job-id="${job.id}">View Logs</button>
        <button class="get-archive-btn" data-job-url="${job.url}">Get Archive</button>
      </td>
    `;

    row.onclick = () => {
      const isOpen = detailRow.style.display === 'table-row';
      document.querySelectorAll('.job-detail').forEach(r => r.style.display = 'none');
      detailRow.style.display = isOpen ? 'none' : 'table-row';
    };

    tbody.appendChild(row);
    tbody.appendChild(detailRow);
    
    // Add event listeners for the buttons (clear existing ones first)
    const viewLogsBtn = detailRow.querySelector('.view-logs-btn');
    const getArchiveBtn = detailRow.querySelector('.get-archive-btn');
    
    if (viewLogsBtn) {
      // Clone button to remove existing event listeners
      const newViewLogsBtn = viewLogsBtn.cloneNode(true);
      viewLogsBtn.parentNode.replaceChild(newViewLogsBtn, viewLogsBtn);
      
      newViewLogsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        loadLogs(job.id);
      });
    }
    
    if (getArchiveBtn) {
      // Clone button to remove existing event listeners
      const newGetArchiveBtn = getArchiveBtn.cloneNode(true);
      getArchiveBtn.parentNode.replaceChild(newGetArchiveBtn, getArchiveBtn);
      
      newGetArchiveBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        getArchive(job.url);
      });
    }
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
 * Fetches and displays the archive content for a given URL in a new tab.
 * 
 * @async
 * @function getArchive
 * @param {string} url - The URL to get the archive for
 * @returns {Promise<void>}
 */
async function getArchive(url) {
  try {
    const res = await fetch(`${API}/job`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ op: "get", url: url })
    });
    
    const result = await res.json();
    
    if (result.path) {
      // Create new archive tab
      const tabId = createArchiveTab(url, result.path);
      
      // Switch to the new tab
      switchToArchiveTab(tabId);
      
      // Load the archived content
      await loadArchiveContent(tabId, result.path, url);
      
      // Update log for reference
      document.getElementById('log').textContent = `Archive loaded: ${url} -> Tab: ${tabId}`;
    } else {
      document.getElementById('log').textContent = "No archive found for this URL";
    }
  } catch (error) {
    console.error('Error loading archive:', error);
    document.getElementById('log').textContent = `Error loading archive: ${error.message}`;
  }
}

/**
 * Loads archive content into a specific tab's iframe.
 * 
 * @async
 * @function loadArchiveContent
 * @param {string} tabId - The ID of the tab to load content into
 * @param {string} path - The local path to the extracted archive
 * @param {string} originalUrl - The original URL that was archived
 * @returns {Promise<void>}
 */
async function loadArchiveContent(tabId, path, originalUrl) {
  const tabData = archiveTabs.get(tabId);
  if (!tabData) return;
  
  const iframe = tabData.contentElement.querySelector('.archive-frame');
  
  try {
    // Try to load the snapshot.html first, then fallback to index.html
    let htmlPath = `${path}/metadata/snapshot.html`;
    
    // Check if snapshot.html exists, otherwise try index.html
    const response = await fetch(`${API}/archive-content?path=${encodeURIComponent(htmlPath)}`);
    
    if (response.ok) {
      const htmlContent = await response.text();
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      
      iframe.src = url;
      
      // Clean up blob URL after loading
      iframe.onload = () => {
        URL.revokeObjectURL(url);
      };
    } else {
      // Try index.html as fallback
      const indexResponse = await fetch(`${API}/archive-content?path=${encodeURIComponent(path + '/index.html')}`);
      if (indexResponse.ok) {
        const htmlContent = await indexResponse.text();
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        
        iframe.src = url;
        
        iframe.onload = () => {
          URL.revokeObjectURL(url);
        };
      } else {
        iframe.srcdoc = '<html><body><h2>Archive content not found</h2><p>The requested archive could not be loaded.</p></body></html>';
      }
    }
  } catch (error) {
    console.error('Error loading archive content:', error);
    iframe.srcdoc = '<html><body><h2>Error loading archive</h2><p>There was an error loading the archived content.</p></body></html>';
  }
}

/**
 * Refreshes the content of an archive tab.
 * 
 * @async
 * @function refreshArchive
 * @param {string} tabId - The ID of the tab to refresh
 * @returns {Promise<void>}
 */
async function refreshArchive(tabId) {
  const tabData = archiveTabs.get(tabId);
  if (tabData) {
    await loadArchiveContent(tabId, tabData.path, tabData.url);
    // Update timestamp
    const timestampElement = tabData.contentElement.querySelector('.archive-timestamp');
    if (timestampElement) {
      timestampElement.textContent = new Date().toLocaleString();
    }
  }
}

/**
 * Opens the archive content in a new window.
 * 
 * @function openArchiveInNewWindow
 * @param {string} tabId - The ID of the tab to open in new window
 * @returns {void}
 */
function openArchiveInNewWindow(tabId) {
  const tabData = archiveTabs.get(tabId);
  if (tabData) {
    const iframe = tabData.contentElement.querySelector('.archive-frame');
    if (iframe.src && iframe.src !== 'about:blank') {
      window.open(iframe.src, '_blank');
    }
  }
}

/**
 * Fetches the user's Qortal identity and updates the UI.
 * 
 * @async
 * @function loadIdentity
 * @returns {Promise<void>}
 */
async function loadIdentity() {
  try {
    const response = await qortalRequest({
      action: "GET_USER_ACCOUNT"
    });
    document.getElementById('identityName').textContent = response.name || response.address || 'Unknown';
  } catch (e) {
    document.getElementById('identityName').textContent = 'Error loading identity';
  }
}

// Apply immediately
applyHubTheme();
initTabs();
loadIdentity();

// Reapply if theme changes (Hub may dispatch event)
window.addEventListener('message', e => {
  if (e.data?.type === 'themeChange') applyHubTheme();
});

loadJobs();
setInterval(loadJobs, 3000);
