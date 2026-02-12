/**
 * Research Agent Frontend JavaScript
 * Handles all user interactions and API communication
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const state = {
    isResearching: false,
    currentQuestion: '',
    lastResult: null,
    statusCheckInterval: null,
    quotaCheckInterval: null
};

const PROGRESS_STEPS = [
    { name: 'Planning', threshold: 10 },
    { name: 'Searching', threshold: 30 },
    { name: 'Extracting', threshold: 50 },
    { name: 'Synthesizing', threshold: 70 },
    { name: 'Evaluating', threshold: 85 },
    { name: 'Formatting', threshold: 95 },
    { name: 'Essay', threshold: 100 }
];

// ============================================================================
// DOM HELPERS
// ============================================================================

function getElement(id) {
    return document.getElementById(id);
}

function show(id) {
    const elem = getElement(id);
    if (elem) elem.classList.remove('hidden');
}

function hide(id) {
    const elem = getElement(id);
    if (elem) elem.classList.add('hidden');
}

function showError(message) {
    const errorDiv = getElement('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');
        setTimeout(() => errorDiv.classList.remove('show'), 5000);
    }
}

// ============================================================================
// QUOTA MONITORING
// ============================================================================

async function updateQuotaDisplay() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        const quotaDiv = getElement('quota-display');
        if (quotaDiv && data.quota) {
            const q = data.quota;
            const percent = Math.round((q.requests_used / q.requests_limit) * 100);
            const status = q.quota_exceeded ? '❌ LIMIT REACHED' : `📊 ${q.requests_used}/${q.requests_limit}`;
            
            quotaDiv.textContent = `${status} requests • ${q.provider}`;
            
            if (q.quota_exceeded) {
                quotaDiv.style.color = '#dc2626';
                quotaDiv.style.fontWeight = 'bold';
            } else if (q.requests_remaining <= 2) {
                quotaDiv.style.color = '#ea580c';
            } else {
                quotaDiv.style.color = 'inherit';
                quotaDiv.style.opacity = '0.8';
            }
        }
    } catch (error) {
        console.error('Quota update error:', error);
    }
}

// Update quota on page load and periodically
document.addEventListener('DOMContentLoaded', () => {
    updateQuotaDisplay();
    state.quotaCheckInterval = setInterval(updateQuotaDisplay, 2000);
});

// ============================================================================
// RESEARCH FUNCTIONS
// ============================================================================

async function startResearch() {
    const question = getElement('question').value.trim();
    const maxSources = parseInt(getElement('max-sources').value) || 10;

    if (!question) {
        showError('Please enter a research question');
        return;
    }

    if (state.isResearching) {
        showError('Research is already in progress');
        return;
    }

    state.isResearching = true;
    state.currentQuestion = question;

    // Hide empty state and show progress
    hide('empty-state');
    show('progress-section');
    hide('results-section');

    // Disable button
    const btn = getElement('research-btn');
    btn.disabled = true;

    try {
        // Start research
        const response = await fetch('/api/research', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                max_sources: maxSources
            })
        });

        if (!response.ok) {
            const data = await response.json();
            showError(data.error || 'Failed to start research');
            state.isResearching = false;
            btn.disabled = false;
            return;
        }

        // Poll for status updates
        state.statusCheckInterval = setInterval(checkStatus, 500);

    } catch (error) {
        showError('Error: ' + error.message);
        state.isResearching = false;
        btn.disabled = false;
    }
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update progress
        updateProgress(data.progress, data.status);

        // Check if research is complete
        if (!data.in_progress && data.has_result) {
            clearInterval(state.statusCheckInterval);
            displayResult();
            state.isResearching = false;
            getElement('research-btn').disabled = false;
        } else if (!data.in_progress && data.error) {
            clearInterval(state.statusCheckInterval);
            showError('Research error: ' + data.error);
            state.isResearching = false;
            getElement('research-btn').disabled = false;
        }
    } catch (error) {
        console.error('Status check error:', error);
    }
}

function updateProgress(percentage, status) {
    const fill = getElement('progress-fill');
    const statusText = getElement('progress-status');
    const percentText = getElement('progress-percentage');

    if (fill) fill.style.width = percentage + '%';
    if (statusText) statusText.textContent = status;
    if (percentText) percentText.textContent = percentage + '%';

    // Render visual step pills
    renderProgressSteps(percentage, status);
}

function renderProgressSteps(percentage, status) {
    const container = getElement('progress-steps');
    const card = getElement('progress-steps-card');
    if (!container && !card) return;

    const target = container || card;
    let html = '<div class="progress-steps">';
    PROGRESS_STEPS.forEach(step => {
        const completed = percentage >= step.threshold;
        const isCurrent = !completed && percentage >= (step.threshold - 15);
        html += `<div class="step ${completed ? 'completed' : ''} ${isCurrent ? 'current' : ''}">${step.name}</div>`;
    });
    html += '</div>';

    if (container) container.innerHTML = html;
    if (card) card.innerHTML = html;
}

async function displayResult() {
    try {
        const response = await fetch('/api/result');
        const data = await response.json();

        if (data.success) {
            state.lastResult = data.data;
            renderResult(data.data);
            hide('progress-section');
            show('results-section');
        }
    } catch (error) {
        showError('Error fetching result: ' + error.message);
    }
}

function renderResult(data) {
    // Overview Tab
    const overviewContent = getElement('overview-content');
    if (overviewContent) {
        overviewContent.innerHTML = `
            <h3>${escapeHtml(data.output.question)}</h3>
            <p>${escapeHtml(data.output.overview)}</p>
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
                <p><strong>Timestamp:</strong> ${data.output.timestamp}</p>
                <p><strong>Sources Analyzed:</strong> ${data.sources_count}</p>
                <p><strong>Average Credibility:</strong> ${(data.avg_credibility * 100).toFixed(1)}%</p>
            </div>
        `;
    }

    // Essay Tab (NEW)
    const essayContent = getElement('essay-content');
    if (essayContent) {
        let essayHtml = `<div style="line-height: 1.8; font-size: 0.95em;">`;
        
        if (data.output.essay) {
            // Parse markdown-style headers and format nicely
            const essayText = data.output.essay
                .replace(/^## (.+)$/gm, '</p><h2 style="margin-top: 24px; margin-bottom: 12px; color: #6366f1;">$1</h2><p>')
                .replace(/^### (.+)$/gm, '</p><h3 style="margin-top: 16px; margin-bottom: 8px; color: #818cf8;">$1</h3><p>')
                .replace(/\n\n/g, '</p><p style="margin: 12px 0;">');
            
            essayHtml += `<p>${essayText}</p>`;
        } else {
            essayHtml += `<p>Essay is being generated...</p>`;
        }
        
        essayHtml += `</div>`;
        essayContent.innerHTML = essayHtml;
    }

    // Findings Tab
    const findingsContent = getElement('findings-content');
    if (findingsContent) {
        let findingsHtml = '<h3>Key Findings</h3>';
        data.output.key_findings.forEach((finding, index) => {
            findingsHtml += `<div style="margin-bottom: 16px;">
                <strong>${index + 1}. ${escapeHtml(finding)}</strong>
            </div>`;
        });
        
        if (data.output.challenges.length > 0) {
            findingsHtml += '<h3 style="margin-top: 20px;">Challenges & Limitations</h3>';
            data.output.challenges.forEach((challenge, index) => {
                findingsHtml += `<div style="margin-bottom: 12px;">
                    <strong>${index + 1}. ${escapeHtml(challenge)}</strong>
                </div>`;
            });
        }

        findingsHtml += `<h3 style="margin-top: 20px;">Conclusion</h3>
            <p>${escapeHtml(data.output.conclusion)}</p>`;

        findingsContent.innerHTML = findingsHtml;
    }

    // Sources Tab
    const sourcesContent = getElement('sources-content');
    if (sourcesContent) {
        let sourcesHtml = `<h3>Sources (${data.output.sources.length})</h3>`;
        data.output.sources.slice(0, 20).forEach((source, index) => {
            sourcesHtml += `<div style="margin-bottom: 12px; padding: 10px; background: #f8fafc; border-radius: 6px;">
                <strong>${index + 1}. ${escapeHtml(source)}</strong>
            </div>`;
        });
        sourcesContent.innerHTML = sourcesHtml;
    }

    // Full Report Tab
    const fullContent = getElement('full-content');
    if (fullContent) {
        // Show essay and full formatted report side-by-side on wide screens
        const essayHtml = data.output.essay ? data.output.essay.replace(/^## (.+)$/gm, '<h2>$1</h2>') : '<p>Essay not available.</p>';
        const formattedHtml = `<pre style="white-space:pre-wrap;">${escapeHtml(data.formatted)}</pre>`;

        fullContent.innerHTML = `
            <div class="full-grid">
                <div class="full-left">
                    <h3>Essay</h3>
                    <div class="content-box full-report">${essayHtml}</div>
                </div>
                <div class="full-right">
                    <h3>Full Report</h3>
                    <div class="content-box full-report">${formattedHtml}</div>
                </div>
            </div>
        `;
    }

    // Result metadata
    const timestamp = getElement('result-timestamp');
    if (timestamp) {
        timestamp.innerHTML = `<strong>Generated:</strong> ${data.output.timestamp}`;
    }

    const stats = getElement('result-stats');
    if (stats) {
        stats.innerHTML = `<strong>Sources:</strong> ${data.sources_count} | 
                          <strong>Avg. Credibility:</strong> ${(data.avg_credibility * 100).toFixed(1)}%`;
    }
}

// ============================================================================
// TAB SWITCHING
// ============================================================================

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = getElement(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Activate button
    event.target.classList.add('active');
}

// ============================================================================
// EXPORT & DOWNLOAD
// ============================================================================

function downloadResult(format) {
    if (!state.lastResult) {
        showError('No result to download');
        return;
    }

    const link = document.createElement('a');
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');

    if (format === 'json') {
        const dataStr = JSON.stringify(state.lastResult.output, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        link.href = URL.createObjectURL(blob);
        link.download = `research_${timestamp}.json`;
    } else if (format === 'txt') {
        const blob = new Blob([state.lastResult.formatted], { type: 'text/plain' });
        link.href = URL.createObjectURL(blob);
        link.download = `research_${timestamp}.txt`;
    }

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function clearResult() {
    if (confirm('Are you sure you want to clear this result?')) {
        fetch('/api/clear', { method: 'POST' });
        state.lastResult = null;
        hide('results-section');
        show('empty-state');
        getElement('question').value = '';
    }
}

// ============================================================================
// HISTORY
// ============================================================================

// ============================================================================
// UTILITIES
// ============================================================================

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('en-US', options);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('🔬 Research Agent UI loaded');

    // Set up event listeners
    getElement('question').addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            startResearch();
        }
    });

    // Keyboard shortcut: Ctrl+Enter to start research
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            if (!getElement('question').value) return;
            startResearch();
        }
    });

    console.log('✅ Event listeners attached');
});

// ============================================================================
// ERROR HANDLING
// ============================================================================

window.addEventListener('error', function (e) {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', function (e) {
    console.error('Unhandled promise rejection:', e.reason);
});
