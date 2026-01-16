// Dashboard JavaScript - Fetch and display data

let funnelChart = null;
let statusChart = null;
let followupItems = [];

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    setLastUpdated();
    
    // Refresh buttons
    document.getElementById('refresh-applied').addEventListener('click', loadAppliedJobs);
    document.getElementById('refresh-suggestions').addEventListener('click', loadSuggestions);
    document.getElementById('refresh-attention').addEventListener('click', loadAttentionNeeded);
    const followupsRefresh = document.getElementById('refresh-followups');
    if (followupsRefresh) {
        followupsRefresh.addEventListener('click', loadFollowups);
    }
});

function setLastUpdated() {
    const now = new Date();
    const formattedTime = now.toLocaleString();
    document.getElementById('last-updated').textContent = `Last Updated: ${formattedTime}`;
}

// ============================================================================
// DASHBOARD TAB FUNCTIONS
// ============================================================================

function loadDashboard() {
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const summary = data.summary;
                const analytics = data.analytics;
                
                // Update stats cards
                document.getElementById('stat-applied').textContent = summary.stats.total_applied;
                document.getElementById('stat-interview').textContent = summary.stats.total_interviews;
                document.getElementById('stat-offer').textContent = summary.stats.total_offers;
                document.getElementById('stat-rejected').textContent = summary.stats.total_rejections;
                
                // Update analytics
                document.getElementById('analytics-success-rate').textContent = analytics.success_rate + '%';
                document.getElementById('analytics-total').textContent = analytics.total_applications;
                document.getElementById('analytics-offers').textContent = analytics.total_offers;
                
                const conversionRate = analytics.total_applications > 0 
                    ? Math.round((analytics.stage_distribution['Interview'] || 0) / analytics.total_applications * 100)
                    : 0;
                document.getElementById('analytics-conversion').textContent = conversionRate + '%';
                
                // Update charts
                updateCharts(analytics);
                
                // Update recent updates
                displayRecentUpdates(summary.recent_updates);
            }
        })
        .catch(error => console.error('Error loading dashboard:', error));
}

