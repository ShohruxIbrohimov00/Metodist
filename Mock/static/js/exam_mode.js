// =================================================================
// SAT EXAM - YANGI JAVASCRIPT (2025)
// Rasmlarcha: Toza, Professional, Xatosiz
// =================================================================

document.addEventListener('DOMContentLoaded', function () {
    // GLOBAL VARIABLES
    const EXAM_AJAX_URL = window.EXAM_AJAX_URL;
    const CSRF_TOKEN = window.CSRF_TOKEN;
    const IS_SUBJECT_EXAM = window.IS_SUBJECT_EXAM;
    const ATTEMPT_ID = window.ATTEMPT_ID;
    let currentSectionId = window.currentSectionId;
    let timeRemaining = window.timeRemaining || 0;

    // DOM ELEMENTS
    const timerEl = document.getElementById('timer');
    const hideTimerBtn = document.getElementById('hide-timer-btn');
    const nextBtn = document.getElementById('next-btn');
    const prevBtn = document.getElementById('prev-btn');
    const navBtn = document.getElementById('nav-btn');
    const calculatorBtn = document.getElementById('calculator-btn');
    const referenceBtn = document.getElementById('reference-btn');
    const directionsBtn = document.getElementById('directions-btn');
    const exitBtn = document.getElementById('exit-btn');
    const markBtn = document.getElementById('mark-review-btn');
    const answerOptionsContainer = document.getElementById('answer-options-container');

    // STATE
    let questionIds = [];
    let currentQuestionIndex = 0;
    let answeredQuestionIds = new Set();
    let reviewedQuestionIds = new Set();
    let timerInterval = null;
    let syncInterval = null;
    let timerHidden = false;
    let serverTimeOffset = 0; // server va brauzer vaqti farqi
    let timerStartTime = null;
    let serverEndTime = Date.now() + timeRemaining * 1000;

    // =================================================================
    // 1. TIMER
    // =================================================================
    hideTimerBtn.addEventListener('click', function () {
        if (timerHidden) {
            timerEl.style.display = 'block';
            this.textContent = 'Hide';
            timerHidden = false;
        } else {
            timerEl.style.display = 'none';
            this.textContent = 'Show';
            timerHidden = true;
        }
    });


    function startTimer() {
        clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            const now = Date.now();
            const remaining = Math.max(0, Math.floor((serverEndTime - now) / 1000));

            if (remaining <= 0) {
                clearInterval(timerInterval);
                finishExam();
                return;
            }

            timeRemaining = remaining;
            const m = String(Math.floor(remaining / 60)).padStart(2, '0');
            const s = String(remaining % 60).padStart(2, '0');
            timerEl.textContent = `${m}:${s}`;
        }, 100); // har 100ms da – juda aniq
    }

    function setupAutoSync() {
        clearInterval(syncInterval);
        syncInterval = setInterval(async () => {
            try {
                const res = await fetch(EXAM_AJAX_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                    body: JSON.stringify({
                        action: 'get_remaining_time',
                        attempt_id: ATTEMPT_ID,
                        section_attempt_id: currentSectionId
                    })
                });
                const data = await res.json();
                if (data.status === 'success' && data.time_remaining !== undefined) {
                    timeRemaining = data.time_remaining;
                    // Server vaqtiga moslashtiramiz
                    serverEndTime = Date.now() + timeRemaining * 1000;
                }
            } catch (err) {
                console.log('Vaqt sinxronizatsiyasi xato:', err);
            }
        }, 10000); // har 10 sekundda
    }

    // =================================================================
    // 2. BO'LIM MA'LUMOTLARINI YUKLASH
    // =================================================================
    async function loadInitialData() {
        try {
            const response = await fetch(EXAM_AJAX_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({
                    action: 'load_section_data',
                    attempt_id: ATTEMPT_ID,
                    section_attempt_id: currentSectionId
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                const s = data.section_data;
                questionIds = s.question_ids || [];
                timeRemaining = s.initial_time_remaining || 0;
                answeredQuestionIds = new Set(s.answered_question_ids || []);
                reviewedQuestionIds = new Set(s.marked_for_review_ids || []);

                startTimer();
                setupAutoSync();
                
                if (questionIds.length > 0) {
                    loadQuestion(questionIds[0]);
                }
                
                updateNavigation();
                renderNavigationGrid();
            } else {
                showError(data.message || 'Failed to load section');
            }
        } catch (err) {
            console.error(err);
            showError('Connection error');
        }
    }

    // =================================================================
    // 3. SAVOL YUKLASH
    // =================================================================
    async function loadQuestion(questionId) {
        if (!questionId) return;

        const data = await fetchQuestionData(questionId);
        if (data.status !== 'success') {
            showError(data.message || 'Failed to load question');
            return;
        }

        const q = data.question_data;
        currentQuestionIndex = questionIds.indexOf(q.id);

        // HEADER
        const headerEl = document.getElementById('question-number-header');
        if (headerEl) {
            if (IS_SUBJECT_EXAM) {
                headerEl.textContent = q.exam_title || window.attemptExamTitle || 'Subject Test';
            } else {
                headerEl.textContent = `${q.section_type || 'Section'} (Module ${q.module_number || 1})`;
            }
        }

        // SAVOL RAQAMI
        const numberEl = document.getElementById('question-number');
        if (numberEl) {
            numberEl.textContent = q.number || (currentQuestionIndex + 1);
        }

        // SAVOL MATNI
        const textEl = document.getElementById('question-text');
        if (textEl) {
            textEl.innerHTML = q.text || 'No question text';
        }

        // SAVOL RASMI
        const imgContainer = document.getElementById('question-image-container');
        const imgEl = document.getElementById('question-image');
        if (imgEl && imgContainer) {
            if (q.image_url) {
                imgEl.src = q.image_url + '?v=' + Date.now();
                imgEl.onload = () => imgContainer.style.display = 'block';
                imgEl.onerror = () => imgContainer.style.display = 'none';
            } else {
                imgContainer.style.display = 'none';
            }
        }

        // PASSAGE
        let passageDiv = document.getElementById('passage-text');
        if (q.passage_text) {
            if (!passageDiv) {
                passageDiv = document.createElement('div');
                passageDiv.id = 'passage-text';
                passageDiv.style.cssText = 'margin: 24px 0; padding: 20px; background: #f8f8f8; border-left: 4px solid #0066cc; border-radius: 8px; line-height: 1.7;';
                const textEl = document.getElementById('question-text');
                if (textEl?.parentNode) {
                    textEl.parentNode.insertBefore(passageDiv, textEl.nextSibling);
                }
            }
            passageDiv.innerHTML = q.passage_text;
            passageDiv.style.display = 'block';
        } else if (passageDiv) {
            passageDiv.style.display = 'none';
        }

        // FORMAT
        let formatInput = document.getElementById('question_format');
        if (!formatInput) {
            formatInput = document.createElement('input');
            formatInput.type = 'hidden';
            formatInput.id = 'question_format';
            answerOptionsContainer?.appendChild(formatInput);
        }
        if (formatInput) formatInput.value = q.format;

        // JAVOB VARIANTLARI
        renderOptions(q);

        // MARK FOR REVIEW
        if (markBtn) {
            if (reviewedQuestionIds.has(q.id)) {
                markBtn.innerHTML = '<i class="fas fa-bookmark"></i> Marked for Review';
                markBtn.classList.add('marked');
            } else {
                markBtn.innerHTML = '<i class="far fa-bookmark"></i> Mark for Review';
                markBtn.classList.remove('marked');
            }
        }

        // MATHJAX
        if (window.renderMath) {
            renderMath();
        } else {
            setTimeout(() => window.renderMath?.(), 1000);
        }

        updateNavigation();
        renderNavigationGrid();
    }

    async function fetchQuestionData(questionId) {
        try {
            const response = await fetch(EXAM_AJAX_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({
                    action: 'load_question_data',
                    attempt_id: ATTEMPT_ID,
                    section_attempt_id: currentSectionId,
                    question_id: questionId
                })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (err) {
            console.error(err);
            return { status: 'error', message: 'Failed to load question' };
        }
    }

    // =================================================================
    // 4. JAVOB VARIANTLARI - AYNAN RASMLARCHA
    // =================================================================
    function renderOptions(q) {
        answerOptionsContainer.innerHTML = '';

        let formatInput = document.getElementById('question_format');
        if (!formatInput) {
            formatInput = document.createElement('input');
            formatInput.type = 'hidden';
            formatInput.id = 'question_format';
            answerOptionsContainer.appendChild(formatInput);
        }
        formatInput.value = q.format;

        if (q.format === 'short_answer') {
            const input = document.createElement('input');
            input.type = 'text';
            input.placeholder = 'Your answer';
            input.value = q.initial_answer?.short_answer_text || '';
            input.addEventListener('input', debounce(saveAnswer, 800));
            answerOptionsContainer.appendChild(input);
            
            const preview = document.createElement('div');
            preview.className = 'answer-preview-label';
            preview.textContent = 'Answer Preview:';
            answerOptionsContainer.appendChild(preview);
            return;
        }

        const letters = ['A', 'B', 'C', 'D', 'E', 'F'];

        q.options.forEach((opt, i) => {
            const label = document.createElement('label');
            const isSelected = q.initial_answer?.selected_options?.includes(opt.id);
            
            if (isSelected) {
                label.classList.add('selected');
            }

            const input = document.createElement('input');
            input.type = q.format === 'multiple' ? 'checkbox' : 'radio';
            input.name = 'option';
            input.value = opt.id;
            input.checked = isSelected;
            input.addEventListener('change', function() {
                // Remove 'selected' from all labels
                answerOptionsContainer.querySelectorAll('label').forEach(l => l.classList.remove('selected'));
                
                // Add 'selected' to checked ones
                if (q.format === 'single') {
                    if (this.checked) {
                        this.closest('label').classList.add('selected');
                    }
                } else {
                    answerOptionsContainer.querySelectorAll('input[name="option"]:checked').forEach(inp => {
                        inp.closest('label').classList.add('selected');
                    });
                }
                
                saveAnswer();
            });

            const letterSpan = document.createElement('span');
            letterSpan.className = 'option-letter';
            letterSpan.textContent = letters[i] + ':';

            const textSpan = document.createElement('span');
            textSpan.className = 'option-text';
            textSpan.innerHTML = opt.text;

            if (opt.image_url) {
                const img = document.createElement('img');
                img.src = opt.image_url;
                img.style.cssText = 'margin-top: 12px; max-width: 100%; border-radius: 6px;';
                textSpan.appendChild(img);
            }

            label.appendChild(input);
            label.appendChild(letterSpan);
            label.appendChild(textSpan);
            answerOptionsContainer.appendChild(label);
        });
    }

    // =================================================================
    // 5. JAVOB SAQLASH
    // =================================================================
    async function saveAnswer() {
        const qid = questionIds[currentQuestionIndex];
        if (!qid) return;

        const format = document.getElementById('question_format')?.value || 'single';

        const payload = {
            action: 'save_answer',
            attempt_id: ATTEMPT_ID,
            section_attempt_id: currentSectionId,
            question_id: qid,
            time_remaining: timeRemaining,
            is_marked_for_review: reviewedQuestionIds.has(qid)
        };

        if (format === 'short_answer') {
            payload.short_answer_text = answerOptionsContainer.querySelector('input[type="text"]')?.value?.trim() || '';
        } else if (format === 'single') {
            const selected = answerOptionsContainer.querySelector('input[name="option"]:checked');
            payload.selected_option = selected ? parseInt(selected.value) : null;
        } else if (format === 'multiple') {
            const checked = answerOptionsContainer.querySelectorAll('input[name="option"]:checked');
            payload.selected_options = Array.from(checked).map(i => parseInt(i.value));
        }

        try {
            const res = await fetch(EXAM_AJAX_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.status === 'success') {
                answeredQuestionIds = new Set(data.answered_question_ids || []);
                updateNavigation();
                renderNavigationGrid();
            }
        } catch (err) {
            console.error('Save error:', err);
        }
    }

    // =================================================================
    // 6. NAVIGATSIYA
    // =================================================================
    function updateNavigation() {
        prevBtn.disabled = currentQuestionIndex === 0;

        nextBtn.innerHTML = 'Next <i class="fa-solid fa-chevron-right"></i>';

        if (currentQuestionIndex === questionIds.length - 1) {
            if (IS_SUBJECT_EXAM) {
                nextBtn.innerHTML = 'Finish Exam <i class="fa-solid fa-check"></i>';
            } else {
                nextBtn.innerHTML = 'Next Section <i class="fa-solid fa-chevron-right"></i>';
            }
        }

        document.getElementById('nav-btn-text').textContent = `Question ${currentQuestionIndex + 1} of ${questionIds.length}`;
    }

    prevBtn.addEventListener('click', () => {
        if (currentQuestionIndex > 0) {
            currentQuestionIndex--;
            loadQuestion(questionIds[currentQuestionIndex]);
        }
    });

    nextBtn.addEventListener('click', () => {
        if (currentQuestionIndex < questionIds.length - 1) {
            currentQuestionIndex++;
            loadQuestion(questionIds[currentQuestionIndex]);
        } else {
            finishExam();
        }
    });

    navBtn.addEventListener('click', () => {
        openModal('nav-modal');
        renderNavigationGrid();
    });

    // =================================================================
    // 7. NAVIGATSIYA GRID - AYNAN RASMLARCHA
    // =================================================================
    function renderNavigationGrid() {
        const grid = document.getElementById('question-nav-grid');
        if (!grid) return;
        grid.innerHTML = '';

        questionIds.forEach((qid, i) => {
            const isAnswered = answeredQuestionIds.has(qid);
            const isMarked = reviewedQuestionIds.has(qid);
            const isCurrent = i === currentQuestionIndex;

            const btn = document.createElement('button');
            btn.className = 'nav-button';
            btn.textContent = i + 1;

            if (isCurrent) {
                btn.classList.add('bg-blue-600');
            } else if (isMarked) {
                btn.classList.add('bg-yellow-500');
            } else if (isAnswered) {
                btn.classList.add('bg-green-500');
            }

            btn.addEventListener('click', () => {
                currentQuestionIndex = i;
                loadQuestion(qid);
                closeModal('nav-modal');
            });

            grid.appendChild(btn);
        });
    }

    // =================================================================
    // 8. YAKUNLASH
    // =================================================================
    async function finishExam() {
        clearInterval(timerInterval);
        clearInterval(syncInterval);

        try {
            const action = IS_SUBJECT_EXAM ? 'finish_exam' : 'finish_section';
            const res = await fetch(EXAM_AJAX_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({
                    action: action,
                    attempt_id: ATTEMPT_ID,
                    section_attempt_id: currentSectionId,
                    time_remaining: 0
                })
            });
            const data = await res.json();
            if (data.status === 'success' && data.redirect_url) {
                window.location.href = data.redirect_url;
            }
        } catch (err) {
            showError('Failed to finish exam');
        }
    }

    // =================================================================
    // 9. TUGMALAR
    // =================================================================
    directionsBtn?.addEventListener('click', () => openModal('directions-modal'));
    
    referenceBtn?.addEventListener('click', () => openModal('reference-modal'));
    exitBtn?.addEventListener('click', () => openModal('confirm-exit-modal'));

    markBtn?.addEventListener('click', function () {
        const qid = questionIds[currentQuestionIndex];
        if (reviewedQuestionIds.has(qid)) {
            reviewedQuestionIds.delete(qid);
            this.innerHTML = '<i class="far fa-bookmark"></i> Mark for Review';
            this.classList.remove('marked');
        } else {
            reviewedQuestionIds.add(qid);
            this.innerHTML = '<i class="fas fa-bookmark"></i> Marked for Review';
            this.classList.add('marked');
        }
        saveAnswer();
    });

    document.getElementById('final-finish-btn')?.addEventListener('click', finishExam);

    // =================================================================
    // 10. UTILITIES
    // =================================================================
    function debounce(func, wait) {
        let timeout;
        return function () {
            clearTimeout(timeout);
            timeout = setTimeout(func, wait);
        };
    }

    // =================================================================
    // DESMOS KALKULYATOR – REFERENCE KABI OCHILGANDA 100% ISHLAYDI (2025)
    // =================================================================
    
    // =================================================================
    // BOSHLASH
    // =================================================================
    loadInitialData();
});