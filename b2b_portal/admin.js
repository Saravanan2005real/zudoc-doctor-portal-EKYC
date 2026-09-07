document.addEventListener('DOMContentLoaded', loadRequests);

async function loadRequests() {
    const grid = document.getElementById('requests-grid');
    grid.innerHTML = '<p style="color: var(--text-muted); padding: 20px;">Loading requests...</p>';

    try {
        const response = await fetch('/api/v1/b2b/admin/requests');
        const result = await response.json();

        if (response.ok) {
            renderRequests(result.data || []);
        } else {
            grid.innerHTML = `<p style="color: var(--danger); padding: 20px;">Error: ${result.detail || 'Failed to load requests'}</p>`;
        }
    } catch (err) {
        grid.innerHTML = `<p style="color: var(--danger); padding: 20px;">Network Error: ${err.message}</p>`;
    }
}

function renderRequests(requests) {
    const grid = document.getElementById('requests-grid');
    grid.innerHTML = '';

    if (requests.length === 0) {
        grid.innerHTML = '<p style="color: var(--text-muted); padding: 20px;">No requests found.</p>';
        return;
    }

    requests.forEach(req => {
        const card = document.createElement('div');
        card.className = 'card';
        
        let statusBadge = '';
        if (req.status === 'PENDING') statusBadge = '<span class="badge pending">PENDING</span>';
        else if (req.status === 'APPROVED') statusBadge = '<span class="badge approved">APPROVED</span>';
        else statusBadge = `<span class="badge">${req.status}</span>`;

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
                <h3 style="margin:0;">${escapeHTML(req.company_name)}</h3>
                ${statusBadge}
            </div>
            
            <div style="margin-bottom: 16px;">
                <p><strong>Contact:</strong> ${escapeHTML(req.contact_name)} (<a href="mailto:${escapeHTML(req.contact_email)}" style="color:var(--accent-color);">${escapeHTML(req.contact_email)}</a>)</p>
                <p><strong>Industry:</strong> ${escapeHTML(req.industry)}</p>
                <p><strong>Volume:</strong> ${escapeHTML(req.expected_volume)} / month</p>
            </div>
            
            <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-bottom: 16px;">
                <p style="margin:0; font-size:0.85rem; color:var(--text-muted); margin-bottom:4px;"><strong>Requirements:</strong></p>
                <p style="margin:0; font-size:0.9rem;">${escapeHTML(req.requirements || 'None provided.')}</p>
            </div>
            
            <div style="text-align: right;">
                ${req.status === 'PENDING' ? `<button class="btn" style="padding: 8px 16px; font-size: 0.9rem;" onclick="approveRequest(${req.id}, this)">Approve & Generate Key</button>` : ''}
            </div>
        `;
        grid.appendChild(card);
    });
}

async function approveRequest(id, btnElement) {
    if (!confirm('Are you sure you want to approve this company and grant API access?')) return;

    btnElement.textContent = 'Approving...';
    btnElement.disabled = true;

    try {
        const response = await fetch(`/api/v1/b2b/admin/requests/${id}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (response.ok) {
            // Show modal with API Key
            document.getElementById('modalApiKey').textContent = result.api_key;
            document.getElementById('apiKeyModal').style.display = 'flex';
            
            // Reload grid
            loadRequests();
        } else {
            alert('Failed to approve: ' + (result.detail || result.message));
            btnElement.textContent = 'Approve & Generate Key';
            btnElement.disabled = false;
        }
    } catch (err) {
        alert('Network Error: ' + err.message);
        btnElement.textContent = 'Approve & Generate Key';
        btnElement.disabled = false;
    }
}

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag])
    );
}