function updateCharts(analytics) {
    const stageDistribution = analytics.stage_distribution;
    
    // Funnel Chart
    const funnelCtx = document.getElementById('funnelChart').getContext('2d');
    
    if (funnelChart) {
        funnelChart.destroy();
    }
    
    funnelChart = new Chart(funnelCtx, {
        type: 'bar',
        data: {
            labels: ['Applied', 'Interview', 'Offer'],
            datasets: [{
                label: 'Application Progress',
                data: [
                    stageDistribution['Applied'] || 0,
                    stageDistribution['Interview'] || 0,
                    stageDistribution['Offer'] || 0
                ],
                backgroundColor: [
                    'rgba(13, 110, 253, 0.7)',
                    'rgba(13, 202, 240, 0.7)',
                    'rgba(25, 135, 84, 0.7)'
                ],
                borderColor: [
                    'rgb(13, 110, 253)',
                    'rgb(13, 202, 240)',
                    'rgb(25, 135, 84)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // Status Distribution Chart (Pie)
    const statusCtx = document.getElementById('statusChart').getContext('2d');
    
    if (statusChart) {
        statusChart.destroy();
    }
    
    statusChart = new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: ['Applied', 'Interview', 'Offer', 'Rejected'],
            datasets: [{
                data: [
                    stageDistribution['Applied'] || 0,
                    stageDistribution['Interview'] || 0,
                    stageDistribution['Offer'] || 0,
                    stageDistribution['Rejected'] || 0
                ],
                backgroundColor: [
                    'rgba(13, 110, 253, 0.7)',
                    'rgba(13, 202, 240, 0.7)',
                    'rgba(25, 135, 84, 0.7)',
                    'rgba(220, 53, 69, 0.7)'
                ],
                borderColor: [
                    'rgb(13, 110, 253)',
                    'rgb(13, 202, 240)',
                    'rgb(25, 135, 84)',
                    'rgb(220, 53, 69)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function displayRecentUpdates(updates) {
    const container = document.getElementById('recent-updates');
    
    if (!updates || updates.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3">No recent updates in the last 7 days</p>';
        return;
    }
    
    let html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Update</th>
                    <th>Days Since</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    updates.forEach(job => {
        const badge = `<span class="badge badge-${job.Status.toLowerCase()}">${job.Status}</span>`;
        html += `
            <tr>
                <td><strong>${job.Company}</strong></td>
                <td>${job.Role}</td>
                <td>${badge}</td>
                <td>${job.Last_Update}</td>
                <td><small class="text-muted">${job.Days_Since_Update} days</small></td>
            </tr>
        `;
    });
    
    html += `</tbody></table>`;
    container.innerHTML = html;
}

// ============================================================================
// APPLIED JOBS TAB
// ============================================================================

function loadAppliedJobs() {
    fetch('/api/applied-jobs')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAppliedJobs(data.data);
            }
        })
        .catch(error => console.error('Error loading applied jobs:', error));
}

function displayAppliedJobs(jobs) {
    const container = document.getElementById('applied-jobs-table');
    
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-text">No applications yet</div>
            </div>
        `;
        return;
    }
    
    let html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Applied Date</th>
                    <th>Last Update</th>
                    <th>Days Since</th>
                    <th>Recruiter</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    jobs.forEach(job => {
        const badge = `<span class="badge badge-${job.Status.toLowerCase()}">${job.Status}</span>`;
        html += `
            <tr>
                <td><strong>${job.Company}</strong></td>
                <td>${job.Role}</td>
                <td>${badge}</td>
                <td><small>${job.Applied_Date || 'N/A'}</small></td>
                <td><small>${job.Last_Update || 'N/A'}</small></td>
                <td><small class="text-muted">${job.Days_Since_Update || 0} days</small></td>
                <td><small>${job.Recruiter_Email || 'N/A'}</small></td>
                <td><small>${job.Notes || 'N/A'}</small></td>
            </tr>
        `;
    });
    
    html += `</tbody></table>`;
    container.innerHTML = html;
}

// Load applied jobs on tab click
document.addEventListener('DOMContentLoaded', function() {
    const appliedTab = document.getElementById('applied-tab');
    if (appliedTab) {
        appliedTab.addEventListener('shown.bs.tab', loadAppliedJobs);
    }
});

// ============================================================================
// SUGGESTIONS TAB
// ============================================================================

function loadSuggestions() {
    fetch('/api/suggestions')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('suggestions-total').textContent = data.total;
                document.getElementById('suggestions-saved').textContent = data.saved_count;
                displaySuggestions(data.all);
            }
        })
        .catch(error => console.error('Error loading suggestions:', error));
}

function displaySuggestions(suggestions) {
    const container = document.getElementById('suggestions-table');
    
    if (!suggestions || suggestions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💡</div>
                <div class="empty-state-text">No job suggestions yet</div>
            </div>
        `;
        return;
    }
    
    let html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Source</th>
                    <th>Email Date</th>
                    <th>Saved</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    suggestions.forEach(suggestion => {
        const savedBadge = `<span class="badge badge-${suggestion.Saved === 'Yes' ? 'success' : 'secondary'}">${suggestion.Saved}</span>`;
        html += `
            <tr>
                <td><strong>${suggestion.Company}</strong></td>
                <td>${suggestion.Role}</td>
                <td><small class="badge bg-info">${suggestion.Source}</small></td>
                <td><small>${suggestion.Email_Date || 'N/A'}</small></td>
                <td>${savedBadge}</td>
                <td><small>${suggestion.Notes || 'N/A'}</small></td>
            </tr>
        `;
    });
    
    html += `</tbody></table>`;
    container.innerHTML = html;
}

// Load suggestions on tab click
document.addEventListener('DOMContentLoaded', function() {
    const suggestionsTab = document.getElementById('suggestions-tab');
    if (suggestionsTab) {
        suggestionsTab.addEventListener('shown.bs.tab', loadSuggestions);
    }
});

// ============================================================================
// ATTENTION NEEDED TAB
// ============================================================================

function loadAttentionNeeded() {
    fetch('/api/attention-needed')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAttentionItems(data.data);
            }
        })
        .catch(error => console.error('Error loading attention items:', error));
}

function displayAttentionItems(items) {
    const container = document.getElementById('attention-items');
    
    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <div class="empty-state-text">All applications are up to date!</div>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    items.forEach(item => {
        const priorityBadge = `<span class="badge badge-${item.priority}">${item.priority.toUpperCase()}</span>`;
        html += `
            <div class="attention-item">
                <div class="attention-header">
                    <div class="attention-company">${item.company}</div>
                    <div class="attention-role">${item.role}</div>
                    <div class="attention-reason">📌 ${item.reason}</div>
                    <div class="attention-footer">
                        <span class="attention-update">Last Update: ${item.last_update}</span>
                        <span class="ms-3">${item.recruiter}</span>
                    </div>
                </div>
                <div>
                    <span class="badge badge-${item.status.toLowerCase()}">${item.status}</span>
                    ${priorityBadge}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Load attention needed on tab click
document.addEventListener('DOMContentLoaded', function() {
    const attentionTab = document.getElementById('attention-tab');
    if (attentionTab) {
        attentionTab.addEventListener('shown.bs.tab', loadAttentionNeeded);
    }
});

// Auto-refresh dashboard every 30 seconds
setInterval(function() {
    setLastUpdated();
    loadDashboard();
}, 30000);

// ============================================================================
// FOLLOW-UPS TAB
// ============================================================================

function loadFollowups() {
    fetch('/api/followups')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                followupItems = Array.isArray(data.data) ? data.data : [];
                displayFollowups(followupItems);
            } else {
                followupItems = [];
                displayFollowups([]);
            }
        })
        .catch(error => {
            console.error('Error loading followups:', error);
            followupItems = [];
            displayFollowups([]);
        });
}

function displayFollowups(items) {
    const container = document.getElementById('followups-table');
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✉️</div>
                <div class="empty-state-text">No follow-ups suggested right now</div>
            </div>
        `;
        return;
    }

    let html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Recipient</th>
                    <th>Subject</th>
                    <th>Reasoning</th>
                    <th>Email Body</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    items.forEach((item, idx) => {
        const subject = item.subject || '';
        const body = (item.body || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const recipient = item.suggested_recipient || '';
        const reasoning = item.reasoning || '';
        html += `
            <tr>
                <td><strong>${item.company}</strong></td>
                <td>${item.role}</td>
                <td><small>${recipient}</small></td>
                <td>${subject}</td>
                <td><small>${reasoning}</small></td>
                <td>
                    <details>
                        <summary>View</summary>
                        <pre style="white-space:pre-wrap">${body}</pre>
                    </details>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-secondary" title="Copy subject" onclick="copyFollowup(${idx}, 'subject')">
                            <i class="bi bi-clipboard"></i> Subject
                        </button>
                        <button class="btn btn-outline-secondary" title="Copy email body" onclick="copyFollowup(${idx}, 'body')">
                            <i class="bi bi-clipboard"></i> Body
                        </button>
                        <button class="btn btn-outline-primary" title="Compose in Gmail" onclick="composeGmail(${idx})">
                            <i class="bi bi-envelope-open"></i> Gmail
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
}

// Clipboard copy for follow-up subject/body
function copyFollowup(index, type) {
    try {
        const item = followupItems[index];
        if (!item) return;
        const text = type === 'subject' ? (item.subject || '') : (item.body || '');
        navigator.clipboard.writeText(text).then(() => {
            // Minimal feedback; could be replaced with toast
            console.log('Copied to clipboard');
        }).catch(err => {
            console.error('Clipboard error:', err);
            alert('Unable to copy to clipboard');
        });
    } catch (e) {
        console.error('Copy handler error:', e);
    }
}

// Open Gmail compose with prefilled subject/body (and recipient if available)
function composeGmail(index) {
    const item = followupItems[index];
    if (!item) return;
    const to = encodeURIComponent(item.suggested_recipient || '');
    const su = encodeURIComponent(item.subject || '');
    const body = encodeURIComponent(item.body || '');
    const url = `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${su}&body=${body}`;
    window.open(url, '_blank');
}

// Load followups on tab click
document.addEventListener('DOMContentLoaded', function() {
    const followupsTab = document.getElementById('followups-tab');
    if (followupsTab) {
        followupsTab.addEventListener('shown.bs.tab', loadFollowups);
    }
});
