// ============================================================
// landing.js — All landing page JavaScript
// Extracted from inline <script> blocks in landing.html
// ============================================================

// Tab switching router
function navigateToTab(tabId) {
    // Read Jinja-injected config from the HTML page
    const isLoggedIn = window.__APP_CONFIG && window.__APP_CONFIG.loggedIn;
    const loginUrl = (window.__APP_CONFIG && window.__APP_CONFIG.loginUrl) || '/login';

    // Check if logged in for Analyzer
    if (tabId === 'dashboard') {
        if (!isLoggedIn) {
            window.location.href = loginUrl;
            return;
        }
    }

    const activeTab = document.querySelector('.nav-link.active');
    const targetTab = document.getElementById('nav-link-' + tabId);
    const activeView = document.querySelector('.page-view.active');
    const targetView = document.getElementById('view-' + tabId);

    if (!targetView || activeView === targetView) return;

    // Toggle background theme depending on target section
    if (tabId === 'home') {
        document.body.classList.remove('non-home-active');
    } else {
        document.body.classList.add('non-home-active');
    }

    // Update Navbar Active Link State
    if (activeTab) activeTab.classList.remove('active');
    if (targetTab) targetTab.classList.add('active');

    // Hide mobile menu if open
    const navbar = document.getElementById('app-navbar');
    if (navbar) navbar.classList.remove('mobile-menu-active');

    // Smooth Fade Out / Fade In Transition
    if (activeView) {
        activeView.style.opacity = '0';
        activeView.style.transform = 'translateY(15px)';

        setTimeout(() => {
            activeView.classList.remove('active');

            targetView.classList.add('active');
            // Force reflow
            targetView.offsetHeight;
            targetView.style.opacity = '1';
            targetView.style.transform = 'translateY(0)';

            // Reset scroll position
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }, 300);
    } else {
        targetView.classList.add('active');
        targetView.style.opacity = '1';
        targetView.style.transform = 'translateY(0)';
    }

    // Update URL hash state without reloading the page
    history.pushState(null, '', '#' + tabId);
}

