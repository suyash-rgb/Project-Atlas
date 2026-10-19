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
    <link rel="icon" type="image/png" href="<?php echo parse_url(base_url('assets/images/logo.png'), PHP_URL_PATH); ?>">
    <link rel="stylesheet" href="<?php echo parse_url(base_url('assets/css/style.css'), PHP_URL_PATH); ?>">
</head>
<body>

    <!-- 1. Top Enterprise Utility Bar -->
    <div class="top-utility-bar">
        <div class="contact-items">
            <span><i class="fa-solid fa-location-dot"></i> Viman Nagar, Pune, India & Sunnyvale, USA</span>
            <span><i class="fa-solid fa-envelope"></i> sales@cognitivemarketresearch.com</span>
        </div>
        <div>
            <span>ESOMAR Corporate Member | Atlas Research Suite</span>
        </div>
    </div>

    <!-- 2. Main Brand Header -->
    <header class="main-header">
        <a href="<?php echo parse_url(site_url(), PHP_URL_PATH); ?>" class="logo-wrap" title="Cognitive Market Research & Consulting">
            <img src="<?php echo parse_url(base_url('assets/images/logo.png'), PHP_URL_PATH); ?>" alt="Cognitive Market Research & Consulting" class="main-logo-img">
        </a>

        <nav class="header-nav">
            <a href="javascript:void(0)" class="nav-link active" id="navHome" onclick="navigateTo('home')">Home</a>
            <a href="javascript:void(0)" class="nav-link" id="navReports" onclick="navigateTo('copilot')">Market Reports</a>
            <a href="javascript:void(0)" class="nav-link" id="navCopilot" onclick="navigateTo('copilot')">Report Copilot (AI)</a>
            <a href="javascript:void(0)" class="nav-link" id="navAthenaeum" onclick="navigateTo('copilot')">Atlas Access</a>

            <!-- Corporate Client Account Profile & Switch Session -->
            <div id="authProfileContainer" class="user-profile-nav" style="display: none;">
                <i class="fa-solid fa-building" style="color: var(--cmr-primary-blue);"></i>
                <span class="company-name" id="currentCompanyName">Not Signed In</span>
                <span class="client-tag" id="currentClientIdBadge">Guest</span>
                <button class="btn-auth-action" onclick="signOutClient()" title="Sign Out of Client Account">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> Sign Out
                </button>
            </div>
            <button id="btnHeaderLogin" class="btn-login-trigger" onclick="openAuthModal()">
                <i class="fa-solid fa-user-lock"></i> Client Sign In
            </button>
        </nav>
    </header>

    <!-- Client Authentication Modal (Login / Signup) -->
    <div class="auth-modal-overlay" id="authModal">
        <div class="auth-modal-card">
            <div class="auth-modal-header">
                <button class="auth-modal-close" onclick="closeAuthModal()">&times;</button>
                <img src="<?php echo parse_url(base_url('assets/images/logo.png'), PHP_URL_PATH); ?>" alt="Cognitive Market Research" style="height: 34px; margin: 0 auto 0.75rem auto; display: block;">
                <h3><i class="fa-solid fa-shield-halved"></i> Client Portal Access</h3>
                <p>Use your business email and password to access your report workspace</p>
            </div>
            <div class="auth-tabs">
                <button type="button" class="auth-tab active" id="tabLogin" onclick="switchAuthTab('login')">Log In</button>
                <button type="button" class="auth-tab" id="tabSignup" onclick="switchAuthTab('signup')">Create Account</button>
            </div>
            <div class="auth-modal-body">
                <p class="auth-message" id="authMessage" role="status" aria-live="polite"></p>
                <form id="loginForm">
                    <div class="auth-form-group">
                        <label for="loginContactEmail">Business Email:</label>
                        <input type="email" id="loginContactEmail" autocomplete="username" maxlength="254" required>
                    </div>
                    <div class="auth-form-group">
                        <label for="loginPassword">Password:</label>
                        <input type="password" id="loginPassword" autocomplete="current-password" required>
                    </div>
                    <button class="btn-auth-submit" type="submit">
                        <i class="fa-solid fa-lock-open"></i> Log In to Report Copilot
                    </button>
                </form>

                <form id="signupForm" style="display: none;">
                    <div class="auth-form-group">
                        <label for="signupCompanyName">Company Name:</label>
                        <input type="text" id="signupCompanyName" autocomplete="organization" maxlength="255" required>
                    </div>
                    <div class="auth-form-group">
                        <label for="signupEmail">Business Email:</label>
                        <input type="email" id="signupEmail" autocomplete="email" maxlength="254" required>
                    </div>
                    <div class="auth-form-group">
                        <label for="signupPassword">Password (12–72 characters):</label>
                        <input type="password" id="signupPassword" autocomplete="new-password" minlength="12" maxlength="72" required>
                    </div>
                    <div class="auth-form-group">
                        <label for="signupPasswordConfirmation">Confirm Password:</label>
                        <input type="password" id="signupPasswordConfirmation" autocomplete="new-password" minlength="12" maxlength="72" required>
                    </div>
                    <button class="btn-auth-submit" type="submit">
                        <i class="fa-solid fa-user-plus"></i> Create Client Account
                    </button>
                </form>

                <div class="auth-hint">
                    <i class="fa-solid fa-circle-info"></i> Your business email is used as your login name and is not email-verified. New accounts can access public report excerpts; paid reports require an existing entitlement.
                </div>
            </div>
        </div>
    </div>

    <!-- VIEW 1: Enterprise Landing Page (Default Home Page) -->
    <div id="viewLanding" class="landing-view-container">
        <!-- Hero Section -->
        <section class="landing-hero">
            <div class="landing-hero-content-wrap">
                <!-- Hero Left Column -->
                <div class="landing-hero-left">
                    <div class="landing-pills-row">
                        <span class="landing-pill">Success of 10+ Years</span>
                        <span class="landing-pill">End to End Market Research</span>
                        <span class="landing-pill">Proprietary Data</span>
                        <span class="landing-pill">Atlas AI Platform</span>
                    </div>
                    <h1>Uncover The Full Truth of<br>Market with Cognitive</h1>
                    <p>
                        End-to-end research solutions for global enterprises. Surveys, expert consultation, deep-dive analytics all in one place.
                    </p>
                    <div class="landing-hero-actions">
                        <button class="btn-hero-primary" onclick="openAuthModal()">
                            <i class="fa-solid fa-chart-line"></i> Atlas AI
                        </button>
                        <button class="btn-hero-secondary" onclick="openAuthModal()">
                            <i class="fa-solid fa-headset"></i> Talk to an Expert
                        </button>
                    </div>
                </div>

                <!-- Hero Right Column: Search Market Data Card -->
                <div class="landing-search-card">
                    <div class="landing-search-card-header">
                        <i class="fa-solid fa-chart-pie"></i>
                        <span>Search Market Data</span>
                    </div>
                    <div class="landing-search-subtitle">
                        Access 50,000+ research reports across 30+ industries
                    </div>
                    <div class="landing-search-bar">
                        <input type="text" id="landingSearchInput" placeholder="e.g. Coal market, EV battery...">
                        <button type="button" onclick="searchReportsFromLanding()" aria-label="Search available reports"><i class="fa-solid fa-magnifying-glass"></i></button>
                    </div>
                    <div class="landing-search-tags">
                        <button class="landing-tag-btn" onclick="openAuthModal()"><i class="fa-solid fa-chart-simple"></i> Market Surveys</button>
                        <button class="landing-tag-btn" onclick="openAuthModal()"><i class="fa-solid fa-brain"></i> Atlas AI</button>
                        <button class="landing-tag-btn" onclick="openAuthModal()"><i class="fa-solid fa-users"></i> Consultation</button>
                        <button class="landing-tag-btn" onclick="openAuthModal()"><i class="fa-solid fa-flask"></i> Methodology</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- Four Pillars of Our Research Ecosystem -->
        <section class="landing-ecosystem-section">
            <div class="landing-subheading-tag">The Full Truth Model</div>
            <h2>Four Pillars of Our Research Ecosystem</h2>
            <div class="pillars-grid">
                <div class="pillar-card" onclick="openAuthModal()">
                    <div class="pillar-icon-box"><i class="fa-solid fa-chart-simple"></i></div>
                    <h3>Market Surveys</h3>
                    <p>CATI, CAVI, CAPI, in-depth interviews and online panels delivering primary data at scale.</p>
                </div>
                <div class="pillar-card" onclick="openAuthModal()">
                    <div class="pillar-icon-box"><i class="fa-solid fa-users-gear"></i></div>
                    <h3>Expert Consultation</h3>
                    <p>Direct access to 10,000+ validated industry experts across 30+ verticals worldwide.</p>
                </div>
                <div class="pillar-card" onclick="openAuthModal()">
                    <div class="pillar-icon-box"><i class="fa-solid fa-newspaper"></i></div>
                    <h3>Market Analysis</h3>
                    <p>Syndicated and custom reports with granular data, forecasts, and competitive intelligence.</p>
                </div>
                <div class="pillar-card" onclick="openAuthModal()">
                    <div class="pillar-icon-box"><i class="fa-solid fa-brain"></i></div>
                    <h3>Atlas AI</h3>
                    <p>AI-powered insights platform (PaaS) with real-time intelligence and interactive dashboards.</p>
                </div>
            </div>
        </section>

        <!-- About Cognitive: End-to-End Market Research Solution (Iceberg Section) -->
        <section class="landing-iceberg-section">
            <div class="iceberg-container">
                <!-- Left Visual: Iceberg Card with 10+ Years Badge -->
                <div class="iceberg-visual-wrap">
                    <div class="iceberg-card">
                        <img src="<?php echo parse_url(base_url('assets/images/iceberg.jpg'), PHP_URL_PATH); ?>" alt="Cognitive Market Research Full Truth Iceberg Methodology" class="iceberg-img">
                    </div>
                    <div class="iceberg-badge">
                        <div class="num">10+</div>
                        <div class="txt">Years of Excellence</div>
                    </div>
                </div>

                <!-- Right Content: Solution Details -->
                <div class="iceberg-content">
                    <div class="tag">About Cognitive</div>
                    <h2>End-to-End Market Research Solution</h2>
                    <p class="iceberg-intro">
                        At Cognitive Market Research and Consulting, we deliver more than just data &mdash; we deliver strategic certainty. For over a decade, we have empowered global enterprises with end-to-end research solutions powered by our proprietary methodology, <strong>The Full Truth</strong>.
                    </p>

                    <div class="iceberg-services-list">
                        <div class="iceberg-service-row">
                            <div class="iceberg-service-icon"><i class="fa-solid fa-chart-simple"></i></div>
                            <div><strong>Market Surveys</strong> &mdash; CATI, CAVI, CAPI, Interviews & more</div>
                        </div>
                        <div class="iceberg-service-row">
                            <div class="iceberg-service-icon"><i class="fa-solid fa-users-gear"></i></div>
                            <div><strong>Industry Experts Consultation Services</strong></div>
                        </div>
                        <div class="iceberg-service-row">
                            <div class="iceberg-service-icon"><i class="fa-solid fa-chart-line"></i></div>
                            <div><strong>Market Analysis DATA and Consultation</strong></div>
                        </div>
                        <div class="iceberg-service-row">
                            <div class="iceberg-service-icon"><i class="fa-solid fa-brain"></i></div>
                            <div><strong>Atlas AI (PaaS)</strong> &mdash; Powerful Insights Platform</div>
                        </div>
                    </div>

                    <!-- Iceberg Callout Box -->
                    <div class="iceberg-callout-box">
                        <div class="iceberg-callout-title">
                            <i class="fa-solid fa-cube"></i> ICEBERG Defines Us!
                        </div>
                        <p class="iceberg-callout-desc">
                            Our proprietary research methodology delves deep beneath the surface, combining survey insights, industry analysts, and market analysts &mdash; each validated and perfected by domain experts.
                        </p>
                    </div>

                    <div class="iceberg-actions">
                        <button class="btn-read-more" onclick="openAuthModal()">
                            <i class="fa-solid fa-arrow-right"></i> Read More
                        </button>
                        <button class="btn-more-services" onclick="openAuthModal()">
                            More Services
                        </button>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <!-- VIEW 2: Authenticated Copilot Chat View (Loaded upon Login) -->
    <div id="viewCopilot" style="display: none;">
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
                <i class="fa-solid fa-folder-open"></i> Available Reports
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
                        <span class="badge-pill conf">SYSTEM READY</span>
                        <span class="badge-pill router">ACCOUNT REPORTS</span>
                    </div>
                    <div class="answer-content">
                        Welcome to the <strong>Cognitive Market Research Report Copilot</strong>. Your workspace shows the reports available to your account. Ask factual questions, request growth-rate calculations, or compare accessible report excerpts.
                        <br><br>
                        <em>Sample queries to try (click to run):</em>
                        <ul style="margin-left: 1.25rem; margin-top: 0.5rem; font-size: 0.88rem; display: flex; flex-direction: column; gap: 0.4rem;">
                            <li onclick="triggerQuickQuery('What does the R-102 public excerpt say about the smart water meter market?')" style="cursor: pointer; color: var(--cmr-primary-blue); font-weight: 500; transition: all 0.2s;"><i class="fa-solid fa-arrow-right" style="font-size: 0.75rem;"></i> "What does the R-102 public excerpt say about the smart water meter market?"</li>
                            <li onclick="triggerQuickQuery('Compare the public market size estimates in R-102 and R-105.')" style="cursor: pointer; color: var(--cmr-primary-blue); font-weight: 500; transition: all 0.2s;"><i class="fa-solid fa-arrow-right" style="font-size: 0.75rem;"></i> "Compare the public market size estimates in R-102 and R-105."</li>
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
    <script src="<?php echo parse_url(base_url('assets/js/markdown.js'), PHP_URL_PATH); ?>"></script>
    <script>
        const chatStream = document.getElementById('chatStream');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const entitlementList = document.getElementById('entitlementList');
        const authModal = document.getElementById('authModal');
        const authMessage = document.getElementById('authMessage');
        const loginForm = document.getElementById('loginForm');
        const signupForm = document.getElementById('signupForm');
        const currentCompanyName = document.getElementById('currentCompanyName');
        const currentClientIdBadge = document.getElementById('currentClientIdBadge');
        const authProfileContainer = document.getElementById('authProfileContainer');
        const btnHeaderLogin = document.getElementById('btnHeaderLogin');
        const viewLanding = document.getElementById('viewLanding');
        const viewCopilot = document.getElementById('viewCopilot');
        const navHome = document.getElementById('navHome');
        const navCopilot = document.getElementById('navCopilot');
        const csrfTokenName = document.querySelector('meta[name="csrf-token-name"]')?.getAttribute('content') || 'csrf_test_name';
        const csrfHash = document.querySelector('meta[name="csrf-hash"]')?.getAttribute('content') || '';
        const authUrls = {
            login: <?php echo json_encode(parse_url(site_url('auth/login'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>,
            register: <?php echo json_encode(parse_url(site_url('auth/register'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>,
            logout: <?php echo json_encode(parse_url(site_url('auth/logout'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>,
            reports: <?php echo json_encode(parse_url(site_url('chat/reports'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>,
            stream: <?php echo json_encode(parse_url(site_url('chat/stream'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>,
            recordConversation: <?php echo json_encode(parse_url(site_url('chat/record_conversation'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>,
            feedback: <?php echo json_encode(parse_url(site_url('chat/feedback'), PHP_URL_PATH), JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>
        };
        const initialClient = <?php echo json_encode(
            $client,
            JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT
        ); ?>;

        let activeClient = initialClient && typeof initialClient === 'object' ? initialClient : null;
        let pendingQuery = null;

        // View Navigation
        function navigateTo(targetView) {
            if (targetView === 'copilot') {
                if (!activeClient) {
                    openAuthModal();
                    return;
                }
                viewLanding.style.display = 'none';
                viewCopilot.style.display = 'block';
                navCopilot.classList.add('active');
                navHome.classList.remove('active');
            } else {
                viewLanding.style.display = 'block';
                viewCopilot.style.display = 'none';
                navHome.classList.add('active');
                navCopilot.classList.remove('active');
            }
        }

        // Modal Controls
        function openAuthModal() {
            setAuthMessage('');
            authModal.style.display = 'flex';
        }

        function closeAuthModal() {
            authModal.style.display = 'none';
            pendingQuery = null;
        }

        function switchAuthTab(tab) {
            const tabLogin = document.getElementById('tabLogin');
            const tabSignup = document.getElementById('tabSignup');
            setAuthMessage('');

            if (tab === 'login') {
                tabLogin.classList.add('active');
                tabSignup.classList.remove('active');
                loginForm.style.display = 'block';
                signupForm.style.display = 'none';
            } else {
                tabSignup.classList.add('active');
                tabLogin.classList.remove('active');
                loginForm.style.display = 'none';
                signupForm.style.display = 'block';
            }
        }

        async function submitClientLogin(event) {
            event.preventDefault();
            setAuthMessage('');
            const submitButton = loginForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;

            try {
                const result = await postAuth(authUrls.login, {
                    email: document.getElementById('loginContactEmail').value,
                    password: document.getElementById('loginPassword').value
                });
                activateClient(result.client, `Welcome back, **${result.client.company}**.`);
                loginForm.reset();
                closeAuthModal();
            } catch (error) {
                setAuthMessage(error.message, true);
            } finally {
                submitButton.disabled = false;
            }
        }

        async function signOutClient() {
            try {
                await postAuth(authUrls.logout, {});
            } catch (error) {
                setAuthMessage(error.message, true);
                authModal.style.display = 'flex';
                return;
            }

            activeClient = null;
            authProfileContainer.style.display = 'none';
            btnHeaderLogin.style.display = 'flex';
            updateSidebarEntitlements();
            chatStream.innerHTML = '';
            chatInput.value = '';
            navigateTo('home');
        }

        async function submitClientSignup(event) {
            event.preventDefault();
            setAuthMessage('');
            const submitButton = signupForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;

            try {
                const result = await postAuth(authUrls.register, {
                    company: document.getElementById('signupCompanyName').value,
                    email: document.getElementById('signupEmail').value,
                    password: document.getElementById('signupPassword').value,
                    password_confirmation: document.getElementById('signupPasswordConfirmation').value
                });
                activateClient(
                    result.client,
                    `Welcome to Project Atlas, **${result.client.company}**. Your account is ready; public report excerpts are available in your library.`
                );
                signupForm.reset();
                closeAuthModal();
            } catch (error) {
                setAuthMessage(error.message, true);
            } finally {
                submitButton.disabled = false;
            }
        }

        function activateClient(client, welcomeMessage) {
            activeClient = client;
            currentCompanyName.textContent = activeClient.company;
            currentClientIdBadge.textContent = activeClient.id;
            authProfileContainer.style.display = 'flex';
            btnHeaderLogin.style.display = 'none';
            updateSidebarEntitlements();
            chatStream.innerHTML = '';
            if (welcomeMessage) {
                appendAssistantResponse({ answer: welcomeMessage, confidence: 1.0 });
            }
            chatInput.value = '';
            navigateTo('copilot');
            if (pendingQuery) {
                const query = pendingQuery;
                pendingQuery = null;
                window.setTimeout(() => triggerQuickQuery(query), 0);
            }
        }

        function setAuthMessage(message, isError) {
            authMessage.textContent = message;
            authMessage.classList.toggle('is-error', Boolean(isError));
        }

        async function postAuth(url, payload) {
            const headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            };

            const response = await fetch(url, {
                method: 'POST',
                headers: headers,
                body: formRequestBody(payload)
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(result.message || `Request failed (${response.status}).`);
            }
            return result;
        }

        function formRequestBody(payload) {
            const form = new URLSearchParams();
            Object.keys(payload).forEach(key => {
                form.append(key, payload[key]);
            });
            form.append(csrfTokenName, csrfHash);
            return form.toString();
        }

        async function updateSidebarEntitlements() {
            if (!activeClient) {
                entitlementList.innerHTML = '';
                entitlementList.style.color = '';
                return;
            }
            const clientId = activeClient.id;
            entitlementList.innerHTML = '<div style="font-size: 0.78rem; color: #64748b; padding: 0.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading entitled reports...</div>';

            try {
                const response = await fetch(authUrls.reports, {
                    headers: { 'Accept': 'application/json' }
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.message || `Report lookup failed (${response.status}).`);
                }
                if (!activeClient || activeClient.id !== clientId) {
                    return;
                }
                renderReportCards(data.reports || []);
            } catch (err) {
                if (!activeClient || activeClient.id !== clientId) {
                    return;
                }
                entitlementList.textContent = 'Could not load this account’s reports. Please refresh or sign in again.';
                entitlementList.style.color = '#b91c1c';
            }
        }

        function searchReportsFromLanding() {
            const searchInput = document.getElementById('landingSearchInput');
            const searchTerm = searchInput.value.trim();
            if (!searchTerm) {
                searchInput.focus();
                return;
            }

            const query = `Search my available reports for ${searchTerm}.`;
            if (!activeClient) {
                pendingQuery = query;
                openAuthModal();
                return;
            }
            navigateTo('copilot');
            triggerQuickQuery(query);
        }

        function renderReportCards(reports) {
            entitlementList.innerHTML = '';
            if (!reports || reports.length === 0) {
                entitlementList.innerHTML = '<div style="font-size: 0.78rem; color: #94a3b8; font-style: italic;">No reports are available for this account.</div>';
                return;
            }

            entitlementList.style.color = '';
            reports.forEach(r => {
                const card = document.createElement('div');
                card.className = 'entitled-report-card';
                const isPurchased = r.is_purchased !== false && (r.entitlement_type || '').includes('Purchased');
                const badgeColor = isPurchased ? '#0284c7' : '#0d9488';
                const lockIcon = isPurchased ? '<i class="fa-solid fa-lock-open"></i> Licensed' : '<i class="fa-solid fa-file-lines"></i> Public Excerpt';
                const reportId = escapeHtml(r.id || '');
                const title = escapeHtml(r.title || 'Untitled report');
                const sector = escapeHtml(r.sector || 'Market Report');
                const entitlement = escapeHtml(r.entitlement_type || 'Licensed');

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="report-badge-id">${reportId}</span>
                        <span style="font-size: 0.7rem; color: ${badgeColor}; font-weight: 600;">${entitlement}</span>
                    </div>
                    <div class="title">${title}</div>
                    <div class="meta">
                        <span>${sector}</span>
                        <span style="color: #059669; font-weight: 600;">${lockIcon}</span>
                    </div>
                `;
                entitlementList.appendChild(card);
            });
        }

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

        function triggerQuickQuery(text) {
            if (!activeClient) {
                openAuthModal();
                return;
            }
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

        function appendAssistantResponse(data, question) {
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble assistant-bubble';
            if (typeof question === 'string') {
                bubble.dataset.query = question;
            }

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

            const rawAnswer = data.answer || data.message || 'No answer generated.';
            const formattedAnswer = window.renderAtlasMarkdown(rawAnswer);

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

            if (typeof question === 'string' && question.trim()) {
                const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7);
                html += `
                    <div class="feedback-bar" data-msg-id="${messageId}">
                        <span>Was this response helpful and accurate?</span>
                        <button class="feedback-btn" onclick="submitFeedback(1, this, '${messageId}')"><i class="fa-regular fa-thumbs-up"></i> Helpful</button>
                        <button class="feedback-btn" onclick="submitFeedback(0, this, '${messageId}')"><i class="fa-regular fa-thumbs-down"></i> Inaccurate</button>
                    </div>
                `;
            }

            bubble.innerHTML = html;
            chatStream.appendChild(bubble);
            chatStream.scrollTop = chatStream.scrollHeight;
            return bubble;
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
            if (!activeClient) {
                openAuthModal();
                return;
            }
            const query = chatInput.value.trim();
            if (!query) return;

            appendUserMessage(query);
            chatInput.value = '';
            sendBtn.disabled = true;

            const streaming = createStreamingBubble();
            let completeResponse = null;
            let receivedToken = false;

            try {
                const reqHeaders = {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Accept': 'text/event-stream',
                    'X-Requested-With': 'XMLHttpRequest'
                };

                const res = await fetch(authUrls.stream, {
                    method: 'POST',
                    headers: reqHeaders,
                    body: formRequestBody({ query: query })
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

                if (!completeResponse) {
                    throw new Error('The response ended without a final answer.');
                }
                streaming.bubble.remove();
                const responseBubble = appendAssistantResponse(completeResponse, query);

                try {
                    const recordResponse = await fetch(authUrls.recordConversation, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: formRequestBody({
                            question: query,
                            answer: completeResponse.answer || '',
                            confidence: completeResponse.confidence || 1.0,
                            escalated: completeResponse.escalated ? 1 : 0
                        })
                    });
                    if (!recordResponse.ok) {
                        const error = await recordResponse.json().catch(() => ({}));
                        throw new Error(error.message || 'The conversation could not be saved.');
                    }
                } catch (error) {
                    const notice = document.createElement('div');
                    notice.className = 'stream-error';
                    notice.textContent = error.message;
                    responseBubble.appendChild(notice);
                }
            } catch (err) {
                const message = err.message || 'Connection error communicating with Report Copilot.';
                if (receivedToken) {
                    const notice = document.createElement('div');
                    notice.className = 'stream-error';
                    notice.textContent = `Response interrupted: ${message}`;
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
            const bar = btn.closest('.feedback-bar');
            const bubble = bar.closest('.chat-bubble');
            const currentQuery = bubble.dataset.query || '';
            const buttons = bar.querySelectorAll('.feedback-btn');
            let status = bar.querySelector('.feedback-status');
            if (!status) {
                status = document.createElement('span');
                status.className = 'feedback-status';
                bar.appendChild(status);
            }
            buttons.forEach(button => {
                button.disabled = true;
            });
            status.textContent = 'Saving feedback...';

            try {
                const response = await fetch(authUrls.feedback, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formRequestBody({
                        message_id: messageId || ('msg-' + Date.now()),
                        rating: rating === 1 ? 'up' : 'down',
                        comment: rating === 1 ? 'Helpful and accurate response.' : 'Flagged as inaccurate or incomplete.',
                        query: currentQuery
                    })
                });
                const result = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(result.message || 'Feedback could not be saved.');
                }
                bar.innerHTML = '<span class="feedback-success"><i class="fa-solid fa-check"></i> Thank you! Your feedback was saved.</span>';
            } catch (error) {
                status.classList.add('is-error');
                status.textContent = error.message;
                buttons.forEach(button => {
                    button.disabled = false;
                });
            }
        }
        window.triggerQuickQuery = triggerQuickQuery;

        loginForm.addEventListener('submit', submitClientLogin);
        signupForm.addEventListener('submit', submitClientSignup);
        if (activeClient) {
            currentCompanyName.textContent = activeClient.company;
            currentClientIdBadge.textContent = activeClient.id;
            authProfileContainer.style.display = 'flex';
            btnHeaderLogin.style.display = 'none';
            updateSidebarEntitlements();
            navigateTo('copilot');
        }
        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        document.getElementById('landingSearchInput').addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                searchReportsFromLanding();
            }
        });
    </script>
</body>
</html>
