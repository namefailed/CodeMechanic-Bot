document.addEventListener('DOMContentLoaded', () => {
    // Tab Switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // API Base
    const API_BASE = 'http://localhost:8000/api';

    // Elements
    const statusDot = document.getElementById('bot-status-dot');
    const statusText = document.getElementById('bot-status-text');
    const toggleBotBtn = document.getElementById('toggle-bot-btn');
    const terminalOutput = document.getElementById('terminal-output');
    const prContainer = document.getElementById('pr-container');
    const aiContainer = document.getElementById('ai-container');
    const configEditor = document.getElementById('config-editor');
    const saveConfigBtn = document.getElementById('save-config-btn');
    
    // Initialize CodeMirror
    let editor = CodeMirror.fromTextArea(configEditor, {
        mode: "yaml",
        theme: "dracula",
        keyMap: "vim",
        lineNumbers: true,
        viewportMargin: Infinity
    });

    let botRunning = false;

    // Fetch Status
    async function fetchStatus() {
        try {
            const res = await fetch(`${API_BASE}/status`);
            const data = await res.json();
            botRunning = data.status === 'running';
            
            if (botRunning) {
                statusDot.className = 'dot running';
                statusText.textContent = 'Running';
                toggleBotBtn.textContent = 'Stop Bot';
                toggleBotBtn.className = 'action-btn stop';
            } else {
                statusDot.className = 'dot stopped';
                statusText.textContent = 'Stopped';
                toggleBotBtn.textContent = 'Start Bot';
                toggleBotBtn.className = 'action-btn';
            }
        } catch (e) {
            console.error("Failed to fetch status", e);
        }
    }

    // Toggle Bot
    toggleBotBtn.addEventListener('click', async () => {
        const endpoint = botRunning ? '/bot/stop' : '/bot/start';
        // Basic start, could add stealth toggle later
        await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
        await fetchStatus();
    });

    // Color code terminal logs
    function colorizeLogs(logs) {
        return escapeHtml(logs)
            .replace(/(ERROR|Exception|Failed|violently reject)/gi, '<span style="color: var(--danger)">$1</span>')
            .replace(/(SUCCESS|APPROVED|Submitting PR)/gi, '<span style="color: var(--success)">$1</span>')
            .replace(/(WARNING)/gi, '<span style="color: var(--warning)">$1</span>');
    }

    // Fetch Terminal Logs
    async function fetchLogs() {
        try {
            const res = await fetch(`${API_BASE}/logs`);
            const data = await res.json();
            terminalOutput.innerHTML = colorizeLogs(data.logs);
            // auto scroll
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        } catch(e) {}
    }

    // Fetch PRs
    async function fetchPRs() {
        try {
            const res = await fetch(`${API_BASE}/prs`);
            const data = await res.json();
            
            if(data.length === 0) {
                prContainer.innerHTML = '<p style="color: var(--text-secondary)">No PRs tracked yet.</p>';
                return;
            }
            
            prContainer.innerHTML = data.map(pr => `
                <div class="pr-card glass-panel">
                    <div class="pr-status ${pr.status.toLowerCase()}">${pr.status}</div>
                    <h3>${pr.repo}</h3>
                    <a href="${pr.issue_url}" target="_blank" style="color: var(--accent); text-decoration: none; font-size: 0.9rem;">View Issue ↗</a>
                    <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 8px;">Updated: ${new Date(pr.updated_at).toLocaleString()}</div>
                </div>
            `).join('');
        } catch(e) {}
    }

    // Fetch AI Activity
    async function fetchAIActivity() {
        try {
            const res = await fetch(`${API_BASE}/activity`);
            const data = await res.json();
            
            if(data.length === 0) {
                aiContainer.innerHTML = '<p style="color: var(--text-secondary)">No AI activity logged yet.</p>';
                return;
            }
            
            // Show latest first
            aiContainer.innerHTML = data.reverse().map(act => `
                <div class="ai-card glass-panel">
                    <div class="ai-meta">
                        <span class="ai-agent-badge">${act.agent}</span>
                        <span>${new Date(act.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div class="ai-content">
                        <div class="ai-prompt">${escapeHtml(act.prompt)}</div>
                        <div class="ai-response">${escapeHtml(act.response)}</div>
                    </div>
                </div>
            `).join('');
        } catch(e) {}
    }

    // Fetch Config
    async function fetchConfig() {
        try {
            const res = await fetch(`${API_BASE}/config`);
            const text = await res.text();
            const data = JSON.parse(text);
            const formatted = JSON.stringify(data, null, 2);
            configEditor.value = formatted;
            editor.setValue(formatted);
        } catch(e) {}
    }

    // Save Config
    saveConfigBtn.addEventListener('click', async () => {
        try {
            editor.save(); // sync CodeMirror to textarea
            const parsed = JSON.parse(configEditor.value);
            await fetch(`${API_BASE}/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(parsed)
            });
            saveConfigBtn.textContent = 'Saved!';
            setTimeout(() => saveConfigBtn.textContent = 'Save Configuration', 2000);
        } catch(e) {
            alert("Invalid JSON format");
        }
    });

    // Utils
    function escapeHtml(unsafe) {
        return (unsafe || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Fetch Approvals
    async function fetchApprovals() {
        try {
            const res = await fetch(`${API_BASE}/approvals`);
            const data = await res.json();
            
            const approvalsContainer = document.getElementById('approvals-container');
            if(data.length === 0) {
                approvalsContainer.innerHTML = '<p style="color: var(--text-secondary)">No patches pending manual approval.</p>';
                return;
            }
            
            approvalsContainer.innerHTML = data.map(pr => `
                <div class="pr-card glass-panel" style="grid-column: 1 / -1;">
                    <div class="pr-status pending">AWAITING APPROVAL</div>
                    <h3>${pr.repo_name} - #${pr.issue_number}</h3>
                    <p><strong>Title:</strong> ${pr.issue_title}</p>
                    <div style="background: rgba(0,0,0,0.5); padding: 10px; border-radius: 5px; margin: 10px 0; max-height: 200px; overflow-y: auto;">
                        <pre style="margin: 0; font-size: 0.85rem;"><code>${escapeHtml(pr.proposed_fix)}</code></pre>
                    </div>
                    <p style="font-size: 0.85rem; color: #aaa;"><strong>AI Review:</strong><br>${escapeHtml(pr.ai_summary)}</p>
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <button class="action-btn" onclick="approvePR('${pr.issue_url}')" style="background: var(--success); color: #000;">Approve & Submit</button>
                        <button class="action-btn" onclick="rejectPR('${pr.issue_url}')" style="background: var(--danger); color: #fff;">Reject</button>
                    </div>
                </div>
            `).join('');
        } catch(e) {}
    }

    window.approvePR = async function(issueUrl) {
        try {
            await fetch(`${API_BASE}/approvals/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ issue_url: issueUrl })
            });
            fetchApprovals();
            fetchPRs();
        } catch(e) {
            alert("Error approving PR");
        }
    };

    window.rejectPR = async function(issueUrl) {
        try {
            await fetch(`${API_BASE}/approvals/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ issue_url: issueUrl })
            });
            fetchApprovals();
            fetchPRs();
        } catch(e) {
            alert("Error rejecting PR");
        }
    };

    // Analytics Charts
    function initCharts() {
        const vulnCtx = document.getElementById('vulnChart');
        const roiCtx = document.getElementById('roiChart');
        if(!vulnCtx || !roiCtx) return;

        new Chart(vulnCtx, {
            type: 'doughnut',
            data: {
                labels: ['Logic Bugs', 'Secrets (Gitleaks)', 'CVEs (Trivy)'],
                datasets: [{
                    data: [12, 19, 3],
                    backgroundColor: ['#00e5ff', '#ff3366', '#ffcc00']
                }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: '#fff' } } } }
        });

        new Chart(roiCtx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Estimated Earnings ($)',
                    data: [0, 50, 150, 300],
                    borderColor: '#00e5ff',
                    tension: 0.4
                }]
            },
            options: { responsive: true, scales: { y: { ticks: { color: '#fff' } }, x: { ticks: { color: '#fff' } } }, plugins: { legend: { labels: { color: '#fff' } } } }
        });
    }

    // Boot
    fetchStatus();
    fetchLogs();
    fetchPRs();
    fetchAIActivity();
    fetchConfig();
    fetchApprovals();
    setTimeout(initCharts, 500);

    // Polling
    setInterval(fetchStatus, 5000);
    setInterval(fetchLogs, 2000);
    setInterval(fetchPRs, 10000);
    setInterval(fetchAIActivity, 10000);
    setInterval(fetchApprovals, 10000);
});
