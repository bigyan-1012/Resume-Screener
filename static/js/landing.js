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
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    if (activeView) {
        activeView.style.opacity = '0';
        activeView.style.transform = 'translateY(15px)';

        setTimeout(() => {
            document.querySelectorAll('.page-view').forEach(v => {
                if (v !== targetView) {
                    v.classList.remove('active');
                    v.style.opacity = '0';
                    v.style.transform = '';
                    v.style.display = 'none';
                }
            });

            targetView.classList.add('active');
            targetView.style.display = 'block';
            // Force reflow
            targetView.offsetHeight;
            targetView.style.opacity = '1';
            targetView.style.transform = 'translateY(0)';

            // Reset scroll position immediately
            window.scrollTo(0, 0);
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
        }, 150);
    } else {
        document.querySelectorAll('.page-view').forEach(v => {
            if (v !== targetView) {
                v.classList.remove('active');
                v.style.opacity = '0';
                v.style.transform = '';
                v.style.display = 'none';
            }
        });
        targetView.classList.add('active');
        targetView.style.display = 'block';
        targetView.style.opacity = '1';
        targetView.style.transform = 'translateY(0)';
        window.scrollTo(0, 0);
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

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelectorAll('.page-view').forEach(v => {
        v.classList.remove('active');
        v.style.opacity = '0';
        v.style.transform = '';
        v.style.display = 'none';
    });

    if (targetTab) targetTab.classList.add('active');
    if (targetView) {
        targetView.classList.add('active');
        targetView.style.display = 'block';
        targetView.style.opacity = '1';
        targetView.style.transform = 'translateY(0)';
    } else {
        const homeTab = document.getElementById('nav-link-home');
        const homeView = document.getElementById('view-home');
        if (homeTab) homeTab.classList.add('active');
        if (homeView) {
            homeView.classList.add('active');
            homeView.style.display = 'block';
            homeView.style.opacity = '1';
            homeView.style.transform = 'translateY(0)';
        }
    }
    const resetPageScroll = () => {
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
    };
    resetPageScroll();
    requestAnimationFrame(resetPageScroll);
    setTimeout(resetPageScroll, 50);
    setTimeout(resetPageScroll, 150);

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
    function updateBgDim() {
        if (!dimOverlay) return;
        const scrollTop = window.scrollY;
        const maxScroll = 500;
        const initialDim = 0.45;
        const maxDim = 0.88;
        const opacity = initialDim + (Math.min(scrollTop / maxScroll, 1) * (maxDim - initialDim));
        dimOverlay.style.opacity = opacity;
    }
    window.addEventListener('scroll', updateBgDim);
    updateBgDim();

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

    // ── Analyser Mode Management (Candidate Mode vs HR Mode) ─────
    window.currentAnalyserMode = 'candidate'; // default 'candidate' or 'hr'
    let selectedFilesList = []; // Array of File objects

    window.setAnalyserMode = function(mode) {
        window.currentAnalyserMode = mode;
        const btnCandidate = document.getElementById('btn-mode-candidate');
        const btnHr = document.getElementById('btn-mode-hr');
        const step3Item = document.getElementById('stepper-step-3');
        const step3Line = document.getElementById('stepper-line-3');
        const wizardTitle = document.getElementById('wizard-title-heading');
        const wizardSubtitle = document.getElementById('wizard-subtitle-text');
        const uploadCardTitle = document.getElementById('upload-card-title');
        const dropzoneTitle = document.getElementById('dropzone-title');
        const dropzoneSubtitle = document.getElementById('dropzone-subtitle');
        const fileInput = document.getElementById('dashboard-file-input');
        const uploadBtn = document.getElementById('dashboard-upload-btn');
        const runAnalysisBtn = document.getElementById('run-analysis-btn');

        const ctaCard = document.getElementById('cta-resume-builder-card');
        if (mode === 'hr') {
            if (btnCandidate) btnCandidate.classList.remove('active');
            if (btnHr) btnHr.classList.add('active');
            if (step3Item) step3Item.style.display = 'none';
            if (step3Line) step3Line.style.display = 'none';
            if (ctaCard) ctaCard.style.display = 'none';

            if (wizardTitle) wizardTitle.innerHTML = 'HR <span class="text-glow-gold">Recruiter Portal</span>';
            if (wizardSubtitle) wizardSubtitle.textContent = 'Upload up to 10 candidate resumes for batch AI screening & ATS ranking.';
            if (uploadCardTitle) uploadCardTitle.innerHTML = '<i class="fa-solid fa-cloud-arrow-up" style="color: #FFD000;"></i> 1. Upload Candidate PDF Resumes (Up to 10)';
            if (dropzoneTitle) dropzoneTitle.textContent = 'Drop candidate resumes here (Up to 10 PDFs)';
            if (dropzoneSubtitle) dropzoneSubtitle.innerHTML = 'or <span class="browse-link">browse files</span> — Batch PDF Upload Supported';
            if (fileInput) fileInput.setAttribute('multiple', 'multiple');
            if (uploadBtn) uploadBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-arrow-up-from-bracket"></i> Upload Resumes';
            if (runAnalysisBtn) runAnalysisBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-trophy"></i> Screen & Rank Candidates';
        } else {
            if (btnCandidate) btnCandidate.classList.add('active');
            if (btnHr) btnHr.classList.remove('active');
            if (step3Item) step3Item.style.display = 'flex';
            if (step3Line) step3Line.style.display = 'flex';
            if (ctaCard) ctaCard.style.display = 'flex';

            if (wizardTitle) wizardTitle.innerHTML = 'Your <span class="text-glow-gold">Dashboard</span>';
            if (wizardSubtitle) wizardSubtitle.textContent = 'Upload your resume to get started with AI-powered screening and analysis.';
            if (uploadCardTitle) uploadCardTitle.innerHTML = '<i class="fa-solid fa-cloud-arrow-up" style="color: #FFD000;"></i> 1. Upload Candidate PDF Resume';
            if (dropzoneTitle) dropzoneTitle.textContent = 'Drop your resume here';
            if (dropzoneSubtitle) dropzoneSubtitle.innerHTML = 'or <span class="browse-link">browse files</span> — PDF only';
            if (fileInput) fileInput.removeAttribute('multiple');
            if (uploadBtn) uploadBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-arrow-up-from-bracket"></i> Upload Resume';
            if (runAnalysisBtn) runAnalysisBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Start Analyzing Process';
        }

        resetFileSelections();
    };

    function resetFileSelections() {
        selectedFilesList = [];
        window.__LAST_UPLOADED_FILENAMES = null;
        window.__LAST_UPLOADED_FILENAME = null;

        const fileInput = document.getElementById('dashboard-file-input');
        const fileDisplay = document.getElementById('dashboard-file-display');
        const filesList = document.getElementById('dashboard-files-list');
        const uploadBtn = document.getElementById('dashboard-upload-btn');
        const errorMsg = document.getElementById('dashboard-error-msg');
        const successMsg = document.getElementById('dashboard-success-msg');
        const runBtn = document.getElementById('run-analysis-btn');

        if (fileInput) fileInput.value = '';
        if (fileDisplay) fileDisplay.style.display = 'none';
        if (filesList) { filesList.style.display = 'none'; filesList.innerHTML = ''; }
        if (uploadBtn) uploadBtn.disabled = true;
        if (errorMsg) errorMsg.style.display = 'none';
        if (successMsg) successMsg.style.display = 'none';
        if (runBtn) runBtn.disabled = true;
    }

    // ── Dashboard Upload Functionality ─────────────────────────
    const dropzone = document.getElementById('dashboard-dropzone');
    const fileInput = document.getElementById('dashboard-file-input');
    const fileDisplay = document.getElementById('dashboard-file-display');
    const filesList = document.getElementById('dashboard-files-list');
    const fileName = document.getElementById('dashboard-file-name');
    const fileSize = document.getElementById('dashboard-file-size');
    const removeBtn = document.getElementById('dashboard-remove-file');
    const uploadBtn = document.getElementById('dashboard-upload-btn');
    const uploadForm = document.getElementById('dashboard-upload-form');
    const errorMsg = document.getElementById('dashboard-error-msg');
    const successMsg = document.getElementById('dashboard-success-msg');

    if (dropzone && fileInput) {
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
            if (files.length > 0) handlePickedFiles(files);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handlePickedFiles(e.target.files);
        });

        function handlePickedFiles(files) {
            if (errorMsg) errorMsg.style.display = 'none';
            if (successMsg) successMsg.style.display = 'none';

            const pdfFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
            if (pdfFiles.length === 0) {
                if (errorMsg) {
                    errorMsg.textContent = 'Only PDF files are allowed.';
                    errorMsg.style.display = 'block';
                }
                return;
            }

            if (window.currentAnalyserMode === 'hr') {
                if (pdfFiles.length > 10) {
                    if (errorMsg) {
                        errorMsg.textContent = 'In HR Mode, you can upload up to 10 resumes at a time.';
                        errorMsg.style.display = 'block';
                    }
                    selectedFilesList = pdfFiles.slice(0, 10);
                } else {
                    selectedFilesList = pdfFiles;
                }

                if (fileDisplay) fileDisplay.style.display = 'none';
                if (filesList) {
                    filesList.innerHTML = selectedFilesList.map((f, idx) => `
                        <div class="multi-file-chip">
                            <i class="fa-solid fa-file-pdf" style="font-size: 1.3rem; color: #ef4444;"></i>
                            <div style="flex: 1; min-width: 0;">
                                <div class="multi-file-chip-name">${f.name}</div>
                                <div class="multi-file-chip-size">${(f.size / (1024 * 1024)).toFixed(2)} MB</div>
                            </div>
                            <button type="button" onclick="removeFileFromList(${idx})" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 0.9rem; padding: 0.4rem;">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    `).join('');
                    filesList.style.display = 'flex';
                }
                if (uploadBtn) uploadBtn.disabled = selectedFilesList.length === 0;
            } else {
                selectedFilesList = [pdfFiles[0]];
                if (filesList) filesList.style.display = 'none';
                if (fileName) fileName.textContent = pdfFiles[0].name;
                if (fileSize) fileSize.textContent = (pdfFiles[0].size / (1024 * 1024)).toFixed(2) + ' MB';
                if (fileDisplay) fileDisplay.style.display = 'flex';
                if (uploadBtn) uploadBtn.disabled = false;
            }
        }

        window.removeFileFromList = function(index) {
            selectedFilesList.splice(index, 1);
            if (selectedFilesList.length === 0) {
                if (filesList) { filesList.style.display = 'none'; filesList.innerHTML = ''; }
                if (uploadBtn) uploadBtn.disabled = true;
            } else {
                handlePickedFiles(selectedFilesList);
            }
        };

        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                resetFileSelections();
            });
        }

        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (errorMsg) errorMsg.style.display = 'none';
            if (successMsg) successMsg.style.display = 'none';

            if (!selectedFilesList || selectedFilesList.length === 0) {
                if (errorMsg) {
                    errorMsg.textContent = 'Please select PDF file(s) first.';
                    errorMsg.style.display = 'block';
                }
                return;
            }

            uploadBtn.disabled = true;
            uploadBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';

            const formData = new FormData();
            selectedFilesList.forEach(f => {
                formData.append('resumes', f);
            });

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
                        successMsg.querySelector('span').textContent = data.message || 'Resume(s) uploaded successfully!';
                        successMsg.style.display = 'block';
                        window.__LAST_UPLOADED_FILENAMES = data.filenames || [data.filename];
                        window.__LAST_UPLOADED_FILENAME = data.filename;
                        
                        const runBtn = document.getElementById('run-analysis-btn');
                        if (runBtn) runBtn.disabled = false;
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
                    const isHr = window.currentAnalyserMode === 'hr';
                    uploadBtn.querySelector('.btn-text').innerHTML = `<i class="fa-solid fa-arrow-up-from-bracket"></i> ${isHr ? 'Upload Resumes' : 'Upload Resume'}`;
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
            const hasFile = !!(window.__LAST_UPLOADED_FILENAMES && window.__LAST_UPLOADED_FILENAMES.length > 0) || !!window.__LAST_UPLOADED_FILENAME;
            runAnalysisBtn.disabled = !(hasJD && hasFile);
        }
    }

    window.switchAnalyserStep = function(stepNum) {
        const p1 = document.getElementById('analyser-part-1');
        const p2 = document.getElementById('analyser-part-2');
        const p3 = document.getElementById('analyser-part-3');
        const resultsSec = document.getElementById('analysis-results-section');

        const s1 = document.getElementById('stepper-step-1');
        const s2 = document.getElementById('stepper-step-2');
        const s3 = document.getElementById('stepper-step-3');

        // Reset view displays
        if (p1) p1.style.display = 'none';
        if (p2) p2.style.display = 'none';
        if (p3) p3.style.display = 'none';

        // Reset stepper UI
        [s1, s2, s3].forEach(s => {
            if (s) {
                s.classList.remove('active');
                s.style.opacity = '0.5';
                const numEl = s.querySelector('.stepper-num');
                if (numEl) {
                    numEl.style.background = 'rgba(255, 255, 255, 0.1)';
                    numEl.style.color = '#ffffff';
                }
            }
        });

        if (stepNum === 1) {
            if (p1) p1.style.display = 'flex';
            if (s1) {
                s1.classList.add('active');
                s1.style.opacity = '1';
                const numEl = s1.querySelector('.stepper-num');
                if (numEl) {
                    numEl.style.background = '#FFD000';
                    numEl.style.color = '#030712';
                }
            }
        } else if (stepNum === 2) {
            if (p2) p2.style.display = 'flex';
            if (resultsSec) resultsSec.style.display = 'flex';
            if (s2) {
                s2.classList.add('active');
                s2.style.opacity = '1';
                const numEl = s2.querySelector('.stepper-num');
                if (numEl) {
                    numEl.style.background = '#FFD000';
                    numEl.style.color = '#030712';
                }
            }
        } else if (stepNum === 3) {
            if (p3) p3.style.display = 'flex';
            if (s3) {
                s3.classList.add('active');
                s3.style.opacity = '1';
                const numEl = s3.querySelector('.stepper-num');
                if (numEl) {
                    numEl.style.background = '#FFD000';
                    numEl.style.color = '#030712';
                }
            }
            if (lastAnalysisData) {
                populateResumeBuilder(lastAnalysisData);
            }
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    let lastAnalysisData = null;

    if (runAnalysisBtn) {
        runAnalysisBtn.addEventListener('click', () => {
            const filesToAnalyze = window.__LAST_UPLOADED_FILENAMES || (window.__LAST_UPLOADED_FILENAME ? [window.__LAST_UPLOADED_FILENAME] : []);
            if (filesToAnalyze.length === 0) {
                analysisErrorMsg.textContent = "Please upload candidate PDF resume(s) first.";
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
            runAnalysisBtn.querySelector('.btn-text').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing NLP & Candidate Ranking...';

            fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filenames: filesToAnalyze,
                    job_title: jobTitle,
                    job_description: jdText,
                    mode: window.currentAnalyserMode
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
                    // Automatically switch to Part 2: Screening Report
                    window.switchAnalyserStep(2);
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
                const isHr = window.currentAnalyserMode === 'hr';
                runAnalysisBtn.querySelector('.btn-text').innerHTML = `<i class="fa-solid ${isHr ? 'fa-trophy' : 'fa-wand-magic-sparkles'}"></i> ${isHr ? 'Screen & Rank Candidates' : 'Start Analyzing Process'}`;
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

        const hrRankingBox = document.getElementById('hr-candidate-ranking-box');
        const ctaCard = document.getElementById('cta-resume-builder-card');
        const isHrMode = window.currentAnalyserMode === 'hr' || (data.candidates && data.candidates.length > 1);

        if (ctaCard) {
            ctaCard.style.display = isHrMode ? 'none' : 'flex';
        }

        if (isHrMode && data.candidates && data.candidates.length > 0) {
            if (hrRankingBox) {
                hrRankingBox.style.display = 'block';
                const totalEl = document.getElementById('hr-stat-total-candidates');
                if (totalEl) totalEl.textContent = `${data.total_candidates || data.candidates.length} Candidates Processed`;

                const tbody = document.getElementById('hr-ranking-table-body');
                if (tbody) {
                    tbody.innerHTML = data.candidates.map((cand, idx) => {
                        let rankBadgeClass = 'rank-other';
                        let rankSymbol = `#${cand.rank || idx + 1}`;
                        if (cand.rank === 1) { rankBadgeClass = 'rank-1'; rankSymbol = '🥇'; }
                        else if (cand.rank === 2) { rankBadgeClass = 'rank-2'; rankSymbol = '🥈'; }
                        else if (cand.rank === 3) { rankBadgeClass = 'rank-3'; rankSymbol = '🥉'; }

                        let gradeClass = 'grade-strong';
                        if (cand.match_percentage < 25) gradeClass = 'grade-weak';
                        else if (cand.match_percentage < 50) gradeClass = 'grade-low';
                        else if (cand.match_percentage < 75) gradeClass = 'grade-moderate';

                        return `
                            <tr class="ranking-row ${idx === 0 ? 'selected-cand-row' : ''}" onclick="selectCandidateFromLeaderboard(${idx})">
                                <td style="padding: 0.8rem 1rem;">
                                    <span class="rank-badge ${rankBadgeClass}">${rankSymbol}</span>
                                </td>
                                <td style="padding: 0.8rem 1rem;">
                                    <div style="font-weight: 700; color: #ffffff;">${cand.filename}</div>
                                    <div style="font-size: 0.78rem; color: var(--text-secondary);">${cand.job_title || 'Target Role'}</div>
                                </td>
                                <td style="padding: 0.8rem 1rem;">
                                    <div style="font-weight: 800; color: #FFD000; font-size: 1rem;">${cand.ats_score} / 100</div>
                                    <div class="ats-progress-bar-bg">
                                        <div class="ats-progress-bar-fill" style="width: ${cand.ats_score}%;"></div>
                                    </div>
                                </td>
                                <td style="padding: 0.8rem 1rem; font-weight: 700; color: #10b981;">
                                    ${cand.match_percentage}%
                                </td>
                                <td style="padding: 0.8rem 1rem;">
                                    <span class="grade-pill ${gradeClass}" style="padding: 0.2rem 0.6rem; font-size: 0.75rem;">${cand.grade}</span>
                                </td>
                                <td style="padding: 0.8rem 1rem; color: var(--text-secondary);">
                                    ${(cand.matched_skills || []).length} skills matched
                                </td>
                                <td style="padding: 0.8rem 1rem; text-align: right;">
                                    <button type="button" class="action-btn" style="background: rgba(255, 208, 0, 0.1); border: 1px solid rgba(255, 208, 0, 0.3); color: #FFD000; padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer;">
                                        View Details <i class="fa-solid fa-chevron-right" style="font-size: 0.7rem;"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        } else {
            if (hrRankingBox) hrRankingBox.style.display = 'none';
        }

        // Render details for top candidate (or first candidate)
        const targetCand = (data.candidates && data.candidates.length > 0) ? data.candidates[0] : data;
        renderSingleCandidateDetail(targetCand);
    }

    window.selectCandidateFromLeaderboard = function(idx) {
        if (!lastAnalysisData || !lastAnalysisData.candidates || !lastAnalysisData.candidates[idx]) return;
        const rows = document.querySelectorAll('.ranking-row');
        rows.forEach((r, i) => {
            if (i === idx) r.classList.add('selected-cand-row');
            else r.classList.remove('selected-cand-row');
        });

        renderSingleCandidateDetail(lastAnalysisData.candidates[idx]);
    };

    function renderSingleCandidateDetail(data) {
        // Set text details
        const fileDisp = document.getElementById('res-filename-display');
        if (fileDisp) fileDisp.textContent = `Target Document: ${data.filename} (${data.job_title || 'General Match'})`;
        
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
        if (gradeEl) {
            gradeEl.textContent = data.grade;
            gradeEl.className = 'grade-pill ';
            if (data.match_percentage >= 75) gradeEl.classList.add('grade-strong');
            else if (data.match_percentage >= 50) gradeEl.classList.add('grade-moderate');
            else if (data.match_percentage >= 25) gradeEl.classList.add('grade-low');
            else gradeEl.classList.add('grade-weak');
        }

        const recEl = document.getElementById('res-recommendation');
        if (recEl) recEl.textContent = data.recommendation;
        const resWordEl = document.getElementById('res-resume-words');
        if (resWordEl) resWordEl.textContent = data.resume_word_count || 0;
        const jdWordEl = document.getElementById('res-jd-words');
        if (jdWordEl) jdWordEl.textContent = data.jd_word_count || 0;

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
                tipsList.innerHTML = data.ats_analysis.recommendations.map(t => `
                    <li style="margin-bottom: 0.5rem; font-size: 0.88rem; color: var(--text-secondary);">${t}</li>
                `).join('');
            }
        }

        // Render Top Keyword Breakdown
        const keywordGrid = document.getElementById('res-keywords-grid');
        if (keywordGrid) {
            if (data.top_keywords && data.top_keywords.length > 0) {
                keywordGrid.innerHTML = data.top_keywords.map(kw => `
                    <div style="background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 0.6rem 0.9rem; border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-weight: 500; font-size: 0.85rem; color: #ffffff;">${kw.word}</span>
                        <span style="font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 4px; ${kw.in_resume ? 'background: rgba(16, 185, 129, 0.15); color: #10b981;' : 'background: rgba(239, 68, 68, 0.15); color: #ef4444;'}">
                            ${kw.in_resume ? 'Found' : 'Missing'}
                        </span>
                    </div>
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
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ── Resume Builder Population & Coach Logic ────────────────
    function populateResumeBuilder(data) {
        if (!data) return;

        const roleTitleEl = document.getElementById('builder-role-title');
        const atsScoreEl = document.getElementById('builder-ats-match-score');
        const atsGradeEl = document.getElementById('builder-ats-grade-badge');
        
        if (roleTitleEl) roleTitleEl.textContent = data.job_title || 'Target Job Role';
        if (atsScoreEl) atsScoreEl.textContent = `${data.match_percentage || 0}%`;
        if (atsGradeEl) {
            atsGradeEl.textContent = data.grade || 'Match Score';
            atsGradeEl.className = 'grade-pill ';
            if (data.match_percentage >= 75) atsGradeEl.classList.add('grade-strong');
            else if (data.match_percentage >= 50) atsGradeEl.classList.add('grade-moderate');
            else if (data.match_percentage >= 25) atsGradeEl.classList.add('grade-low');
            else atsGradeEl.classList.add('grade-weak');
        }

        const matched = data.matched_skills || [];
        const missing = data.missing_skills || [];
        const allRequired = Array.from(new Set([...matched, ...missing]));

        // 1. Required Skills List
        const reqListEl = document.getElementById('builder-required-skills-list');
        if (reqListEl) {
            if (allRequired.length > 0) {
                reqListEl.innerHTML = allRequired.map(s => 
                    `<span class="skill-pill" style="background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid var(--border-color);"><i class="fa-solid fa-briefcase" style="color: #FFD000;"></i> ${s}</span>`
                ).join('');
            } else {
                reqListEl.innerHTML = `<span style="font-size: 0.85rem; color: var(--text-secondary);">General job requirements parsed.</span>`;
            }
        }

        // 2. Resume Mentioned Skills
        const resumeListEl = document.getElementById('builder-resume-skills-list');
        if (resumeListEl) {
            if (matched.length > 0) {
                resumeListEl.innerHTML = matched.map(s => 
                    `<span class="skill-pill matched-pill"><i class="fa-solid fa-circle-check"></i> ${s}</span>`
                ).join('');
            } else {
                resumeListEl.innerHTML = `<span style="font-size: 0.85rem; color: var(--text-secondary);">No matching skills found in candidate PDF.</span>`;
            }
        }

        // 3. Compulsory Skills to Add
        const compulsoryContainer = document.getElementById('builder-compulsory-skills-container');
        if (compulsoryContainer) {
            if (missing.length > 0) {
                compulsoryContainer.innerHTML = missing.map(s => `
                    <div style="background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 12px; padding: 1rem 1.2rem; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.8rem;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
                                <span style="font-weight: 700; color: #f59e0b; font-size: 1rem;"><i class="fa-solid fa-circle-exclamation"></i> ${s}</span>
                                <span style="font-size: 0.7rem; font-weight: 700; background: rgba(245, 158, 11, 0.2); color: #f59e0b; padding: 0.15rem 0.5rem; border-radius: 12px;">HIGH PRIORITY</span>
                            </div>
                            <div style="font-size: 0.85rem; color: var(--text-secondary);">
                                Explicitly requested for <strong>${data.job_title || 'this role'}</strong>. Add <code>${s}</code> under your <em>Technical Skills</em> heading and mention a project or work experience achievement using it.
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                compulsoryContainer.innerHTML = `
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 1rem 1.2rem; color: #10b981; font-size: 0.9rem;">
                        <i class="fa-solid fa-circle-check" style="margin-right: 0.5rem;"></i> Great job! You have already included all compulsory technical skills required for this role.
                    </div>
                `;
            }
        }

        // 4. Recommended Extra & Bonus Skills
        const recommendedContainer = document.getElementById('builder-recommended-skills-container');
        if (recommendedContainer) {
            const bonusSkills = ["Git / GitHub", "RESTful APIs", "CI/CD Automation", "Docker", "Unit Testing / TDD", "Agile / Scrum", "System Design"];
            const extraToRecommend = bonusSkills.filter(b => !matched.includes(b));
            recommendedContainer.innerHTML = extraToRecommend.map(s => 
                `<span class="skill-pill" style="background: rgba(99, 102, 241, 0.12); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3);"><i class="fa-solid fa-plus-circle"></i> ${s}</span>`
            ).join('');
        }

        // 5. Skills & Irrelevant Noise to Remove (Score Maximizer)
        const removeContainer = document.getElementById('builder-remove-skills-container');
        if (removeContainer) {
            removeContainer.innerHTML = `
                <div style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 12px; padding: 1.2rem; display: flex; flex-direction: column; gap: 0.8rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-weight: 700; color: #ef4444; font-size: 0.95rem;"><i class="fa-solid fa-trash-can"></i> Remove Generic & Non-Technical Buzzwords</span>
                        <span style="font-size: 0.7rem; font-weight: 700; background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 0.15rem 0.5rem; border-radius: 12px;">NOISE REDUCTION</span>
                    </div>
                    <div style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5;">
                        Remove non-relevant terms such as <em>"Basic MS Office", "Windows XP", "Hardworking", "Team Player", "Internet Surfing", "Photoshop"</em>. 
                        <strong>Why?</strong> Traditional TF-IDF algorithms evaluate term frequency density. Removing filler words increases the mathematical concentration of core keywords like <code>${matched.slice(0, 3).join(', ') || 'Python'}</code>, boosting your similarity match score by up to <strong>+15%</strong>.
                    </div>
                </div>
            `;
        }

        // 6. ATS-Optimized Bullet Points
        const bulletsContainer = document.getElementById('builder-bullet-points-container');
        if (bulletsContainer) {
            const topMatched = matched.length > 0 ? matched : ["Python", "SQL"];
            const topMissing = missing.length > 0 ? missing : ["Docker", "REST API"];

            const generatedBullets = [
                `Developed and maintained high-performance applications utilizing ${topMatched.join(' and ')}, resulting in a 30% increase in system efficiency.`,
                `Engineered scalable RESTful web services and integrated ${topMissing[0] || 'Docker'} containerization to streamline automated deployment pipelines.`,
                `Collaborated with cross-functional teams to implement robust data models using ${topMatched[1] || topMatched[0]}, ensuring high availability and zero downtime.`
            ];

            bulletsContainer.innerHTML = generatedBullets.map((b, i) => `
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-color); border-radius: 10px; padding: 0.9rem 1.2rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
                    <div style="font-size: 0.88rem; color: #ffffff; line-height: 1.5; flex: 1;">
                        <i class="fa-solid fa-angle-right" style="color: #FFD000; margin-right: 0.5rem;"></i> ${b}
                    </div>
                    <button type="button" class="action-btn copy-bullet-btn" data-bullet="${b.replace(/"/g, '&quot;')}" style="background: rgba(255, 208, 0, 0.1); border: 1px solid rgba(255, 208, 0, 0.3); color: #FFD000; padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.8rem; cursor: pointer; white-space: nowrap;">
                        <i class="fa-solid fa-copy"></i> Copy
                    </button>
                </div>
            `).join('');

            // Attach copy handlers
            bulletsContainer.querySelectorAll('.copy-bullet-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const text = btn.getAttribute('data-bullet');
                    navigator.clipboard.writeText(text).then(() => {
                        const orig = btn.innerHTML;
                        btn.innerHTML = '<i class="fa-solid fa-check" style="color: #10b981;"></i> Copied!';
                        setTimeout(() => { btn.innerHTML = orig; }, 2000);
                    });
                });
            });
        }
    }

    // ── Resume Builder & Navigation Toolbar Handlers ───────────
    const btnGoToBuilder = document.getElementById('btn-go-to-resume-builder');
    const btnBackToReport = document.getElementById('btn-back-to-report');
    const btnUploadNewVersion = document.getElementById('btn-upload-new-version');

    if (btnGoToBuilder) {
        btnGoToBuilder.addEventListener('click', () => {
            window.switchAnalyserStep(3);
        });
    }

    if (btnBackToReport) {
        btnBackToReport.addEventListener('click', () => {
            window.switchAnalyserStep(2);
        });
    }

    if (btnUploadNewVersion) {
        btnUploadNewVersion.addEventListener('click', () => {
            window.switchAnalyserStep(1);
        });
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

    // ── Custom Themed Confirmation Modal Helper ──────────────────
    window.showConfirmModal = function(options = {}) {
        return new Promise((resolve) => {
            const modal = document.getElementById('custom-confirm-modal');
            const titleEl = document.getElementById('confirm-modal-title');
            const msgEl = document.getElementById('confirm-modal-message');
            const iconEl = document.getElementById('confirm-modal-icon');
            const okBtn = document.getElementById('confirm-modal-btn-ok');
            const okText = document.getElementById('confirm-modal-btn-ok-text');
            const cancelBtn = document.getElementById('confirm-modal-btn-cancel');

            if (!modal) {
                resolve(confirm(options.message || 'Are you sure?'));
                return;
            }

            if (titleEl) titleEl.textContent = options.title || 'Hire𝒽ive Confirmation';
            if (msgEl) msgEl.textContent = options.message || 'Are you sure you want to proceed?';
            if (iconEl) iconEl.className = options.icon || 'fa-solid fa-triangle-exclamation';
            if (okText) okText.textContent = options.confirmText || 'Confirm';

            modal.style.display = 'flex';

            function cleanup() {
                modal.style.display = 'none';
                okBtn.removeEventListener('click', onOk);
                cancelBtn.removeEventListener('click', onCancel);
            }

            function onOk() {
                cleanup();
                resolve(true);
            }

            function onCancel() {
                cleanup();
                resolve(false);
            }

            okBtn.addEventListener('click', onOk);
            cancelBtn.addEventListener('click', onCancel);
        });
    };

    async function deleteHistoryItem(id) {
        const confirmed = await window.showConfirmModal({
            title: 'Delete Screening Record',
            message: 'Are you sure you want to delete this candidate screening record?',
            confirmText: 'Delete Record',
            icon: 'fa-solid fa-trash-can'
        });
        if (!confirmed) return;

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
        btnClearHistory.addEventListener('click', async () => {
            const confirmed = await window.showConfirmModal({
                title: 'Clear All Screening History',
                message: 'Are you sure you want to clear ALL screening history records? This action cannot be undone.',
                confirmText: 'Clear All History',
                icon: 'fa-solid fa-triangle-exclamation'
            });
            if (!confirmed) return;

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



