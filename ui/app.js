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

            // Fix CodeMirror rendering issues when switching from a hidden state
            setTimeout(() => {
                if (btn.dataset.tab === 'settings' && typeof editor !== 'undefined') {
                    editor.refresh();
                } else if (btn.dataset.tab === 'approvals' && typeof approvalEditors !== 'undefined') {
                    Object.values(approvalEditors).forEach(cm => cm.refresh());
                }
            }, 10);
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
            .replace(/^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3})/gm, '<span style="color: var(--text-secondary)">$1</span>')
            .replace(/-\s(INFO)\s-/g, '- <span style="color: var(--accent)">$1</span> -')
            .replace(/-\s(WARNING)\s-/g, '- <span style="color: #fbbf24">$1</span> -')
            .replace(/-\s(ERROR)\s-/g, '- <span style="color: var(--danger)">$1</span> -')
            .replace(/(Exception|Failed|violently reject)/gi, '<span style="color: var(--danger)">$1</span>')
            .replace(/(SUCCESS|APPROVED|Submitting PR)/gi, '<span style="color: var(--success)">$1</span>');
    }

    // Fetch Terminal Logs
    async function fetchLogs() {
        try {
            const res = await fetch(`${API_BASE}/logs`);
            const data = await res.json();
            
            // Check if user is scrolled to the bottom (within 50px)
            const isScrolledToBottom = terminalOutput.scrollHeight - terminalOutput.clientHeight <= terminalOutput.scrollTop + 50;
            
            if (terminalOutput.dataset.rawLogs === data.logs) return;
            terminalOutput.dataset.rawLogs = data.logs;
            
            const currentScrollTop = terminalOutput.scrollTop;
            
            let colorized = colorizeLogs(data.logs);
            // Loop detection highlight
            colorized = colorized.replace(/(Loop detected — read '.*?' 3 times in a row)/g, '<span style="background: rgba(245,158,11,0.2); padding: 2px 4px; border-radius: 4px;">$1</span>');
            
            terminalOutput.innerHTML = colorized;
            
            // auto scroll only if they were already at the bottom
            if (isScrolledToBottom) {
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            } else {
                terminalOutput.scrollTop = currentScrollTop;
            }
        } catch(e) {}
    }

    // Fetch Current Issue
    async function fetchCurrentIssue() {
        try {
            const res = await fetch(`${API_BASE}/bot/current`);
            const data = await res.json();
            const badge = document.getElementById('current-issue-badge');
            if (data && data.repo && data.title) {
                badge.style.display = 'inline-block';
                badge.textContent = `Processing: ${data.repo} - ${data.title}`;
            } else {
                badge.style.display = 'none';
            }
        } catch(e) {}
    }

    // Command Bar Actions
    document.getElementById('send-nudge-btn').addEventListener('click', async () => {
        const input = document.getElementById('nudge-input');
        if (!input.value.trim()) return;
        try {
            await fetch(`${API_BASE}/bot/nudge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: input.value })
            });
            input.value = '';
        } catch (e) { alert('Failed to send nudge'); }
    });

    document.getElementById('reset-loop-btn').addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/bot/reset-loop`, { method: 'POST' });
        } catch (e) { alert('Failed to reset loop'); }
    });

    document.getElementById('skip-issue-btn').addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/bot/skip`, { method: 'POST' });
        } catch (e) { alert('Failed to skip issue'); }
    });


    const copyLogsBtn = document.getElementById('copy-logs-btn');
    if (copyLogsBtn) {
        copyLogsBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(terminalOutput.innerText);
            const originalText = copyLogsBtn.textContent;
            copyLogsBtn.textContent = 'Copied!';
            setTimeout(() => copyLogsBtn.textContent = originalText, 2000);
        });
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
                    <div class="pr-status ${escapeHtml((pr.status || '').toLowerCase())}">${escapeHtml(pr.status)}</div>
                    <h3>${escapeHtml(pr.repo)}</h3>
                    <a href="${escapeHtml(pr.issue_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent); text-decoration: none; font-size: 0.9rem;">View Issue ↗</a>
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
                if (aiContainer.dataset.rawActivity !== "empty") {
                    aiContainer.innerHTML = '<p style="color: var(--text-secondary)">No engine activity logged yet.</p>';
                    aiContainer.dataset.rawActivity = "empty";
                }
                return;
            }
            
            const dataStr = JSON.stringify(data);
            if (aiContainer.dataset.rawActivity === dataStr) return;
            aiContainer.dataset.rawActivity = dataStr;
            
            // Show latest first
            aiContainer.innerHTML = data.reverse().map(act => {
                // Parse AI prompt and response to separate <think> blocks and highlight <call> or <file> tags
                let parsedResponse = escapeHtml(act.response);
                let thinkContent = "";
                
                // Extract <think>...</think>
                const thinkRegex = /&lt;think&gt;([\s\S]*?)&lt;\/think&gt;/i;
                const thinkMatch = parsedResponse.match(thinkRegex);
                if (thinkMatch) {
                    thinkContent = thinkMatch[1];
                    parsedResponse = parsedResponse.replace(thinkRegex, '');
                }

                // Highlight <call>...</call>
                parsedResponse = parsedResponse.replace(/(&lt;call&gt;[\s\S]*?&lt;\/call&gt;)/gi, '<span style="color: var(--accent); font-weight: bold;">$1</span>');
                
                // Highlight <file ...>...</file>
                parsedResponse = parsedResponse.replace(/(&lt;file path=&quot;.*?&quot;&gt;)/gi, '<span style="color: var(--success); font-weight: bold;">$1</span>');
                parsedResponse = parsedResponse.replace(/(&lt;\/file&gt;)/gi, '<span style="color: var(--success); font-weight: bold;">$1</span>');

                let thinkHtml = thinkContent ? `<div class="ai-think-block" style="background: rgba(255,255,255,0.05); border-left: 4px solid var(--text-secondary); color: var(--text-secondary); padding: 12px; margin-bottom: 12px; font-style: italic; font-size: 0.9em; white-space: pre-wrap;">${thinkContent}</div>` : '';

                return `
                <div class="ai-card glass-panel">
                    <div class="ai-meta">
                        <span class="ai-agent-badge">${escapeHtml(act.agent)}</span>
                        <span>${new Date(act.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div class="ai-content">
                        <div class="ai-prompt">${escapeHtml(act.prompt)}</div>
                        <div class="ai-response">${thinkHtml}${parsedResponse}</div>
                    </div>
                </div>
            `;
            }).join('');
        } catch(e) {}
    }

    // Pop Out Terminal
    const popoutBtn = document.getElementById('popout-terminal-btn');
    if (popoutBtn) {
        popoutBtn.addEventListener('click', () => {
            window.open('terminal.html', 'Live Terminal', 'width=800,height=600,menubar=no,toolbar=no,location=no,status=no');
        });
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
        return (unsafe == null ? '' : String(unsafe))
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Approvals Management
    const approvalEditors = {};

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
            
            // Only re-render if the number or URLs of approvals changed to avoid destroying active edits
            const currentUrls = Object.keys(approvalEditors);
            const newUrls = data.map(pr => pr.issue_url);
            if (currentUrls.length === newUrls.length && currentUrls.every(u => newUrls.includes(u))) {
                return;
            }

            approvalsContainer.innerHTML = data.map((pr, idx) => `
                <div class="pr-card glass-panel" style="grid-column: 1 / -1;">
                    <div class="pr-status pending">AWAITING APPROVAL</div>
                    <h3>${escapeHtml(pr.repo_name)} - #${escapeHtml(pr.issue_number)}</h3>
                    <p><strong>Title:</strong> ${escapeHtml(pr.issue_title)}</p>
                    <div style="margin: 10px 0;">
                        <textarea id="approval-editor-${idx}"></textarea>
                    </div>
                    <p style="font-size: 0.85rem; color: #aaa;"><strong>Engine Review:</strong><br>${escapeHtml(pr.ai_summary)}</p>
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <button class="action-btn approve-btn" data-issue-url="${escapeHtml(pr.issue_url)}" style="background: var(--success); color: #000;">Approve & Submit</button>
                        <button class="action-btn reject-btn" data-issue-url="${escapeHtml(pr.issue_url)}" style="background: var(--danger); color: #fff;">Reject</button>
                    </div>
                </div>
            `).join('');

            // Wire buttons via listeners (not inline onclick) so untrusted issue URLs
            // can never break out into HTML/JS.
            approvalsContainer.querySelectorAll('.approve-btn').forEach(btn => {
                btn.addEventListener('click', () => approvePR(btn.dataset.issueUrl));
            });
            approvalsContainer.querySelectorAll('.reject-btn').forEach(btn => {
                btn.addEventListener('click', () => rejectPR(btn.dataset.issueUrl));
            });

            // Initialize CodeMirror for each approval
            data.forEach((pr, idx) => {
                const ta = document.getElementById(`approval-editor-${idx}`);
                ta.value = pr.proposed_fix;
                const cm = CodeMirror.fromTextArea(ta, {
                    mode: "python", // Best effort, but supports XML tags
                    theme: "dracula",
                    keyMap: "vim",
                    lineNumbers: true,
                    viewportMargin: Infinity
                });
                approvalEditors[pr.issue_url] = cm;
            });
        } catch(e) {}
    }

    window.approvePR = async function(issueUrl) {
        try {
            const cm = approvalEditors[issueUrl];
            const editedCode = cm ? cm.getValue() : null;
            
            await fetch(`${API_BASE}/approvals/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ issue_url: issueUrl, edited_code: editedCode })
            });
            delete approvalEditors[issueUrl];
            // Force re-render
            const approvalsContainer = document.getElementById('approvals-container');
            approvalsContainer.innerHTML = '';
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
            delete approvalEditors[issueUrl];
            // Force re-render
            const approvalsContainer = document.getElementById('approvals-container');
            approvalsContainer.innerHTML = '';
            fetchApprovals();
            fetchPRs();
        } catch(e) {
            alert("Error rejecting PR");
        }
    };

    let vulnChartInstance = null;
    let roiChartInstance = null;

    async function fetchAnalytics() {
        try {
            const res = await fetch(`${API_BASE}/analytics`);
            const data = await res.json();
            
            const statusCounts = data.status_counts || {};
            const paid = statusCounts['PAYOUT_CONFIRMED'] || 0;
            const submitted = statusCounts['SUBMITTED'] || 0;
            const pending = (statusCounts['PENDING'] || 0) + (statusCounts['AWAITING_APPROVAL'] || 0);
            const aborted = (statusCounts['ABORTED'] || 0) + (statusCounts['REJECTED'] || 0) + (statusCounts['REJECTED_MANUALLY'] || 0);

            const chartData = [paid, submitted, pending, aborted];
            
            // Update Metric Cards
            const totalSubmitted = submitted;
            const totalMerged = paid;
            const totalEarnings = Object.values(data.earnings || {}).reduce((a, b) => a + b, 0) || 0;
            const totalAttempts = paid + submitted + pending + aborted + rejected;
            const successRate = totalAttempts > 0 ? Math.round((totalMerged / totalAttempts) * 100) : 0;
            
            const prsSubmittedEl = document.getElementById('metric-prs-submitted');
            if (prsSubmittedEl) prsSubmittedEl.textContent = totalSubmitted;
            
            const prsMergedEl = document.getElementById('metric-prs-merged');
            if (prsMergedEl) prsMergedEl.textContent = totalMerged;
            
            const earningsEl = document.getElementById('metric-earnings');
            if (earningsEl) earningsEl.textContent = totalEarnings.toFixed(2);
            
            const successRateEl = document.getElementById('metric-success-rate');
            if (successRateEl) successRateEl.textContent = successRate + '%';

            if (vulnChartInstance) {
                vulnChartInstance.data.datasets[0].data = chartData;
                vulnChartInstance.update();
            }
            
            const daily = data.daily_activity || {};
            const days = [];
            const counts = [];
            for(let i=6; i>=0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                const dateStr = d.toISOString().split('T')[0];
                days.push(d.toLocaleDateString(undefined, {weekday: 'short'}));
                counts.push(daily[dateStr] || 0);
            }
            
            if (roiChartInstance) {
                roiChartInstance.data.labels = days;
                roiChartInstance.data.datasets[0].data = counts;
                roiChartInstance.update();
            }
        } catch(e) {}
    }

    // Analytics Charts
    function initCharts() {
        const vulnCtx = document.getElementById('vulnChart');
        const roiCtx = document.getElementById('roiChart');
        if(!vulnCtx || !roiCtx) return;

        vulnChartInstance = new Chart(vulnCtx, {
            type: 'doughnut',
            data: {
                labels: ['Paid', 'Submitted', 'Pending', 'Aborted/Rejected'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: { 
                responsive: true, 
                cutout: '70%',
                plugins: { 
                    legend: { position: 'bottom', labels: { color: '#cdd6f4', padding: 20, font: { family: 'Outfit', size: 12 } } },
                    tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.9)', titleColor: '#fff', bodyColor: '#fff', cornerRadius: 8, padding: 12 }
                } 
            }
        });

        roiChartInstance = new Chart(roiCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Earnings (RTC)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: { 
                responsive: true, 
                scales: { 
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false } }, 
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false, drawBorder: false } } 
                }, 
                plugins: { 
                    legend: { display: false },
                    tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.9)', titleColor: '#fff', bodyColor: '#fff', cornerRadius: 8, padding: 12, displayColors: false }
                } 
            }
        });
        
        fetchAnalytics();
    }

    // Boot
    fetchStatus();
    fetchLogs();
    fetchPRs();
    fetchAIActivity();
    fetchConfig();
    fetchApprovals();
    fetchCurrentIssue();
    setTimeout(initCharts, 500);

    // Polling
    setInterval(fetchStatus, 5000);
    setInterval(fetchLogs, 2000);
    setInterval(fetchCurrentIssue, 3000);
    setInterval(fetchPRs, 10000);
    setInterval(fetchAIActivity, 10000);
    setInterval(fetchApprovals, 10000);
    setInterval(fetchAnalytics, 10000);
});
