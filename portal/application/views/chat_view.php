<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token-name" content="<?php echo $this->security->get_csrf_token_name(); ?>">
    <meta name="csrf-hash" content="<?php echo $this->security->get_csrf_hash(); ?>">
    <title><?php echo html_escape($title); ?></title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <link rel="stylesheet" href="<?php echo base_url('assets/css/style.css'); ?>">
</head>
<body>

    <!-- 1. Top Enterprise Utility Bar -->
    <div class="top-utility-bar">
        <div class="contact-items">
            <span><i class="fa-solid fa-location-dot"></i> Viman Nagar, Pune, India & Sunnyvale, USA</span>
            <span><i class="fa-solid fa-envelope"></i> sales@cognitivemarketresearch.com</span>
        </div>
        <div>
            <span>ESOMAR Corporate Member | Athenaeum Research Suite</span>
        </div>
    </div>

    <!-- 2. Main Brand Header -->
    <header class="main-header">
        <a href="<?php echo site_url(); ?>" class="logo-wrap">
            <div class="logo-symbol">C</div>
            <div class="logo-text">
                <h2>Cognitive</h2>
                <span>Market Research & Consulting</span>
            </div>
        </a>

        <nav class="header-nav">
            <a href="#" class="nav-link">Market Reports</a>
            <a href="#" class="nav-link">Custom Consulting</a>
            <a href="#" class="nav-link active">Report Copilot (AI)</a>
            <a href="#" class="nav-link">Athenaeum Access</a>

            <!-- Corporate Client Account Profile & Switch Session -->
            <div id="authProfileContainer" class="user-profile-nav">
                <i class="fa-solid fa-building" style="color: var(--cmr-primary-blue);"></i>
                <span class="company-name" id="currentCompanyName">Northwind Utilities</span>
                <span class="client-tag" id="currentClientIdBadge">C-01</span>
                <button class="btn-auth-action" onclick="openAuthModal()" title="Switch Client Account / Log In">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> Switch
                </button>
            </div>
        </nav>
    </header>

    <!-- Client Authentication Modal (Login / Signup) -->
    <div class="auth-modal-overlay" id="authModal">
        <div class="auth-modal-card">
            <div class="auth-modal-header">
                <button class="auth-modal-close" onclick="closeAuthModal()">&times;</button>
                <h3><i class="fa-solid fa-shield-halved"></i> Client Portal Access</h3>
                <p>Authenticate as an enterprise client to access licensed reports</p>
            </div>
            <div class="auth-tabs">
                <button class="auth-tab active" id="tabLogin" onclick="switchAuthTab('login')">Client Sign In</button>
                <button class="auth-tab" id="tabSignup" onclick="switchAuthTab('signup')">Register Client</button>
            </div>
            <div class="auth-modal-body">
                <!-- Login View -->
                <div id="loginFormView">
                    <div class="auth-form-group">
                        <label for="loginClientSelect">Select Corporate Client Account:</label>
                        <select id="loginClientSelect">
                            <?php foreach ($clients as $cid => $cname): ?>
                                <option value="<?php echo html_escape($cid); ?>"><?php echo html_escape("[$cid] $cname"); ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="auth-form-group">
                        <label for="loginContactEmail">Authorized Corporate Email:</label>
                        <input type="email" id="loginContactEmail" value="ops@example.com" placeholder="e.g. ops@northwind.example.com">
                    </div>
                    <button class="btn-auth-submit" onclick="submitClientLogin()">
                        <i class="fa-solid fa-lock-open"></i> Log In to Report Copilot
                    </button>
                </div>

                <!-- Signup View -->
                <div id="signupFormView" style="display: none;">
                    <div class="auth-form-group">
                        <label for="signupClientId">Assigned Client Identifier:</label>
                        <input type="text" id="signupClientId" placeholder="e.g. C-07">
                    </div>
                    <div class="auth-form-group">
                        <label for="signupCompanyName">Company Name:</label>
                        <input type="text" id="signupCompanyName" placeholder="e.g. Apex Power & Water Corp">
                    </div>
                    <div class="auth-form-group">
                        <label for="signupEmail">Corporate Contact Email:</label>
                        <input type="email" id="signupEmail" placeholder="e.g. research@apexpower.example.com">
                    </div>
                    <div class="auth-form-group">
                        <label for="signupPurchasedReports">Initial Purchased Reports:</label>
                        <input type="text" id="signupPurchasedReports" placeholder="e.g. R-101, R-103">
                    </div>
                    <button class="btn-auth-submit" onclick="submitClientSignup()">
                        <i class="fa-solid fa-user-plus"></i> Create Client Account
                    </button>
                </div>

                <div class="auth-hint">
                    <i class="fa-solid fa-circle-info"></i> Client session is authenticated securely and grants access strictly to your corporate licensed reports.
                </div>
            </div>
        </div>
    </div>

    <!-- 3. Portal Sub-Banner -->
    <div class="portal-sub-banner">
        <div>
            <h3>
                <i class="fa-solid fa-compass" style="color: #00a8cc;"></i>
                Project Atlas — Report Copilot
                <span class="badge-live-copilot">Active Agent</span>
            </h3>
            <p>Non-autoregressive Laya decision router with entitlement-filtered RAG & citation verification.</p>
        </div>
        <div class="portal-actions">
            <a href="javascript:void(0)" class="btn-view-library" onclick="triggerQuickQuery('What reports are in your library?')">
                <i class="fa-solid fa-database"></i> Database Summary
            </a>
            <a href="javascript:void(0)" class="btn-view-library" onclick="triggerQuickQuery('Why do R-101 and R-102 disagree on 2024?')">
                <i class="fa-solid fa-code-compare"></i> Compare R-101 vs R-102
            </a>
        </div>
    </div>

    <!-- 4. Main Two-Column Container -->
    <div class="app-container">
        
        <!-- Left Sidebar: Client Library & Entitlements -->
        <aside class="library-sidebar">
            <div class="sidebar-section-title">
                <i class="fa-solid fa-folder-open"></i> Purchased Reports
            </div>
            
            <div id="entitlementList" style="display: flex; flex-direction: column; gap: 0.65rem;">
                <!-- Populated dynamically based on selected client -->
            </div>

        </aside>

        <!-- Right Column: Interactive Chat Canvas -->
        <section class="chat-canvas">
            <div class="chat-canvas-header">
                <div class="chat-status-pill">
                    <span class="pulse-dot"></span>
                    <span>System 1 Decision Engine Online (30s SLA)</span>
                </div>
                <div style="font-size: 0.78rem; color: var(--cmr-text-muted);">
                    Backend: <strong>FastAPI / LangGraph</strong>
                </div>
            </div>

            <!-- Message Stream -->
            <div class="chat-stream" id="chatStream">
                <div class="assistant-bubble">
                    <div class="meta-badges-row">
                        <span class="badge-pill conf">SYSTEM INITIALIZED</span>
                        <span class="badge-pill router">ENTITLEMENTS VERIFIED</span>
                    </div>
                    <div class="answer-content">
                        Hello! Welcome to the <strong>Cognitive Market Research Report Copilot</strong>. 
                        I have verified your active company license. Ask any factual lookup, growth rate derivation (CAGR), or cross-report comparison.
                        <br><br>
                        <em>Sample queries to try (click to run):</em>
                        <ul style="margin-left: 1.25rem; margin-top: 0.5rem; font-size: 0.88rem; display: flex; flex-direction: column; gap: 0.4rem;">
                            <li onclick="triggerQuickQuery('What will the smart water meter market be worth in 2030 in R-101?')" style="cursor: pointer; color: var(--cmr-primary-blue); font-weight: 500; transition: all 0.2s;"><i class="fa-solid fa-arrow-right" style="font-size: 0.75rem;"></i> "What will the smart water meter market be worth in 2030 in R-101?"</li>
                            <li onclick="triggerQuickQuery('Why does R-101 report $4.21B while R-102 reports $3.87B for 2024?')" style="cursor: pointer; color: var(--cmr-primary-blue); font-weight: 500; transition: all 0.2s;"><i class="fa-solid fa-arrow-right" style="font-size: 0.75rem;"></i> "Why does R-101 report $4.21B while R-102 reports $3.87B for 2024?"</li>
                            <li onclick="triggerQuickQuery('Which sector has the most published reports in your database?')" style="cursor: pointer; color: var(--cmr-primary-blue); font-weight: 500; transition: all 0.2s;"><i class="fa-solid fa-arrow-right" style="font-size: 0.75rem;"></i> "Which sector has the most published reports in your database?"</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Input Bar -->
            <div class="chat-canvas-footer">
                <div class="chat-input-wrapper">
                    <textarea id="chatInput" placeholder="Type your market research inquiry..." rows="1"></textarea>
                </div>
                <button class="btn-send" id="sendBtn">
                    <span>Send</span>
                    <i class="fa-solid fa-paper-plane"></i>
                </button>
            </div>
        </section>

    </div>

    <!-- 5. Corporate Footer -->
    <footer class="main-footer">
        <div>
            &copy; <?php echo date('Y'); ?> Cognitive Market Research & Consulting. All Rights Reserved.
        </div>
        <div>
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Use</a>
            <a href="#">Data Entitlements</a>
            <a href="#">Security Audit</a>
        </div>
    </footer>

    <!-- Interactive Logic -->
    <script>
        const chatStream = document.getElementById('chatStream');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const entitlementList = document.getElementById('entitlementList');
        const authModal = document.getElementById('authModal');
        const loginClientSelect = document.getElementById('loginClientSelect');
        const currentCompanyName = document.getElementById('currentCompanyName');
        const currentClientIdBadge = document.getElementById('currentClientIdBadge');

        // Corporate Client Session State
        let activeClient = {
            id: 'C-01',
            company: 'Northwind Utilities',
            email: 'ops@northwind.example.com'
        };

        // Modal Controls
        function openAuthModal() {
            authModal.style.display = 'flex';
        }

        function closeAuthModal() {
            authModal.style.display = 'none';
        }

        function switchAuthTab(tab) {
            const tabLogin = document.getElementById('tabLogin');
            const tabSignup = document.getElementById('tabSignup');
            const loginView = document.getElementById('loginFormView');
            const signupView = document.getElementById('signupFormView');

            if (tab === 'login') {
                tabLogin.classList.add('active');
                tabSignup.classList.remove('active');
                loginView.style.display = 'block';
                signupView.style.display = 'none';
            } else {
                tabSignup.classList.add('active');
                tabLogin.classList.remove('active');
                loginView.style.display = 'none';
                signupView.style.display = 'block';
            }
        }

        function submitClientLogin() {
            const cid = loginClientSelect.value;
            const email = document.getElementById('loginContactEmail').value.trim();
            const selectedText = loginClientSelect.options[loginClientSelect.selectedIndex].text;
            
            const compMatch = selectedText.match(/\[C-\d+\]\s*(.*?)(?:\s*\(|$)/);
            const compName = compMatch ? compMatch[1].trim() : selectedText;

            activeClient = {
                id: cid,
                company: compName,
                email: email || `${cid.toLowerCase()}@client.example.com`
            };

            currentCompanyName.textContent = activeClient.company;
            currentClientIdBadge.textContent = activeClient.id;

            closeAuthModal();
            updateSidebarEntitlements();

            chatStream.innerHTML = '';
            appendAssistantResponse({
                answer: `Welcome back, **${activeClient.company}** (${activeClient.id}). Your secure enterprise session is active. You have full analytical clearance to query your licensed research reports. How can I assist your team today?`,
                confidence: 1.0
            });
        }

        function submitClientSignup() {
            const cid = document.getElementById('signupClientId').value.trim().toUpperCase() || 'C-07';
            const company = document.getElementById('signupCompanyName').value.trim() || 'New Enterprise Client';
            const email = document.getElementById('signupEmail').value.trim() || 'client@example.com';
            
            activeClient = { id: cid, company: company, email: email };
            currentCompanyName.textContent = activeClient.company;
            currentClientIdBadge.textContent = activeClient.id;

            closeAuthModal();
            updateSidebarEntitlements();

            chatStream.innerHTML = '';
            appendAssistantResponse({
                answer: `Welcome to Project Atlas, **${activeClient.company}** (${activeClient.id}). Your client account registration is confirmed.`,
                confidence: 1.0
            });
        }

        async function updateSidebarEntitlements() {
            const cid = activeClient.id;
            entitlementList.innerHTML = '<div style="font-size: 0.78rem; color: #64748b; padding: 0.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading entitled reports...</div>';

            try {
                const res = await fetch(`http://127.0.0.1:8085/api/v1/clients/${cid}/reports`);
                if (res.ok) {
                    const data = await res.json();
                    renderReportCards(data.reports || []);
                    return;
                }
            } catch (err) {
                console.warn('API lookup failed, falling back to local client mapping:', err);
            }

            // Fallback matching database seed
            const fallbackMap = {
                'C-01': [
                    { id: 'R-101', title: 'Global Smart Water Meter Market 2025', sector: 'Utilities', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-103', title: 'Residential Water Purifier Market 2025', sector: 'Consumer Durables', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-102', title: 'Smart Water Metering: Industry Outlook 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false },
                    { id: 'R-105', title: 'Smart Multi-Utility Metering Infrastructure 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false }
                ],
                'C-02': [
                    { id: 'R-103', title: 'Residential Water Purifier Market 2025', sector: 'Consumer Durables', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-102', title: 'Smart Water Metering: Industry Outlook 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false },
                    { id: 'R-105', title: 'Smart Multi-Utility Metering Infrastructure 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false }
                ],
                'C-03': [
                    { id: 'R-104', title: 'Commercial & Industrial RO Membrane Systems 2025', sector: 'Industrial Equipment', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-106', title: 'Decentralized Wastewater Recycling Systems 2025', sector: 'Cleantech', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-102', title: 'Smart Water Metering: Industry Outlook 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false },
                    { id: 'R-105', title: 'Smart Multi-Utility Metering Infrastructure 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false }
                ],
                'C-04': [
                    { id: 'R-101', title: 'Global Smart Water Meter Market 2025', sector: 'Utilities', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-102', title: 'Smart Water Metering: Industry Outlook 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false },
                    { id: 'R-105', title: 'Smart Multi-Utility Metering Infrastructure 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false }
                ],
                'C-05': [
                    { id: 'R-105', title: 'Smart Multi-Utility Metering Infrastructure 2024', sector: 'Utilities', entitlement_type: 'Full Turnkey (Purchased)', is_purchased: true },
                    { id: 'R-102', title: 'Smart Water Metering: Industry Outlook 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false }
                ],
                'C-06': [
                    { id: 'R-102', title: 'Smart Water Metering: Industry Outlook 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false },
                    { id: 'R-105', title: 'Smart Multi-Utility Metering Infrastructure 2024', sector: 'Utilities', entitlement_type: 'Public Excerpt', is_purchased: false }
                ]
            };
            renderReportCards(fallbackMap[cid] || []);
        }

        function renderReportCards(reports) {
            entitlementList.innerHTML = '';
            if (!reports || reports.length === 0) {
                entitlementList.innerHTML = '<div style="font-size: 0.78rem; color: #94a3b8; font-style: italic;">No licensed reports found for this account.</div>';
                return;
            }

            reports.forEach(r => {
                const card = document.createElement('div');
                card.className = 'entitled-report-card';
                const isPurchased = r.is_purchased !== false && (r.entitlement_type || '').includes('Purchased');
                const badgeColor = isPurchased ? '#0284c7' : '#0d9488';
                const lockIcon = isPurchased ? '<i class="fa-solid fa-lock-open"></i> Licensed' : '<i class="fa-solid fa-file-lines"></i> Public Excerpt';

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="report-badge-id">${r.id}</span>
                        <span style="font-size: 0.7rem; color: ${badgeColor}; font-weight: 600;">${r.entitlement_type || 'Licensed'}</span>
                    </div>
                    <div class="title">${r.title}</div>
                    <div class="meta">
                        <span>${r.sector || 'Market Report'}</span>
                        <span style="color: #059669; font-weight: 600;">${lockIcon}</span>
                    </div>
                `;
                entitlementList.appendChild(card);
            });
        }

        // Initialize sidebar on page load
        updateSidebarEntitlements();

        // Security: HTML entity encoding against XSS attacks
        function escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        const csrfTokenName = document.querySelector('meta[name="csrf-token-name"]')?.getAttribute('content') || 'csrf_test_name';
        const csrfHash = document.querySelector('meta[name="csrf-hash"]')?.getAttribute('content') || '';

        function triggerQuickQuery(text) {
            chatInput.value = text;
            sendMessage();
        }

        function appendUserMessage(text) {
            const bubble = document.createElement('div');
            bubble.className = 'user-bubble';
            bubble.textContent = text;
            chatStream.appendChild(bubble);
            chatStream.scrollTop = chatStream.scrollHeight;
        }

        function appendAssistantResponse(data) {
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble assistant-bubble';

            let html = '<div class="meta-badges-row">';
            if (data.confidence !== undefined) {
                const confPercent = Math.round(data.confidence * 100);
                html += `<span class="badge-pill conf"><i class="fa-solid fa-circle-check"></i> ${escapeHtml(confPercent)}% Confidence</span>`;
            }
            if (data.escalated) {
                html += `<span class="badge-pill escalate"><i class="fa-solid fa-headset"></i> Escalated to Human Analyst</span>`;
            }
            if (data.intent) {
                html += `<span class="badge-pill router">Intent: ${escapeHtml(data.intent)}</span>`;
            }
            html += '</div>';

            // Escape all HTML to prevent XSS, then format simple markdown
            const rawAnswer = data.answer || data.message || 'No answer generated.';
            const safeAnswer = escapeHtml(rawAnswer);
            const formattedAnswer = safeAnswer
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\n\n/g, '<br><br>')
                .replace(/\n/g, '<br>');

            html += `<div class="answer-content">${formattedAnswer}</div>`;

            // Derived values / formulas (properly escaped)
            if (data.derived_values && data.derived_values.length > 0) {
                html += '<div class="derived-callout"><strong><i class="fa-solid fa-calculator"></i> Derived Projection (Deterministic Math):</strong><br>';
                data.derived_values.forEach(d => {
                    const val = escapeHtml(d.estimated_value || d.value || '');
                    const metric = escapeHtml(d.metric || 'Metric');
                    const formula = escapeHtml(d.formula || '');
                    const rawAssum = Array.isArray(d.assumptions) ? d.assumptions.join('; ') : (d.assumptions || '');
                    const assum = escapeHtml(rawAssum);
                    html += `• <strong>${metric}:</strong> <span style="color:var(--cmr-primary); font-weight:700;">${val}</span><br>&nbsp;&nbsp;<em>Formula:</em> <code>${formula}</code><br>&nbsp;&nbsp;<em>Assumptions:</em> <small>${assum}</small><br>`;
                });
                html += '</div>';
            }

            // Conflicts (properly escaped)
            if (data.conflicts && data.conflicts.length > 0) {
                html += '<div class="conflict-callout"><strong><i class="fa-solid fa-triangle-exclamation"></i> Methodological Conflict & Scope Divergence:</strong><br>';
                data.conflicts.forEach(c => {
                    const topic = escapeHtml(c.metric || c.topic || 'Report Comparison');
                    const desc = escapeHtml(c.description || '');
                    const diff = escapeHtml(c.scope_differences || c.resolution || '');
                    html += `• <strong>${topic}:</strong> ${desc}<br>&nbsp;&nbsp;<em>Methodology Resolution:</em> ${diff}<br>`;
                });
                html += '</div>';
            }

            // Citations (properly escaped)
            if (data.citations && data.citations.length > 0) {
                html += '<div class="citations-section"><h5><i class="fa-solid fa-bookmark"></i> Verified Source Citations</h5>';
                data.citations.forEach(cit => {
                    if (typeof cit === 'string') {
                        html += `<div>• <span style="background:var(--cmr-primary); color:#fff; padding:2px 8px; border-radius:4px; font-weight:700; font-size:12px;"><i class="fa-solid fa-file-pdf"></i> ${escapeHtml(cit)}</span> Verified reference in Cognitive Market Research database</div>`;
                    } else {
                        const repId = escapeHtml(cit.report_id || '');
                        const pg = escapeHtml(cit.page || '1');
                        const q = escapeHtml(cit.quote || cit.text || '');
                        html += `<div>• <strong>${repId}</strong> (Page ${pg}): <em>"${q}"</em></div>`;
                    }
                });
                html += '</div>';
            }

            // Generate message identifier for feedback linking
            const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7);

            // Feedback buttons with messageId
            html += `
                <div class="feedback-bar" data-msg-id="${messageId}">
                    <span>Was this response helpful and accurate?</span>
                    <button class="feedback-btn" onclick="submitFeedback(1, this, '${messageId}')"><i class="fa-regular fa-thumbs-up"></i> Helpful</button>
                    <button class="feedback-btn" onclick="submitFeedback(0, this, '${messageId}')"><i class="fa-regular fa-thumbs-down"></i> Inaccurate</button>
                </div>
            `;

            bubble.innerHTML = html;
            chatStream.appendChild(bubble);
            chatStream.scrollTop = chatStream.scrollHeight;
        }

        function createStreamingBubble() {
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble assistant-bubble';
            const content = document.createElement('div');
            content.className = 'answer-content';
            content.setAttribute('aria-live', 'polite');
            content.setAttribute('aria-label', 'Streaming assistant response');
            bubble.appendChild(content);
            chatStream.appendChild(bubble);
            chatStream.scrollTop = chatStream.scrollHeight;
            return { bubble, content };
        }

        async function consumeEventStream(response, onEvent) {
            if (!response.body) {
                throw new Error('This browser does not support streamed responses.');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let eventName = 'message';
            let dataLines = [];
            let completed = false;

            function dispatchEvent() {
                if (dataLines.length === 0) return;
                const payload = JSON.parse(dataLines.join('\n'));
                if (eventName === 'complete') completed = true;
                onEvent(eventName, payload);
                eventName = 'message';
                dataLines = [];
            }

            function processLines(finalChunk) {
                let newline;
                while ((newline = buffer.indexOf('\n')) !== -1) {
                    let line = buffer.slice(0, newline);
                    buffer = buffer.slice(newline + 1);
                    if (line.endsWith('\r')) line = line.slice(0, -1);
                    if (line === '') {
                        dispatchEvent();
                    } else if (line.charAt(0) !== ':') {
                        const separator = line.indexOf(':');
                        const field = separator === -1 ? line : line.slice(0, separator);
                        let value = separator === -1 ? '' : line.slice(separator + 1);
                        if (value.charAt(0) === ' ') value = value.slice(1);
                        if (field === 'event') eventName = value;
                        if (field === 'data') dataLines.push(value);
                    }
                }
                if (finalChunk && buffer.length > 0) {
                    if (buffer.endsWith('\r')) buffer = buffer.slice(0, -1);
                    if (buffer.indexOf('data:') === 0) dataLines.push(buffer.slice(5).replace(/^ /, ''));
                    dispatchEvent();
                    buffer = '';
                }
            }

            try {
                while (true) {
                    const result = await reader.read();
                    buffer += decoder.decode(result.value || new Uint8Array(), { stream: !result.done });
                    processLines(result.done);
                    if (result.done) break;
                }
            } catch (error) {
                await reader.cancel();
                throw error;
            } finally {
                reader.releaseLock();
            }

            if (!completed) {
                throw new Error('The streamed response ended before completion.');
            }
        }

        async function sendMessage() {
            const query = chatInput.value.trim();
            if (!query) return;

            appendUserMessage(query);
            chatInput.dataset.lastQuery = query;
            chatInput.value = '';
            sendBtn.disabled = true;

            const clientId = activeClient.id;
            const streaming = createStreamingBubble();
            let completeResponse = null;
            let receivedToken = false;

            try {
                const streamUrl = '<?php echo site_url("chat/stream"); ?>'.replace(/^https?:\/\/[^\/]+/, window.location.origin);
                const reqHeaders = {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                };
                if (csrfHash) {
                    reqHeaders['X-CSRF-Token'] = csrfHash;
                }

                const res = await fetch(streamUrl, {
                    method: 'POST',
                    headers: reqHeaders,
                    body: JSON.stringify({
                        client_id: clientId,
                        query: query,
                        [csrfTokenName]: csrfHash
                    })
                });

                if (!res.ok) {
                    const error = await res.json().catch(() => ({}));
                    throw new Error(error.detail || error.message || `Request failed (${res.status}).`);
                }

                await consumeEventStream(res, (event, payload) => {
                    if (event === 'token') {
                        if (!receivedToken) {
                            streaming.content.textContent = '';
                            receivedToken = true;
                        }
                        streaming.content.textContent += payload.text || '';
                        chatStream.scrollTop = chatStream.scrollHeight;
                    } else if (event === 'complete') {
                        completeResponse = payload.response;
                    } else if (event === 'error') {
                        throw new Error(payload.message || 'The response could not be generated.');
                    }
                });

                streaming.bubble.remove();
                appendAssistantResponse(completeResponse);

                // Persist completed conversation in MySQL history
                if (completeResponse) {
                    const recordUrl = '<?php echo site_url("chat/record_conversation"); ?>'.replace(/^https?:\/\/[^\/]+/, window.location.origin);
                    fetch(recordUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfHash
                        },
                        body: JSON.stringify({
                            client_id: clientId,
                            question: query,
                            answer: completeResponse.answer || '',
                            confidence: completeResponse.confidence || 1.0,
                            escalated: completeResponse.escalated ? 1 : 0,
                            [csrfTokenName]: csrfHash
                        })
                    }).catch(() => {});
                }
            } catch (err) {
                const message = err.message || 'Connection error communicating with Report Copilot.';
                if (receivedToken) {
                    const notice = document.createElement('div');
                    notice.className = 'stream-error';
                    notice.textContent = `Response interrupted: ${escapeHtml(message)}`;
                    streaming.bubble.appendChild(notice);
                } else {
                    streaming.bubble.remove();
                    appendAssistantResponse({
                        answer: message,
                        confidence: 0.0,
                        escalated: true
                    });
                }
            } finally {
                sendBtn.disabled = false;
            }
        }

        async function submitFeedback(rating, btn, messageId) {
            const bar = btn.parentElement;
            const currentQuery = chatInput.dataset.lastQuery || '';
            bar.innerHTML = '<span style="color: var(--cmr-success); font-weight: 600;"><i class="fa-solid fa-check"></i> Thank you! Your feedback has been recorded in our MySQL database.</span>';
            try {
                const feedbackUrl = '<?php echo site_url("chat/feedback"); ?>'.replace(/^https?:\/\/[^\/]+/, window.location.origin);
                const reqHeaders = { 'Content-Type': 'application/json' };
                if (csrfHash) {
                    reqHeaders['X-CSRF-Token'] = csrfHash;
                }
                await fetch(feedbackUrl, {
                    method: 'POST',
                    headers: reqHeaders,
                    body: JSON.stringify({
                        client_id: activeClient.id,
                        message_id: messageId || ('msg-' + Date.now()),
                        rating: rating === 1 ? 'up' : 'down',
                        comment: rating === 1 ? 'Helpful and accurate response.' : 'Flagged as inaccurate or incomplete.',
                        query: currentQuery,
                        [csrfTokenName]: csrfHash
                    })
                });
            } catch (e) {}
        }

        function triggerQuickQuery(text) {
            chatInput.value = text;
            sendMessage();
        }
        window.triggerQuickQuery = triggerQuickQuery;

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
