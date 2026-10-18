<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo html_escape($title); ?></title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0f19;
            --panel-bg: rgba(20, 27, 45, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --accent: #2563eb;
            --accent-glow: rgba(37, 99, 235, 0.25);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Top Navigation Header */
        header {
            background: var(--panel-bg);
            border-bottom: 1px solid var(--border);
            backdrop-filter: blur(12px);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-badge {
            background: var(--accent);
            color: white;
            font-weight: 700;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.85rem;
            letter-spacing: 0.05em;
        }

        .brand h1 {
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-main);
        }

        .client-selector-wrap {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.875rem;
        }

        .client-selector-wrap select {
            background: #1e293b;
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 0.45rem 1rem;
            border-radius: 6px;
            font-size: 0.875rem;
            outline: none;
            cursor: pointer;
        }

        /* Main Container */
        main {
            flex: 1;
            max-width: 1050px;
            width: 100%;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            padding: 1.5rem 1rem;
            height: calc(100vh - 75px);
        }

        /* Message Stream */
        .chat-stream {
            flex: 1;
            overflow-y: auto;
            padding-right: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .chat-bubble {
            max-width: 85%;
            padding: 1.1rem 1.35rem;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 0.935rem;
            animation: fadeIn 0.25s ease forwards;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .user-bubble {
            align-self: flex-end;
            background: var(--accent);
            color: white;
            border-bottom-right-radius: 2px;
            box-shadow: 0 4px 12px var(--accent-glow);
        }

        .assistant-bubble {
            align-self: flex-start;
            background: var(--panel-bg);
            border: 1px solid var(--border);
            color: var(--text-main);
            border-bottom-left-radius: 2px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }

        /* Structured Sections inside Assistant Bubble */
        .badge-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }

        .meta-badge {
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-confidence { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .badge-guardrail  { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .badge-derived    { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .badge-conflict   { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

        .citations-card {
            margin-top: 1rem;
            padding: 0.75rem 1rem;
            background: rgba(15, 23, 42, 0.6);
            border-left: 3px solid var(--accent);
            border-radius: 4px;
            font-size: 0.825rem;
        }

        .citations-card h4 {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .conflicts-card {
            margin-top: 0.75rem;
            padding: 0.75rem 1rem;
            background: rgba(245, 158, 11, 0.1);
            border-left: 3px solid var(--warning);
            border-radius: 4px;
            font-size: 0.825rem;
            color: #fde68a;
        }

        .derived-card {
            margin-top: 0.75rem;
            padding: 0.75rem 1rem;
            background: rgba(59, 130, 246, 0.1);
            border-left: 3px solid var(--accent);
            border-radius: 4px;
            font-size: 0.825rem;
            color: #bfdbfe;
        }

        /* Thumbs Feedback */
        .feedback-actions {
            margin-top: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .feedback-btn {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
            border-radius: 4px;
            padding: 0.25rem 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .feedback-btn:hover {
            color: var(--text-main);
            border-color: rgba(255,255,255,0.25);
        }

        /* Input Bar */
        .input-bar-container {
            margin-top: 1rem;
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.6rem 0.8rem;
            display: flex;
            gap: 0.75rem;
            align-items: center;
            backdrop-filter: blur(12px);
        }

        .input-bar-container textarea {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 0.95rem;
            resize: none;
            max-height: 120px;
            height: 38px;
            line-height: 1.4;
            padding: 0.4rem 0.5rem;
        }

        .send-btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.6rem 1.25rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: background 0.2s;
        }

        .send-btn:hover {
            background: #1d4ed8;
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <span class="brand-badge">ATLAS</span>
            <h1>Cognitive Market Research & Consulting — Report Copilot</h1>
        </div>
        <div class="client-selector-wrap">
            <label for="clientSelect">Active Entitlement:</label>
            <select id="clientSelect">
                <?php foreach ($clients as $cid => $cname): ?>
                    <option value="<?php echo html_escape($cid); ?>"><?php echo html_escape("[$cid] $cname"); ?></option>
                <?php endforeach; ?>
            </select>
        </div>
    </header>

    <main>
        <div class="chat-stream" id="chatStream">
            <div class="chat-bubble assistant-bubble">
                <div class="badge-bar">
                    <span class="meta-badge badge-confidence">SYSTEM ONLINE</span>
                </div>
                Welcome to the Cognitive Market Research <strong>Report Copilot</strong>. Select your company client entitlement above, then ask any market research or projection query (e.g. <em>"What will the smart water meter market be worth in 2030 in R-101?"</em> or <em>"Why do R-101 and R-102 disagree on 2024?"</em>).
            </div>
        </div>

        <div class="input-bar-container">
            <textarea id="chatInput" placeholder="Ask a question about your purchased reports..." rows="1"></textarea>
            <button class="send-btn" id="sendBtn">Send</button>
        </div>
    </main>

    <script>
        const chatStream = document.getElementById('chatStream');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const clientSelect = document.getElementById('clientSelect');

        function appendUserMessage(text) {
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble user-bubble';
            bubble.textContent = text;
            chatStream.appendChild(bubble);
            chatStream.scrollTop = chatStream.scrollHeight;
        }

        function appendAssistantResponse(data) {
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble assistant-bubble';

            let html = '<div class="badge-bar">';
            if (data.confidence !== undefined) {
                const confPercent = Math.round(data.confidence * 100);
                html += `<span class="meta-badge badge-confidence">Confidence: ${confPercent}%</span>`;
            }
            if (data.escalated) {
                html += `<span class="meta-badge badge-guardrail">Escalated to Human Analyst</span>`;
            }
            html += '</div>';

            html += `<div class="answer-text">${data.answer || data.message || 'No answer generated.'}</div>`;

            // Derived values / formulas
            if (data.derived_values && data.derived_values.length > 0) {
                html += '<div class="derived-card"><strong>Derived Projection:</strong><br>';
                data.derived_values.forEach(d => {
                    html += `• <strong>${d.metric}:</strong> ${d.value} (Formula: <code>${d.formula}</code>, Assumptions: ${d.assumptions})<br>`;
                });
                html += '</div>';
            }

            // Conflicts
            if (data.conflicts && data.conflicts.length > 0) {
                html += '<div class="conflicts-card"><strong>⚠️ Methodological Conflict Detected:</strong><br>';
                data.conflicts.forEach(c => {
                    html += `• ${c.topic}: ${c.description} (Resolution: ${c.resolution})<br>`;
                });
                html += '</div>';
            }

            // Citations
            if (data.citations && data.citations.length > 0) {
                html += '<div class="citations-card"><h4>Verified Citations</h4>';
                data.citations.forEach(cit => {
                    html += `<div>• <strong>${cit.report_id}</strong> (p. ${cit.page}): <em>"${cit.quote || cit.text || ''}"</em></div>`;
                });
                html += '</div>';
            }

            // Feedback buttons
            html += `
                <div class="feedback-actions">
                    <span>Was this answer helpful?</span>
                    <button class="feedback-btn" onclick="submitFeedback(1, this)">👍 Yes</button>
                    <button class="feedback-btn" onclick="submitFeedback(0, this)">👎 No</button>
                </div>
            `;

            bubble.innerHTML = html;
            chatStream.appendChild(bubble);
            chatStream.scrollTop = chatStream.scrollHeight;
        }

        async function sendMessage() {
            const query = chatInput.value.trim();
            if (!query) return;

            appendUserMessage(query);
            chatInput.value = '';
            sendBtn.disabled = true;

            const clientId = clientSelect.value;

            try {
                const res = await fetch('<?php echo site_url("chat/send"); ?>', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ client_id: clientId, query: query })
                });

                const json = await res.json();
                if (json.status === 'success' && json.data) {
                    appendAssistantResponse(json.data);
                } else {
                    appendAssistantResponse({
                        answer: json.message || 'An error occurred connecting to Report Copilot.',
                        confidence: 0.0,
                        escalated: true
                    });
                }
            } catch (err) {
                appendAssistantResponse({
                    answer: 'Connection error communicating with the legacy backend portal.',
                    confidence: 0.0,
                    escalated: true
                });
            } finally {
                sendBtn.disabled = false;
            }
        }

        async function submitFeedback(rating, btn) {
            const container = btn.parentElement;
            container.innerHTML = '<span style="color: #34d399;">✓ Feedback recorded! Thank you.</span>';
            try {
                await fetch('<?php echo site_url("chat/feedback"); ?>', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        client_id: clientSelect.value,
                        rating: rating
                    })
                });
            } catch (e) {}
        }

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