document.addEventListener('DOMContentLoaded', () => {
    // ── Splash Screen ──────────────────────────────────────────
    const splash = document.getElementById('splash-screen');

    // Hide splash screen after 2.4 seconds
    setTimeout(() => {
        if (splash) {
            splash.classList.add('splash-fade-out');
        }

        // Initialize scroll reveal animations for features after splash hides
        const observerOptions = {
            threshold: 0.15,
            rootMargin: "0px 0px -50px 0px"
        };

        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('reveal-active');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        document.querySelectorAll('.reveal-on-scroll').forEach(el => {
            revealObserver.observe(el);
        });
    }, 2400);

    // ── Initialize from URL parameter or hash on load ──────────
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    const hashParam = window.location.hash.substring(1);
    const initialTab = tabParam || hashParam || 'home';

    // Switch to the correct tab on startup (no delay since splash is running)
    if (initialTab !== 'home') {
        document.body.classList.add('non-home-active');
    } else {
        document.body.classList.remove('non-home-active');
    }
    const targetTab = document.getElementById('nav-link-' + initialTab);
    const targetView = document.getElementById('view-' + initialTab);
    if (targetTab && targetView) {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelectorAll('.page-view').forEach(v => v.classList.remove('active'));
        targetTab.classList.add('active');
        targetView.classList.add('active');
        targetView.style.opacity = '1';
        targetView.style.transform = 'translateY(0)';
    }

    // ── Mobile menu toggling ───────────────────────────────────
    const hamburgerBtn = document.getElementById('nav-hamburger-btn');
    const navbar = document.getElementById('app-navbar');
    if (hamburgerBtn && navbar) {
        hamburgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            navbar.classList.toggle('mobile-menu-active');
        });
        document.addEventListener('click', () => {
            navbar.classList.remove('mobile-menu-active');
        });
    }

    // ── Background Dimming on Scroll ───────────────────────────
    const dimOverlay = document.getElementById('bg-dim-overlay');
    window.addEventListener('scroll', () => {
        const scrollTop = window.scrollY;
        const maxScroll = 500;
        const opacity = Math.min(scrollTop / maxScroll, 0.85);
        if (dimOverlay) {
            dimOverlay.style.opacity = opacity;
        }
    });

    // ── Button Click Shockwave Border Effect ───────────────────
    const clickableButtons = document.querySelectorAll('.submit-button, .cta-btn, .navbar-login-btn, .home-btn-link, .logout-btn-link, .nav-link');
    clickableButtons.forEach(button => {
        button.addEventListener('click', function () {
            this.classList.add('btn-click-pulse');
            setTimeout(() => {
                this.classList.remove('btn-click-pulse');
            }, 500);
        });
    });

    // ── Profile Dropdown Toggle ────────────────────────────────
    const profileDropdownBtn = document.getElementById('profile-dropdown-btn');
    const profileDropdownMenu = document.getElementById('profile-dropdown-menu');
    if (profileDropdownBtn && profileDropdownMenu) {
        profileDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            profileDropdownMenu.classList.toggle('show');
        });
        document.addEventListener('click', (e) => {
            if (!profileDropdownMenu.contains(e.target) && !profileDropdownBtn.contains(e.target)) {
                profileDropdownMenu.classList.remove('show');
            }
        });
    }

    // ── Dashboard Upload Functionality ─────────────────────────
    const dropzone = document.getElementById('dashboard-dropzone');
    const fileInput = document.getElementById('dashboard-file-input');
    const fileDisplay = document.getElementById('dashboard-file-display');
    const fileName = document.getElementById('dashboard-file-name');
    const fileSize = document.getElementById('dashboard-file-size');
    const removeBtn = document.getElementById('dashboard-remove-file');
    const uploadBtn = document.getElementById('dashboard-upload-btn');
    const uploadForm = document.getElementById('dashboard-upload-form');
    const errorMsg = document.getElementById('dashboard-error-msg');
    const successMsg = document.getElementById('dashboard-success-msg');

    if (dropzone && fileInput) {
        let selectedFile = null;

        dropzone.addEventListener('click', (e) => {
            if (e.target !== fileInput) fileInput.click();
        });

        ['dragenter', 'dragover'].forEach(ev => {
            dropzone.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); dropzone.classList.add('dragover'); }, false);
        });
        ['dragleave', 'drop'].forEach(ev => {
            dropzone.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); dropzone.classList.remove('dragover'); }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) pickFile(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) pickFile(e.target.files[0]);
        });

        function pickFile(file) {
            errorMsg.style.display = 'none';
            successMsg.style.display = 'none';
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                errorMsg.textContent = 'Only PDF files are allowed.';
                errorMsg.style.display = 'block';
                return;
            }
            selectedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
            fileDisplay.style.display = 'flex';
            uploadBtn.disabled = false;
        }

        removeBtn.addEventListener('click', () => {
            selectedFile = null;
            fileInput.value = '';
            fileDisplay.style.display = 'none';
            uploadBtn.disabled = true;
        });

        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            errorMsg.style.display = 'none';
            successMsg.style.display = 'none';

            if (!selectedFile) {
                errorMsg.textContent = 'Please select a PDF file first.';
                errorMsg.style.display = 'block';
                return;
            }

            uploadBtn.disabled = true;
            uploadBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';

            const formData = new FormData();
            formData.append('resume', selectedFile);

            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
                .then(resp => {
                    if (resp.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    return resp.json();
                })
                .then(data => {
                    if (!data) return;
                    if (data.success) {
                        successMsg.querySelector('span').textContent = data.message || 'Resume uploaded successfully!';
                        successMsg.style.display = 'block';
                        window.__LAST_UPLOADED_FILENAME = data.filename;
                        
                        // Enable Run Analysis button if JD has text
                        const runBtn = document.getElementById('run-analysis-btn');
                        if (runBtn) {
                            runBtn.disabled = false;
                        }
                    } else {
                        errorMsg.textContent = data.error || 'Upload failed.';
                        errorMsg.style.display = 'block';
                    }
                })
                .catch(err => {
                    errorMsg.textContent = 'Upload failed. Please try again.';
                    errorMsg.style.display = 'block';
                })
                .finally(() => {
                    uploadBtn.disabled = false;
                    uploadBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-arrow-up-from-bracket"></i> Upload Resume';
                });
        });
    }

    // ── Job Description Presets & AI Match Analysis ────────────
    const jdInput = document.getElementById('jd-input-text');
    const jobTitleInput = document.getElementById('job-title-input');
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    const presetBtns = document.querySelectorAll('.jd-preset-btn');
    const analysisErrorMsg = document.getElementById('analysis-error-msg');
    const resultsSection = document.getElementById('analysis-results-section');

    const PRESETS = {
        swe: {
            title: "Senior Software Engineer",
            text: "We are seeking a Senior Software Engineer proficient in Python, Flask, SQL databases, REST API design, Git, and Microservices architecture. Experience with Docker, Linux, and Cloud (AWS) is highly desired."
        },
        fullstack: {
            title: "Full Stack Developer",
            text: "Looking for a Full Stack Developer skilled in React, TypeScript, Node.js, HTML/CSS, PostgreSQL, MongoDB, System Design, and CI/CD pipelines. Experience in Agile team environments preferred."
        },
        ds: {
            title: "Data Scientist",
            text: "Hiring a Data Scientist with strong technical expertise in Python, Machine Learning, Deep Learning, Pandas, NumPy, Scikit-Learn, SQL, Data Analysis, TensorFlow, PyTorch, and NLP."
        },
        devops: {
            title: "DevOps Engineer",
            text: "Seeking a DevOps Engineer experienced in Linux, AWS, GCP, Docker, Kubernetes, Terraform, Ansible, Jenkins, CI/CD automation, and Shell scripting."
        }
    };

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-preset');
            if (PRESETS[key]) {
                if (jdInput) jdInput.value = PRESETS[key].text;
                if (jobTitleInput) jobTitleInput.value = PRESETS[key].title;
                checkEnableAnalysis();
            }
        });
    });

    if (jdInput) {
        jdInput.addEventListener('input', checkEnableAnalysis);
    }

    function checkEnableAnalysis() {
        if (runAnalysisBtn) {
            const hasJD = jdInput && jdInput.value.trim().length > 10;
            const hasFile = !!window.__LAST_UPLOADED_FILENAME;
            runAnalysisBtn.disabled = !(hasJD && hasFile);
        }
    }

    let lastAnalysisData = null;

    if (runAnalysisBtn) {
        runAnalysisBtn.addEventListener('click', () => {
            if (!window.__LAST_UPLOADED_FILENAME) {
                analysisErrorMsg.textContent = "Please upload a candidate PDF resume first.";
                analysisErrorMsg.style.display = "block";
                return;
            }

            const jdText = jdInput ? jdInput.value.trim() : "";
            if (!jdText) {
                analysisErrorMsg.textContent = "Please enter or select a Job Description first.";
                analysisErrorMsg.style.display = "block";
                return;
            }

            const jobTitle = jobTitleInput ? jobTitleInput.value.trim() : "General Match";

            analysisErrorMsg.style.display = "none";
            runAnalysisBtn.disabled = true;
            runAnalysisBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing NLP & TF-IDF Match...';

            fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: window.__LAST_UPLOADED_FILENAME,
                    job_title: jobTitle,
                    job_description: jdText
                })
            })
            .then(resp => {
                if (resp.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                return resp.json();
            })
            .then(data => {
                if (!data) return;
                if (data.success) {
                    lastAnalysisData = data;
                    renderAnalysisReport(data);
                    loadHistory();
                } else {
                    analysisErrorMsg.textContent = data.error || "Analysis failed.";
                    analysisErrorMsg.style.display = "block";
                }
            })
            .catch(err => {
                analysisErrorMsg.textContent = "An error occurred during analysis. Please try again.";
                analysisErrorMsg.style.display = "block";
            })
            .finally(() => {
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Run AI Match Analysis';
            });
        });
    }

    function animateCounter(el, start, end, duration, suffix = '') {
        const startTime = performance.now();
        function step(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const currentVal = (start + (end - start) * progress).toFixed(1);
            el.textContent = `${currentVal}${suffix}`;
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }
        requestAnimationFrame(step);
    }

    function renderAnalysisReport(data) {
        if (!resultsSection) return;

        // Set text details
        document.getElementById('res-filename-display').textContent = `Target Document: ${data.filename} (${data.job_title || 'General Match'})`;
        
        // Animate SVG radial progress ring and score number
        const ringPath = document.getElementById('score-ring-path');
        const percentText = document.getElementById('res-match-percentage');
        const targetPct = data.match_percentage || 0;
        const circumference = 264;
        const offset = circumference - (circumference * Math.min(targetPct, 100) / 100);

        if (ringPath) {
            ringPath.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.1, 0.8, 0.3, 1)';
            ringPath.style.strokeDashoffset = offset;
        }

        if (percentText) {
            animateCounter(percentText, 0, targetPct, 1000, '%');
        }

        const gradeEl = document.getElementById('res-match-grade');
        gradeEl.textContent = data.grade;
        gradeEl.className = 'grade-pill ';
        if (data.match_percentage >= 75) gradeEl.classList.add('grade-strong');
        else if (data.match_percentage >= 50) gradeEl.classList.add('grade-moderate');
        else if (data.match_percentage >= 25) gradeEl.classList.add('grade-low');
        else gradeEl.classList.add('grade-weak');

        document.getElementById('res-recommendation').textContent = data.recommendation;
        document.getElementById('res-resume-words').textContent = data.resume_word_count || 0;
        document.getElementById('res-jd-words').textContent = data.jd_word_count || 0;

        // Render Matched Skills
        const matchedContainer = document.getElementById('res-matched-skills-container');
        if (matchedContainer) {
            if (data.matched_skills && data.matched_skills.length > 0) {
                matchedContainer.innerHTML = data.matched_skills.map(s => 
                    `<span class="skill-pill matched-pill"><i class="fa-solid fa-circle-check"></i> ${s}</span>`
                ).join('');
            } else {
                matchedContainer.innerHTML = `<span style="font-size: 0.85rem; color: var(--text-secondary);">No exact skill overlap detected.</span>`;
            }
        }

        // Render Missing Skills
        const missingContainer = document.getElementById('res-missing-skills-container');
        if (missingContainer) {
            if (data.missing_skills && data.missing_skills.length > 0) {
                missingContainer.innerHTML = data.missing_skills.map(s => 
                    `<span class="skill-pill missing-pill"><i class="fa-solid fa-triangle-exclamation"></i> ${s}</span>`
                ).join('');
            } else {
                missingContainer.innerHTML = `<span style="font-size: 0.85rem; color: #10b981;">No missing target skills! All required skills matched.</span>`;
            }
        }

        // Render ATS Readiness Analysis
        if (data.ats_analysis) {
            const atsScoreEl = document.getElementById('res-ats-score-badge');
            if (atsScoreEl) {
                atsScoreEl.textContent = `${data.ats_analysis.ats_score} / 100`;
            }

            const checksGrid = document.getElementById('res-ats-checks-grid');
            if (checksGrid && data.ats_analysis.checks) {
                checksGrid.innerHTML = data.ats_analysis.checks.map(c => `
                    <div style="background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 0.7rem 1rem; border: 1px solid ${c.passed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; display: flex; align-items: center; gap: 0.6rem;">
                        <i class="fa-solid ${c.passed ? 'fa-circle-check' : 'fa-circle-xmark'}" style="color: ${c.passed ? '#10b981' : '#ef4444'}; font-size: 1.1rem;"></i>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-size: 0.85rem; font-weight: 600; color: #ffffff;">${c.name}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">${c.details}</div>
                        </div>
                    </div>
                `).join('');
            }

            const tipsList = document.getElementById('res-ats-tips-list');
            if (tipsList && data.ats_analysis.recommendations) {
                tipsList.innerHTML = data.ats_analysis.recommendations.map(r => `
                    <li>${r}</li>
                `).join('');
            }
        }

        // Render Keyword Frequency & TF-IDF Weights
        const kwContainer = document.getElementById('res-keywords-container');
        if (kwContainer) {
            if (data.top_keywords && data.top_keywords.length > 0) {
                const maxScore = Math.max(...data.top_keywords.map(k => k.score)) || 1;
                kwContainer.innerHTML = data.top_keywords.map(k => {
                    const widthPct = Math.min(Math.round((k.score / maxScore) * 100), 100);
                    const statusClass = k.in_resume ? 'kw-found' : 'kw-missing';
                    const statusText = k.in_resume ? '<i class="fa-solid fa-check"></i> Found' : '<i class="fa-solid fa-xmark"></i> Missing';
                    return `
                        <div class="kw-row">
                            <span class="kw-label">${k.word}</span>
                            <div class="kw-bar-bg">
                                <div class="kw-bar-fill" style="width: ${widthPct}%;"></div>
                            </div>
                            <span class="kw-status ${statusClass}">${statusText}</span>
                        </div>
                    `;
                }).join('');
            } else {
                kwContainer.innerHTML = `<span style="font-size: 0.85rem; color: var(--text-secondary);">No TF-IDF terms extracted.</span>`;
            }
        }

        // Display results section with smooth scroll
        resultsSection.style.display = 'flex';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ── Export Toolbar Handlers ────────────────────────────────
    const btnPrint = document.getElementById('btn-print-report');
    const btnExportJson = document.getElementById('btn-export-json');
    const btnCopySummary = document.getElementById('btn-copy-summary');

    if (btnCopySummary) {
        btnCopySummary.addEventListener('click', () => {
            if (!lastAnalysisData) return;
            const summaryText = `Hire𝒽ive Candidate Screening Report\nDocument: ${lastAnalysisData.filename}\nRole: ${lastAnalysisData.job_title || 'General Match'}\nMatch Score: ${lastAnalysisData.match_percentage}% (${lastAnalysisData.grade})\nATS Score: ${lastAnalysisData.ats_score || 0}/100\nMatched Skills: ${lastAnalysisData.matched_skills ? lastAnalysisData.matched_skills.join(', ') : 'None'}\nMissing Skills: ${lastAnalysisData.missing_skills ? lastAnalysisData.missing_skills.join(', ') : 'None'}`;
            navigator.clipboard.writeText(summaryText).then(() => {
                const origHTML = btnCopySummary.innerHTML;
                btnCopySummary.innerHTML = '<i class="fa-solid fa-check" style="color: #10b981;"></i> Copied!';
                setTimeout(() => { btnCopySummary.innerHTML = origHTML; }, 2000);
            });
        });
    }

    if (btnPrint) {
        btnPrint.addEventListener('click', () => {
            window.print();
        });
    }

    if (btnExportJson) {
        btnExportJson.addEventListener('click', () => {
            if (!lastAnalysisData) return;
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(lastAnalysisData, null, 2));
            const downloadAnchor = document.createElement('a');
            downloadAnchor.setAttribute("href", dataStr);
            downloadAnchor.setAttribute("download", `hirehive_${lastAnalysisData.filename || 'analysis'}_report.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();
        });
    }

    // ── Candidate Inspection Modal Logic ──────────────────────
    const modal = document.getElementById('inspection-modal');
    const modalBody = document.getElementById('modal-body-content');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalCloseFooterBtn = document.getElementById('modal-close-footer-btn');

    function openModal(item) {
        if (!modal || !modalBody) return;
        const matched = item.matched_skills && item.matched_skills.length > 0 
            ? item.matched_skills.map(s => `<span class="skill-pill matched-pill"><i class="fa-solid fa-circle-check"></i> ${s}</span>`).join('') 
            : '<span style="color: var(--text-secondary); font-size: 0.85rem;">No skills overlap</span>';
        
        const missing = item.missing_skills && item.missing_skills.length > 0 
            ? item.missing_skills.map(s => `<span class="skill-pill missing-pill"><i class="fa-solid fa-triangle-exclamation"></i> ${s}</span>`).join('') 
            : '<span style="color: #10b981; font-size: 0.85rem;">All target skills matched!</span>';

        modalBody.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.03); padding: 1.2rem; border-radius: 12px; border: 1px solid var(--border-color);">
                <div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">Candidate Document</div>
                    <div style="font-weight: 700; color: #ffffff; font-size: 1.1rem;"><i class="fa-solid fa-file-pdf" style="color: #ef4444; margin-right: 0.4rem;"></i> ${item.filename}</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.3rem;">Target Role: <strong style="color: #fff;">${item.job_title}</strong></div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.8rem; font-weight: 800; color: #FFD000;">${item.match_score}%</div>
                    <div class="grade-pill grade-strong" style="font-size: 0.8rem; margin-top: 0.3rem;">${item.grade}</div>
                </div>
            </div>

            <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 10px; padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.9rem; color: #ffffff; font-weight: 600;"><i class="fa-solid fa-file-shield" style="color: #6366f1;"></i> ATS Readiness Score</span>
                <span style="font-size: 1.1rem; font-weight: 800; color: #6366f1;">${item.ats_score} / 100</span>
            </div>

            <div>
                <h5 style="color: #10b981; font-size: 0.92rem; font-weight: 700; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;"><i class="fa-solid fa-circle-check"></i> Matched Technical Skills</h5>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">${matched}</div>
            </div>

            <div>
                <h5 style="color: #f59e0b; font-size: 0.92rem; font-weight: 700; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;"><i class="fa-solid fa-triangle-exclamation"></i> Missing Required Keywords</h5>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">${missing}</div>
            </div>
        `;
        modal.style.display = 'flex';
    }

    function closeModal() {
        if (modal) modal.style.display = 'none';
    }

    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
    if (modalCloseFooterBtn) modalCloseFooterBtn.addEventListener('click', closeModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    // ── Candidate History Management ───────────────────────────
    const historyTableBody = document.getElementById('history-table-body');
    const historyEmptyState = document.getElementById('history-empty-state');
    const historySearchInput = document.getElementById('history-search-input');
    const btnRefreshHistory = document.getElementById('btn-refresh-history');
    const btnClearHistory = document.getElementById('btn-clear-history');

    let allHistory = [];

    function loadHistory() {
        if (!historyTableBody) return;
        const isLoggedIn = window.__APP_CONFIG && window.__APP_CONFIG.loggedIn;
        if (!isLoggedIn) return;

        fetch('/api/history')
            .then(resp => resp.json())
            .then(data => {
                if (data.success) {
                    allHistory = data.history || [];
                    renderHistoryTable(allHistory);
                }
            })
            .catch(err => console.error("Error loading history:", err));
    }

    function renderHistoryTable(items) {
        if (!historyTableBody || !historyEmptyState) return;

        const searchTerm = historySearchInput ? historySearchInput.value.toLowerCase().trim() : '';
        const filtered = items.filter(item => {
            if (!searchTerm) return true;
            return (
                (item.filename && item.filename.toLowerCase().includes(searchTerm)) ||
                (item.job_title && item.job_title.toLowerCase().includes(searchTerm))
            );
        });

        if (filtered.length === 0) {
            historyTableBody.innerHTML = '';
            historyEmptyState.style.display = 'block';
            return;
        }

        historyEmptyState.style.display = 'none';
        historyTableBody.innerHTML = filtered.map((item, idx) => {
            let scoreClass = 'grade-strong';
            if (item.match_score < 25) scoreClass = 'grade-weak';
            else if (item.match_score < 50) scoreClass = 'grade-low';
            else if (item.match_score < 75) scoreClass = 'grade-moderate';

            const dateStr = item.created_at ? item.created_at.split('.')[0] : 'Just now';

            return `
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); transition: background 0.2s;">
                    <td style="padding: 0.9rem 1rem; color: var(--text-secondary); font-size: 0.85rem;">${dateStr}</td>
                    <td style="padding: 0.9rem 1rem; color: #ffffff; font-weight: 600;">
                        <i class="fa-solid fa-file-pdf" style="color: #ef4444; margin-right: 0.4rem;"></i> ${item.filename}
                    </td>
                    <td style="padding: 0.9rem 1rem; color: var(--text-secondary);">${item.job_title}</td>
                    <td style="padding: 0.9rem 1rem;">
                        <span class="grade-pill ${scoreClass}" style="font-size: 0.8rem; padding: 0.2rem 0.6rem;">${item.match_score}% (${item.grade})</span>
                    </td>
                    <td style="padding: 0.9rem 1rem; font-weight: 700; color: #6366f1;">
                        ${item.ats_score} / 100
                    </td>
                    <td style="padding: 0.9rem 1rem; text-align: right; white-space: nowrap;">
                        <button type="button" class="view-history-btn action-btn" data-index="${idx}" style="background: rgba(255, 208, 0, 0.1); border: 1px solid rgba(255, 208, 0, 0.3); color: #FFD000; padding: 0.3rem 0.7rem; border-radius: 6px; font-size: 0.8rem; cursor: pointer; margin-right: 0.4rem;" title="View Full Inspection">
                            <i class="fa-solid fa-eye"></i> View
                        </button>
                        <button type="button" class="delete-history-btn" data-id="${item.id}" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 0.9rem; padding: 0.3rem 0.6rem; border-radius: 6px;" title="Delete Record">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Attach event listeners for view inspection and deletion
        document.querySelectorAll('.view-history-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.getAttribute('data-index'), 10);
                if (filtered[idx]) openModal(filtered[idx]);
            });
        });

        document.querySelectorAll('.delete-history-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                deleteHistoryItem(id);
            });
        });
    }

    function deleteHistoryItem(id) {
        if (!confirm("Are you sure you want to delete this candidate screening record?")) return;
        fetch(`/api/history/${id}`, { method: 'DELETE' })
            .then(resp => resp.json())
            .then(data => {
                if (data.success) {
                    loadHistory();
                }
            })
            .catch(err => console.error("Failed to delete history item:", err));
    }

    if (btnRefreshHistory) {
        btnRefreshHistory.addEventListener('click', loadHistory);
    }

    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', () => {
            if (!confirm("Are you sure you want to clear ALL screening history records?")) return;
            fetch('/api/history/clear', { method: 'POST' })
                .then(resp => resp.json())
                .then(data => {
                    if (data.success) {
                        loadHistory();
                    }
                })
                .catch(err => console.error("Failed to clear history:", err));
        });
    }

    if (historySearchInput) {
        historySearchInput.addEventListener('input', () => {
            renderHistoryTable(allHistory);
        });
    }

    // Initial history fetch if user is on Dashboard
    loadHistory();

});



