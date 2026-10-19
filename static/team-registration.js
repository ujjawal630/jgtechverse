/**
 * JG TechVerse 2026 — Registration & Project Submission Engine
 * Cyber-Academic Editorial Experience with 5-Stage Stepper & Multi-Project Builder
 */

// ==========================================================================
// CONSTANTS & STATE REGISTRY
// ==========================================================================

const MAX_MEMBERS = 5; // Exactly 5 members allowed in the team members table
const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const TOTAL_STEPS = 5;

const arenaDescriptions = {
    Buddhi: "AI Model Building & Machine Learning",
    Fiontar: "Startup & Innovation Incubation",
    Talos: "Robotic Arena & Autonomous Systems",
    Pegasus: "Drone Fest & UAV Avionics",
    Promethia: "Coding Challenge & Scalable Systems",
    Mercatus: "Trading & Quantitative Financial Analytics"
};

const arenaIcons = {
    Buddhi: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>`,
    Fiontar: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="18" x2="15" y2="18"></line><line x1="10" y1="22" x2="14" y2="22"></line><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"></path></svg>`,
    Talos: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8.01" y2="16"></line><line x1="16" y1="16" x2="16.01" y2="16"></line></svg>`,
    Pegasus: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>`,
    Promethia: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`,
    Mercatus: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line><polyline points="3 8 9 2 15 8 21 2"></polyline></svg>`
};

// DOM Elements
const form = document.getElementById("teamForm");
const message = document.getElementById("message");
const membersBody = document.getElementById("membersBody");
const addMemberButton = document.getElementById("addMember");
const memberCountBadge = document.getElementById("memberCountBadge");
const memberLimitNotice = document.getElementById("memberLimitNotice");
const arenaCheckboxes = document.querySelectorAll('input[name="arenas"]');
const projectsContainer = document.getElementById("projectsContainer");
const addProjectBtn = document.getElementById("addProjectBtn");
const projectCountNotice = document.getElementById("projectCountNotice");

// Stepper DOM Elements
const stepPills = document.querySelectorAll(".tv-stepper-pill");
const formSteps = document.querySelectorAll(".tv-form-step");
const stepperProgressFill = document.getElementById("stepperProgressFill");
const stepperPercentText = document.getElementById("stepperPercentText");
const stepErrorBanner = document.getElementById("stepErrorBanner");
const stepErrorText = document.getElementById("stepErrorText");
const reviewSummaryContainer = document.getElementById("reviewSummaryContainer");

// Stepper State
let currentStep = 1;
let furthestStepReached = 1;

// Ephemeral file storage Map keyed by unique projectId
const projectFilesMap = new Map();

// ==========================================================================
// STEPPER ENGINE & NAVIGATION
// ==========================================================================

function showStepError(msg, targetElement = null) {
    if (stepErrorBanner && stepErrorText) {
        stepErrorText.textContent = msg;
        stepErrorBanner.style.display = "flex";
        if (window.TVMotion && typeof window.TVMotion.shakeErrorBanner === "function") {
            window.TVMotion.shakeErrorBanner(stepErrorBanner);
        }
    }
    if (message) {
        message.textContent = msg;
    }
    if (targetElement) {
        targetElement.classList.add("is-invalid");
        targetElement.focus();
        targetElement.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function hideStepError() {
    if (stepErrorBanner) {
        stepErrorBanner.style.display = "none";
        stepErrorBanner.classList.remove("tv-banner-shake");
    }
    if (message) {
        message.textContent = "";
    }
    document.querySelectorAll(".is-invalid").forEach(el => el.classList.remove("is-invalid"));
}

function updateStepperUI() {
    // 1. Progress Bar & Meta
    const percent = Math.round((currentStep / TOTAL_STEPS) * 100);
    if (stepperProgressFill) {
        stepperProgressFill.style.width = `${percent}%`;
    }
    if (stepperPercentText) {
        stepperPercentText.textContent = `Step ${currentStep} of ${TOTAL_STEPS} · ${percent}% Complete`;
    }

    // 2. Stepper Pills
    stepPills.forEach(pill => {
        const stepNum = parseInt(pill.dataset.step, 10);
        pill.classList.remove("active");
        pill.setAttribute("aria-selected", "false");

        if (stepNum === currentStep) {
            pill.classList.add("active");
            pill.classList.remove("completed");
            pill.setAttribute("aria-selected", "true");
        } else if (stepNum < currentStep) {
            pill.classList.add("completed");
        } else {
            pill.classList.remove("completed");
        }
    });

    // 3. Form Step Panels
    formSteps.forEach(stepPanel => {
        const stepNum = parseInt(stepPanel.dataset.step, 10);
        if (stepNum === currentStep) {
            stepPanel.classList.add("active");
        } else {
            stepPanel.classList.remove("active");
        }
    });

    // Scroll to top of the form smoothly with content reveal
    if (form) {
        if (window.TVMotion && typeof window.TVMotion.scrollToElement === "function") {
            const activeStepEl = document.querySelector(".tv-form-step.active") || form;
            window.TVMotion.scrollToElement(form, function () {
                window.TVMotion.triggerContentReveal(activeStepEl);
            });
        } else {
            const headerOffset = 80;
            const formPosition = form.getBoundingClientRect().top + window.pageYOffset - headerOffset;
            window.scrollTo({ top: formPosition, behavior: "smooth" });
        }
    }
}

function validateStep(stepNumber) {
    hideStepError();

    // ------------------------------------------
    // STEP 1: Team & Leader Details
    // ------------------------------------------
    if (stepNumber === 1) {
        const teamName = form.teamName ? form.teamName.value.trim() : "";
        const leaderName = form.leaderName ? form.leaderName.value.trim() : "";
        const leaderEmail = form.leaderEmail ? form.leaderEmail.value.trim().toLowerCase() : "";
        const leaderPhone = form.leaderPhone ? form.leaderPhone.value.trim() : "";

        if (!teamName) {
            showStepError("Please enter your team name.", form.teamName);
            return false;
        }

        if (!leaderName) {
            showStepError("Please enter the team leader's full name.", form.leaderName);
            return false;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!leaderEmail || !emailRegex.test(leaderEmail)) {
            showStepError("Please enter a valid official leader email address.", form.leaderEmail);
            return false;
        }

        const phoneRegex = /^[0-9+\-\s()]{8,18}$/;
        if (!leaderPhone || !phoneRegex.test(leaderPhone)) {
            showStepError("Please enter a valid phone number (8–18 characters).", form.leaderPhone);
            return false;
        }

        return true;
    }

    // ------------------------------------------
    // STEP 2: Academic & Institutional Credentials
    // ------------------------------------------
    if (stepNumber === 2) {
        const collegeName = form.collegeName ? form.collegeName.value.trim() : "";
        const collegeCity = form.collegeCity ? form.collegeCity.value.trim() : "";
        const leaderSection = form.leaderSection ? form.leaderSection.value.trim() : "";
        const leaderYear = form.leaderYear ? form.leaderYear.value.trim() : "";

        if (!collegeName) {
            showStepError("Please enter your college or university name.", form.collegeName);
            return false;
        }

        if (!collegeCity) {
            showStepError("Please enter your campus city and state.", form.collegeCity);
            return false;
        }

        if (!leaderSection) {
            showStepError("Please enter the leader's academic section.", form.leaderSection);
            return false;
        }

        if (!leaderYear) {
            showStepError("Please select the leader's year of study.", form.leaderYear);
            return false;
        }

        return true;
    }

    // ------------------------------------------
    // STEP 3: Team Members Roster
    // ------------------------------------------
    if (stepNumber === 3) {
        const rows = membersBody ? membersBody.querySelectorAll("tr") : [];
        if (rows.length < 1) {
            showStepError("A team must contain at least 1 member.");
            return false;
        }

        if (rows.length > MAX_MEMBERS) {
            showStepError(`A team cannot exceed ${MAX_MEMBERS} members.`);
            return false;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const nameInput = row.querySelector('input[name="memberName[]"]');
            const emailInput = row.querySelector('input[name="memberEmail[]"]');
            const sectionInput = row.querySelector('input[name="memberSection[]"]');
            const yearInput = row.querySelector('select[name="memberYear[]"]');

            const name = nameInput ? nameInput.value.trim() : "";
            const email = emailInput ? emailInput.value.trim().toLowerCase() : "";
            const section = sectionInput ? sectionInput.value.trim() : "";
            const year = yearInput ? yearInput.value.trim() : "";

            if (!name) {
                showStepError(`Member #${i + 1}: Please enter member's full name.`, nameInput);
                return false;
            }

            if (!email || !emailRegex.test(email)) {
                showStepError(`Member #${i + 1}: Please enter a valid email address.`, emailInput);
                return false;
            }

            if (!section) {
                showStepError(`Member #${i + 1}: Please enter academic section.`, sectionInput);
                return false;
            }

            if (!year) {
                showStepError(`Member #${i + 1}: Please select year of study.`, yearInput);
                return false;
            }
        }

        return true;
    }

    // ------------------------------------------
    // STEP 4: Challenge Arenas & Project Submissions
    // ------------------------------------------
    if (stepNumber === 4) {
        const selectedArenas = getSelectedArenas();
        if (selectedArenas.length === 0) {
            showStepError("Please select at least one challenge arena track.");
            document.getElementById("arenas-title")?.scrollIntoView({ behavior: "smooth", block: "center" });
            return false;
        }

        const arenaSections = projectsContainer ? [...projectsContainer.querySelectorAll(".tv-arena-form-section")] : [];
        if (arenaSections.length === 0) {
            showStepError("Please select at least one challenge arena track above to open its submission section.");
            document.getElementById("arenas-title")?.scrollIntoView({ behavior: "smooth", block: "center" });
            return false;
        }

        for (let sIdx = 0; sIdx < arenaSections.length; sIdx++) {
            const section = arenaSections[sIdx];
            const arenaName = section.dataset.arena;
            const cards = [...section.querySelectorAll(".project-card")];

            if (cards.length === 0) {
                showStepError(`[${arenaName} Arena] Please add at least one question/project submission.`);
                return false;
            }

            for (let cIdx = 0; cIdx < cards.length; cIdx++) {
                const card = cards[cIdx];
                const pId = card.dataset.projectId;
                const titleInput = card.querySelector(".project-title-input");
                const problemInput = card.querySelector(".project-problem-input");
                const solutionInput = card.querySelector(".project-solution-input");
                const ghInput = card.querySelector(".project-github-input");
                const files = projectFilesMap.get(pId) || [];

                const titleVal = titleInput ? titleInput.value.trim() : "";
                const problemVal = problemInput ? problemInput.value.trim() : "";
                const solutionVal = solutionInput ? solutionInput.value.trim() : "";
                const ghVal = ghInput ? ghInput.value.trim() : "";
                const entryLabel = `[${arenaName} — Question #${cIdx + 1}]`;

                if (!titleVal) {
                    showStepError(`${entryLabel} Please enter a project title.`, titleInput);
                    return false;
                }

                if (!problemVal) {
                    showStepError(`${entryLabel} Please provide a problem statement / challenge question.`, problemInput);
                    return false;
                }

                if (!solutionVal) {
                    showStepError(`${entryLabel} Please explain your proposed solution and architecture.`, solutionInput);
                    return false;
                }

                const ghCheck = validateGitHubRepoUrl(ghVal);
                if (!ghCheck.valid) {
                    showStepError(`${entryLabel} ${ghCheck.message}`, ghInput);
                    return false;
                }

                if (files.length === 0) {
                    showStepError(`${entryLabel} Please upload at least one evidence/architecture image.`);
                    card.querySelector(".tv-upload-dropzone, .project-evidence-input")?.scrollIntoView({ behavior: "smooth", block: "center" });
                    return false;
                }

                const fileError = validateFiles(files);
                if (fileError) {
                    showStepError(`${entryLabel} ${fileError}`);
                    return false;
                }
            }
        }

        return true;
    }

    return true;
}

function goToStep(targetStep) {
    if (targetStep < 1 || targetStep > TOTAL_STEPS) return;

    // If attempting to jump forward, validate all intermediate steps sequentially
    if (targetStep > currentStep) {
        for (let s = currentStep; s < targetStep; s++) {
            if (!validateStep(s)) {
                return; // Stop at the first invalid step
            }
        }
    } else {
        hideStepError();
    }

    currentStep = targetStep;
    if (currentStep > furthestStepReached) {
        furthestStepReached = currentStep;
    }

    if (currentStep === 5) {
        renderReviewSummary();
    }

    updateStepperUI();
}

// Bind Click Listeners for Stepper Navigation
document.addEventListener("DOMContentLoaded", () => {
    // Stepper Pills click (allow jumping to any already visited step)
    stepPills.forEach(pill => {
        pill.addEventListener("click", () => {
            const stepNum = parseInt(pill.dataset.step, 10);
            if (stepNum <= furthestStepReached || stepNum < currentStep) {
                goToStep(stepNum);
            } else {
                goToStep(stepNum);
            }
        });
    });

    // Next Step buttons
    document.querySelectorAll(".step-next-btn[data-next]").forEach(btn => {
        btn.addEventListener("click", () => {
            const next = parseInt(btn.dataset.next, 10);
            goToStep(next);
        });
    });

    // Previous Step buttons
    document.querySelectorAll(".step-prev-btn[data-prev]").forEach(btn => {
        btn.addEventListener("click", () => {
            const prev = parseInt(btn.dataset.prev, 10);
            goToStep(prev);
        });
    });
});

// ==========================================================================
// MEMBER ROSTER MANAGEMENT
// ==========================================================================

function updateMemberNumbers() {
    const rows = membersBody ? membersBody.querySelectorAll("tr") : [];
    const count = rows.length;

    rows.forEach((row, index) => {
        const numCell = row.querySelector(".row-number");
        if (numCell) numCell.textContent = index + 1;
        const removeBtn = row.querySelector(".remove-btn");
        if (removeBtn) {
            removeBtn.disabled = count === 1;
            removeBtn.title = count === 1 ? "At least one member is required." : "Remove member";
        }
    });

    if (memberCountBadge) {
        memberCountBadge.textContent = `${count} / ${MAX_MEMBERS} Members Added`;
    }

    const isMax = count >= MAX_MEMBERS;
    if (addMemberButton) {
        addMemberButton.disabled = isMax;
        addMemberButton.title = isMax ? "Maximum 5 team members reached." : "Add team member";
    }

    if (memberLimitNotice) {
        memberLimitNotice.textContent = isMax
            ? "Maximum 5 members reached (Limit enforced)."
            : `Add up to ${MAX_MEMBERS - count} more member${MAX_MEMBERS - count === 1 ? "" : "s"}.`;
    }
}

function addMember() {
    if (!membersBody) return;
    if (membersBody.querySelectorAll("tr").length >= MAX_MEMBERS) {
        return;
    }

    const row = document.createElement("tr");

    row.innerHTML = `
        <td class="row-number" style="font-family:var(--font-mono); font-weight:700; color:var(--color-crimson); text-align:center;"></td>
        <td>
            <input type="text" name="memberName[]" placeholder="Member full name" required autocomplete="name" aria-label="Member full name">
        </td>
        <td>
            <input type="email" name="memberEmail[]" placeholder="student@institution.edu" required autocomplete="email" aria-label="Member email address">
        </td>
        <td>
            <input type="text" name="memberSection[]" list="sectionDatalist" placeholder="e.g. A or Section" maxlength="50" required aria-label="Member academic section">
        </td>
        <td>
            <select name="memberYear[]" required aria-label="Member academic year of study">
                <option value="">Year</option>
                <option value="1">1st Year</option>
                <option value="2">2nd Year</option>
                <option value="3">3rd Year</option>
                <option value="4">4th Year</option>
            </select>
        </td>
        <td style="text-align: center;">
            <button type="button" class="remove-btn" aria-label="Remove member" title="Remove member">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </td>
    `;

    row.querySelector(".remove-btn").addEventListener("click", () => {
        if (membersBody.querySelectorAll("tr").length > 1) {
            row.remove();
            updateMemberNumbers();
        }
    });

    membersBody.appendChild(row);
    updateMemberNumbers();
}

if (addMemberButton) {
    addMemberButton.addEventListener("click", addMember);
}

// Initial default member
addMember();

// ==========================================================================
// VALIDATION UTILITIES (FILES & GITHUB)
// ==========================================================================

function validateFiles(files) {
    for (const file of files) {
        if (!ALLOWED_TYPES.includes(file.type)) {
            return `${file.name}: Please upload PNG, JPG or WEBP image formats only.`;
        }

        if (file.size > MAX_FILE_SIZE) {
            return `${file.name} is larger than the 5 MB limit.`;
        }
    }
    return "";
}

function validateGitHubRepoUrl(url) {
    if (!url || typeof url !== "string") {
        return { valid: false, message: "GitHub repository URL is mandatory." };
    }
    let cleaned = url.trim();
    if (!cleaned) {
        return { valid: false, message: "GitHub repository URL is mandatory for project evaluation." };
    }
    if (cleaned.toLowerCase().startsWith("github.com/") || cleaned.toLowerCase().startsWith("www.github.com/")) {
        cleaned = "https://" + cleaned;
    }
    let parsed;
    try {
        parsed = new URL(cleaned);
    } catch (e) {
        return { valid: false, message: "Please enter a valid URL (e.g. https://github.com/owner/repository)." };
    }

    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        return { valid: false, message: "GitHub repository URL must use HTTPS (e.g. https://github.com/owner/repo)." };
    }

    const hostname = parsed.hostname.toLowerCase();
    if (hostname !== "github.com" && hostname !== "www.github.com") {
        return { valid: false, message: `Only GitHub repositories are accepted (received: ${hostname}).` };
    }

    if (parsed.username || parsed.password) {
        return { valid: false, message: "Repository URL must not contain embedded credentials." };
    }

    const parts = parsed.pathname.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
    if (parts.length === 0) {
        return { valid: false, message: "Please enter your actual project repository URL, not the GitHub homepage." };
    }
    if (parts.length === 1) {
        return { valid: false, message: "Please provide the specific repository URL (e.g. https://github.com/owner/repo), not just a user or organization profile." };
    }

    const owner = parts[0];
    const rawRepo = parts[1];
    const repoClean = rawRepo.toLowerCase().endsWith(".git") ? rawRepo.slice(0, -4) : rawRepo;

    const ownerPattern = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/;
    const repoPattern = /^[a-zA-Z0-9_.-]{1,100}$/;

    if (!ownerPattern.test(owner)) {
        return { valid: false, message: `Invalid GitHub owner/organization name: "${owner}".` };
    }

    if (!repoPattern.test(repoClean) || repoClean === "." || repoClean === "..") {
        return { valid: false, message: `Invalid GitHub repository name: "${rawRepo}".` };
    }

    const reserved = new Set([
        "features", "pricing", "security", "customer-stories", "enterprise",
        "explore", "topics", "trending", "collections", "events", "readme",
        "organizations", "settings", "notifications", "login", "join", "about",
        "contact", "site", "blog", "marketplace", "pulls", "issues", "sponsors"
    ]);
    if (reserved.has(owner.toLowerCase())) {
        return { valid: false, message: `"${owner}" is a GitHub platform section, not a project repository.` };
    }

    return { valid: true, normalized: `https://github.com/${owner}/${rawRepo}` };
}

// ==========================================================================
// DEDICATED ARENA SECTIONS & MULTI-QUESTION SUBMISSION CONTROLS
// ==========================================================================

function getSelectedArenas() {
    return [...arenaCheckboxes]
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.value);
}

function updateProjectFileDisplay(card, projectId) {
    const output = card.querySelector(".project-evidence-names");
    if (!output) return;

    const files = projectFilesMap.get(projectId) || [];
    if (files.length === 0) {
        output.innerHTML = '<span style="color:var(--color-text-muted); font-size:12px;">No images uploaded yet. Upload at least one architecture diagram or evidence photo.</span>';
        return;
    }

    const fileBadges = files.map((file, fIndex) => {
        const sizeKb = Math.round(file.size / 1024);
        return `<span style="display:inline-flex; align-items:center; gap:6px; background:var(--color-bg-surface); border:1px solid var(--color-border-default); border-radius:4px; padding:4px 9px; font-size:11.5px; font-weight:600; color:var(--color-text-primary); box-shadow:var(--shadow-xs);">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
            <span>${file.name} (${sizeKb} KB)</span>
            <button type="button" data-file-index="${fIndex}" class="remove-single-file-btn" style="background:none; border:none; color:var(--color-crimson); font-size:14px; font-weight:800; cursor:pointer; line-height:1; padding:0 2px;" title="Remove file">&times;</button>
        </span>`;
    }).join("");

    output.innerHTML = `
        <div style="margin-top:10px;">
            <div style="font-weight:700; color:var(--color-text-primary); font-size:12px; margin-bottom:6px; display:inline-flex; align-items:center; gap:6px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span>${files.length} Evidence Image${files.length === 1 ? "" : "s"} Attached:</span>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                ${fileBadges}
                <button type="button" class="clear-files-btn" style="background:none; border:none; color:var(--color-crimson); font-size:11.5px; font-weight:700; cursor:pointer; text-decoration:underline; margin-left:8px;" title="Clear all files for this project">Clear all</button>
            </div>
        </div>
    `;

    // Clear all files
    const clearBtn = output.querySelector(".clear-files-btn");
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            projectFilesMap.set(projectId, []);
            updateProjectFileDisplay(card, projectId);
        });
    }

    // Remove single file
    output.querySelectorAll(".remove-single-file-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const index = parseInt(btn.dataset.fileIndex, 10);
            const currentFiles = projectFilesMap.get(projectId) || [];
            currentFiles.splice(index, 1);
            projectFilesMap.set(projectId, currentFiles);
            updateProjectFileDisplay(card, projectId);
        });
    });
}

function renderEmptyArenasNotice() {
    if (!projectsContainer) return;
    projectsContainer.innerHTML = `
        <div class="empty-arenas-notice">
            <div style="width: 52px; height: 52px; border-radius: 50%; background: var(--color-crimson-light); color: var(--color-crimson); display: grid; place-items: center; margin: 0 auto 12px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <polyline points="9 11 12 14 22 4"></polyline>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                </svg>
            </div>
            <h3 style="font-family: var(--font-heading); font-size: 16px; font-weight: 700; color: var(--color-text-primary); margin: 0 0 6px;">Select Challenge Arenas Above</h3>
            <p style="font-size: 13.5px; color: var(--color-text-muted); max-width: 460px; margin: 0 auto;">Choose one or more challenge arena tracks in Stage 04 above. Each selected arena will open its own dedicated submission section here.</p>
        </div>
    `;
    updateTotalProjectCount();
}

function updateTotalProjectCount() {
    const totalCards = projectsContainer ? projectsContainer.querySelectorAll(".project-card").length : 0;
    const totalArenas = projectsContainer ? projectsContainer.querySelectorAll(".tv-arena-form-section").length : 0;

    if (projectCountNotice) {
        if (totalArenas === 0) {
            projectCountNotice.textContent = "0 Projects Added";
        } else {
            projectCountNotice.textContent = `${totalCards} Question${totalCards === 1 ? '' : 's'} across ${totalArenas} Arena${totalArenas === 1 ? '' : 's'}`;
        }
    }
}

function updateArenaSectionEntryNumbers(arenaSection) {
    if (!arenaSection) return;
    const cards = arenaSection.querySelectorAll(".project-card");
    const count = cards.length;

    cards.forEach((card, index) => {
        const numSpan = card.querySelector(".entry-num");
        if (numSpan) {
            numSpan.textContent = `#${index + 1}`;
        }
        const removeBtn = card.querySelector(".remove-project-btn");
        if (removeBtn) {
            removeBtn.disabled = count <= 1;
            removeBtn.title = count <= 1
                ? "At least one question is required for this arena. Uncheck the arena above to remove the entire track."
                : "Remove this question entry";
            removeBtn.style.opacity = count <= 1 ? "0.4" : "1";
        }
    });

    const countBadge = arenaSection.querySelector(".arena-q-count");
    if (countBadge) {
        countBadge.textContent = `${count} Question${count === 1 ? '' : 's'} / Project${count === 1 ? '' : 's'}`;
    }

    updateTotalProjectCount();
}

function addQuestionToArena(arenaName) {
    const entriesContainer = document.getElementById(`entriesContainer_${arenaName}`);
    if (!entriesContainer) return;

    const projectId = `proj_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    projectFilesMap.set(projectId, []);

    const card = document.createElement("div");
    card.className = "project-card";
    card.dataset.projectId = projectId;
    card.dataset.arena = arenaName;

    card.innerHTML = `
        <input type="hidden" class="project-arena-val" name="projectArena[]" value="${escapeHtml(arenaName)}">
        <div class="project-card-header">
            <div class="project-header-title">
                <span class="project-badge">${escapeHtml(arenaName)} · Question <span class="entry-num">#1</span></span>
                <span class="project-arena-badge-display">Track: ${escapeHtml(arenaName)}</span>
            </div>
            <button type="button" class="remove-project-btn" title="Remove this question entry" style="display:inline-flex; align-items:center; gap:5px;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                <span>Remove Question</span>
            </button>
        </div>

        <div class="project-fields-grid">
            <label class="wide">
                <span>Project / Problem Title<span class="field-required-star">*</span></span>
                <input type="text" class="project-title-input" placeholder="e.g. Autonomous Solar Navigation Rover" maxlength="200" aria-label="Project Title" required>
                <small class="field-hint">A clear, distinctive name for this project or challenge solution under ${escapeHtml(arenaName)}.</small>
            </label>

            <label class="wide">
                <span>Problem Statement / Challenge Question<span class="field-required-star">*</span></span>
                <textarea class="project-problem-input" placeholder="What specific problem, real-world limitation, or engineering constraint does this project address?" maxlength="2000" aria-label="Problem Statement for this project" required></textarea>
                <small class="field-hint">Clearly define the problem context, challenge questions, and technical constraints.</small>
            </label>

            <label class="wide">
                <span>Proposed Solution &amp; Architecture<span class="field-required-star">*</span></span>
                <textarea class="project-solution-input" placeholder="Explain your methodology, system architecture, tech stack, and implementation design..." maxlength="4000" aria-label="Proposed Solution and Architecture for this project" required></textarea>
                <small class="field-hint">Describe how your prototype operates and what technologies are utilized.</small>
            </label>

            <label class="wide">
                <span>GitHub Repository URL<span class="field-required-star">*</span></span>
                <div class="tv-gh-input-wrap">
                    <input type="url" class="project-github-input" placeholder="https://github.com/organization-or-user/project-repository" autocomplete="off" spellcheck="false" aria-label="GitHub Repository URL for this project" required>
                    <div class="tv-gh-status-indicator"></div>
                </div>
                <small class="field-hint">Direct link to your project repository (e.g. <code>https://github.com/owner/repository</code>). Root homepages or user profile links are rejected.</small>
            </label>

            <div class="wide">
                <label>
                    <span>Evidence / Architecture Images<span class="field-required-star">*</span></span>
                </label>
                <div class="tv-upload-dropzone">
                    <div class="tv-upload-icon-wrap">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                    </div>
                    <div class="tv-upload-title">Drag &amp; drop evidence images here, or browse</div>
                    <div class="tv-upload-meta">PNG, JPG, or WEBP up to 5 MB per file. Upload architecture diagrams, circuit schematics, UI screens, or prototype photos.</div>
                    <input type="file" class="project-evidence-input" accept="image/png,image/jpeg,image/webp" multiple aria-label="Upload evidence or architecture images for this project" style="display:none;">
                </div>
                <div class="project-evidence-names wide" aria-live="polite" style="margin-top:8px;">
                    <span style="color:var(--color-text-muted); font-size:12px;">No images uploaded yet. Upload at least one architecture diagram or evidence photo.</span>
                </div>
            </div>
        </div>
    `;

    // Event: GitHub URL validation on blur & input
    const ghInput = card.querySelector(".project-github-input");
    const ghIndicator = card.querySelector(".tv-gh-status-indicator");

    function validateGhInline() {
        const val = ghInput.value.trim();
        if (val.length === 0) {
            ghIndicator.className = "tv-gh-status-indicator";
            ghIndicator.innerHTML = "";
            ghInput.setCustomValidity("");
            return;
        }

        const check = validateGitHubRepoUrl(val);
        if (check.valid) {
            ghIndicator.className = "tv-gh-status-indicator valid";
            ghIndicator.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span>Valid</span>
            `;
            ghInput.setCustomValidity("");
            ghInput.classList.remove("is-invalid");
        } else {
            ghIndicator.className = "tv-gh-status-indicator invalid";
            ghIndicator.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <span>Invalid</span>
            `;
            ghInput.setCustomValidity(check.message);
        }
    }

    ghInput.addEventListener("blur", validateGhInline);
    ghInput.addEventListener("input", () => {
        ghInput.setCustomValidity("");
        if (ghIndicator.classList.contains("invalid")) {
            ghIndicator.className = "tv-gh-status-indicator";
            ghIndicator.innerHTML = "";
        }
    });

    // Dropzone Click and File Selection
    const dropzone = card.querySelector(".tv-upload-dropzone");
    const fileInput = card.querySelector(".project-evidence-input");

    dropzone.addEventListener("click", () => {
        fileInput.click();
    });

    dropzone.addEventListener("dragover", e => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", e => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer && e.dataTransfer.files) {
            handleFilesSelected(e.dataTransfer.files);
        }
    });

    function handleFilesSelected(newlySelected) {
        const existing = projectFilesMap.get(projectId) || [];
        const merged = [...existing];

        for (const file of newlySelected) {
            const duplicate = merged.some(oldFile =>
                oldFile.name === file.name &&
                oldFile.size === file.size &&
                oldFile.lastModified === file.lastModified
            );
            if (!duplicate) {
                merged.push(file);
            }
        }

        const newFiles = [...newlySelected].filter(file =>
            !existing.some(oldFile =>
                oldFile.name === file.name &&
                oldFile.size === file.size &&
                oldFile.lastModified === file.lastModified
            )
        );

        const error = validateFiles(newFiles);
        if (error) {
            showStepError(error);
            fileInput.value = "";
            updateProjectFileDisplay(card, projectId);
            return;
        }

        projectFilesMap.set(projectId, merged);
        fileInput.value = "";
        updateProjectFileDisplay(card, projectId);
        hideStepError();
    }

    fileInput.addEventListener("change", () => {
        if (fileInput.files) {
            handleFilesSelected(fileInput.files);
        }
    });

    // Remove single question entry from this arena
    const removeBtn = card.querySelector(".remove-project-btn");
    removeBtn.addEventListener("click", () => {
        const parentArenaSection = card.closest(".tv-arena-form-section");
        const allCardsInArena = entriesContainer.querySelectorAll(".project-card");
        if (allCardsInArena.length > 1) {
            projectFilesMap.delete(projectId);
            card.remove();
            if (parentArenaSection) {
                updateArenaSectionEntryNumbers(parentArenaSection);
            }
        }
    });

    entriesContainer.appendChild(card);

    const parentSection = card.closest(".tv-arena-form-section");
    if (parentSection) {
        updateArenaSectionEntryNumbers(parentSection);
    }
}

function createArenaSection(arenaName) {
    if (!projectsContainer) return null;

    // Remove empty notice if present
    const emptyNotice = projectsContainer.querySelector(".empty-arenas-notice");
    if (emptyNotice) {
        emptyNotice.remove();
    }

    const section = document.createElement("div");
    section.className = "tv-arena-form-section";
    section.id = `arenaSection_${arenaName}`;
    section.dataset.arena = arenaName;

    const iconSvg = arenaIcons[arenaName] || `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>`;
    const descText = arenaDescriptions[arenaName] || `${arenaName} Track`;

    section.innerHTML = `
        <div class="tv-arena-section-header">
            <div class="tv-arena-section-info">
                <div class="tv-arena-section-icon" aria-hidden="true">
                    ${iconSvg}
                </div>
                <div>
                    <h3 class="tv-arena-section-title">
                        <span>${escapeHtml(arenaName)} Arena</span>
                        <span class="project-arena-badge-display">Track: ${escapeHtml(arenaName)}</span>
                    </h3>
                    <p class="tv-arena-section-desc">${escapeHtml(descText)}</p>
                </div>
            </div>
            <span class="tv-arena-questions-count-badge arena-q-count">1 Question / Project</span>
        </div>

        <div class="arena-entries-container" id="entriesContainer_${arenaName}"></div>

        <div class="arena-section-actions">
            <button type="button" class="add-arena-question-btn" data-arena="${escapeHtml(arenaName)}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                <span>Add Another Question / Project for ${escapeHtml(arenaName)}</span>
            </button>
            <span class="muted" style="font-size:12px;">Add multiple challenge questions or problem solutions for this arena.</span>
        </div>
    `;

    // Bind Add Another Question button
    const addQBtn = section.querySelector(".add-arena-question-btn");
    addQBtn.addEventListener("click", () => {
        addQuestionToArena(arenaName);
    });

    projectsContainer.appendChild(section);

    // Add first question entry for this arena
    addQuestionToArena(arenaName);

    return section;
}

function handleArenaCheckboxChange(event) {
    const checkbox = event.target;
    const arenaName = checkbox.value;
    const isChecked = checkbox.checked;

    if (isChecked) {
        // User selected an arena: create a fresh detail section for this arena
        // Previous arena sections remain completely unchanged!
        let section = document.getElementById(`arenaSection_${arenaName}`);
        if (!section) {
            section = createArenaSection(arenaName);
            if (section && typeof section.scrollIntoView === "function") {
                section.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
        }
    } else {
        // User unchecked this arena: remove its section and clean up its files
        const section = document.getElementById(`arenaSection_${arenaName}`);
        if (section) {
            section.querySelectorAll(".project-card").forEach(c => {
                const pId = c.dataset.projectId;
                if (pId) {
                    projectFilesMap.delete(pId);
                }
            });
            section.remove();
        }

        // If no arena sections remain, show empty notice
        const remainingSections = projectsContainer ? projectsContainer.querySelectorAll(".tv-arena-form-section") : [];
        if (remainingSections.length === 0) {
            renderEmptyArenasNotice();
        }
    }

    updateTotalProjectCount();
}

function syncInitialArenasAndProjects() {
    const selected = getSelectedArenas();
    if (selected.length > 0) {
        selected.forEach(arena => {
            if (!document.getElementById(`arenaSection_${arena}`)) {
                createArenaSection(arena);
            }
        });
    } else {
        renderEmptyArenasNotice();
    }
}

if (addProjectBtn) {
    addProjectBtn.addEventListener("click", () => {
        const selected = getSelectedArenas();
        if (selected.length === 0) {
            showStepError("Please select at least one challenge arena track above first.");
            document.getElementById("arenas-title")?.scrollIntoView({ behavior: "smooth", block: "center" });
            return;
        }

        // Add another question to the last selected arena
        const lastArena = selected[selected.length - 1];
        addQuestionToArena(lastArena);

        const lastSection = document.getElementById(`arenaSection_${lastArena}`);
        if (lastSection) {
            const cards = lastSection.querySelectorAll(".project-card");
            const newCard = cards[cards.length - 1];
            if (newCard) {
                newCard.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
    });
}

arenaCheckboxes.forEach(checkbox => {
    checkbox.addEventListener("change", handleArenaCheckboxChange);
});

// Initialize projects matching any checked arenas, or create empty prompt
syncInitialArenasAndProjects();

// ==========================================================================
// STEP 5: LIVE REVIEW SUMMARY GENERATOR
// ==========================================================================

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderReviewSummary() {
    if (!reviewSummaryContainer) return;

    // Gather Step 1 data
    const teamName = form.teamName ? form.teamName.value.trim() : "—";
    const teamNumber = form.teamNumber ? form.teamNumber.value.trim() : "Not assigned";
    const leaderName = form.leaderName ? form.leaderName.value.trim() : "—";
    const leaderEmail = form.leaderEmail ? form.leaderEmail.value.trim() : "—";
    const leaderPhone = form.leaderPhone ? form.leaderPhone.value.trim() : "—";

    // Gather Step 2 data
    const collegeName = form.collegeName ? form.collegeName.value.trim() : "—";
    const collegeCity = form.collegeCity ? form.collegeCity.value.trim() : "—";
    const collegeDept = form.collegeDept ? form.collegeDept.value.trim() : "—";
    const leaderSection = form.leaderSection ? form.leaderSection.value.trim() : "—";
    const leaderYear = form.leaderYear ? form.leaderYear.value.trim() : "—";

    // Gather Step 3 data (Members)
    const memberRows = membersBody ? membersBody.querySelectorAll("tr") : [];
    const membersList = [];
    memberRows.forEach(row => {
        const name = row.querySelector('input[name="memberName[]"]')?.value.trim() || "";
        const email = row.querySelector('input[name="memberEmail[]"]')?.value.trim() || "";
        const section = row.querySelector('input[name="memberSection[]"]')?.value.trim() || "";
        const year = row.querySelector('select[name="memberYear[]"]')?.value.trim() || "";
        if (name) {
            membersList.push({ name, email, section, year });
        }
    });

    // Gather Step 4 data (Arenas & Projects)
    const selectedArenas = getSelectedArenas();
    const arenaSections = projectsContainer ? [...projectsContainer.querySelectorAll(".tv-arena-form-section")] : [];
    const projectsList = [];

    arenaSections.forEach(section => {
        const arena = section.dataset.arena;
        const cards = section.querySelectorAll(".project-card");
        cards.forEach((card, idx) => {
            const pId = card.dataset.projectId;
            const title = card.querySelector(".project-title-input")?.value.trim() || "";
            const problem = card.querySelector(".project-problem-input")?.value.trim() || "";
            const solution = card.querySelector(".project-solution-input")?.value.trim() || "";
            const github = card.querySelector(".project-github-input")?.value.trim() || "";
            const files = projectFilesMap.get(pId) || [];

            projectsList.push({
                arena,
                qNum: idx + 1,
                title,
                problem,
                solution,
                github,
                filesCount: files.length
            });
        });
    });

    // Build Roster Table HTML
    let rosterHtml = "";
    if (membersList.length === 0) {
        rosterHtml = '<p style="color:var(--color-error); font-size:12.5px;">No members added.</p>';
    } else {
        rosterHtml = `
            <table style="width:100%; border-collapse:collapse; font-size:12px; margin-top:6px;">
                <thead>
                    <tr style="background:var(--color-bg-subtle);">
                        <th style="padding:6px 10px; border:1px solid var(--color-border-subtle); width:35px;">#</th>
                        <th style="padding:6px 10px; border:1px solid var(--color-border-subtle);">Name</th>
                        <th style="padding:6px 10px; border:1px solid var(--color-border-subtle);">Email</th>
                        <th style="padding:6px 10px; border:1px solid var(--color-border-subtle); width:80px;">Section</th>
                        <th style="padding:6px 10px; border:1px solid var(--color-border-subtle); width:80px;">Year</th>
                    </tr>
                </thead>
                <tbody>
                    ${membersList.map((m, i) => `
                        <tr>
                            <td style="padding:6px 10px; border:1px solid var(--color-border-subtle); text-align:center; font-family:var(--font-mono); font-weight:700;">${i + 1}</td>
                            <td style="padding:6px 10px; border:1px solid var(--color-border-subtle); font-weight:600;">${escapeHtml(m.name)}</td>
                            <td style="padding:6px 10px; border:1px solid var(--color-border-subtle); color:var(--color-text-muted);">${escapeHtml(m.email)}</td>
                            <td style="padding:6px 10px; border:1px solid var(--color-border-subtle);">${escapeHtml(m.section)}</td>
                            <td style="padding:6px 10px; border:1px solid var(--color-border-subtle);">${escapeHtml(m.year ? `${m.year} Year` : '—')}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    // Build Projects HTML
    let projectsHtml = "";
    if (projectsList.length === 0) {
        projectsHtml = '<p style="color:var(--color-error); font-size:12.5px;">No projects submitted.</p>';
    } else {
        projectsHtml = projectsList.map(p => `
            <div style="background:var(--color-bg-subtle); border:1px solid var(--color-border-subtle); border-left:3.5px solid var(--color-crimson); border-radius:var(--radius-sm); padding:12px 14px; margin-bottom:10px;">
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-family:var(--font-heading); font-weight:800; font-size:12px; background:var(--color-bg-surface); padding:2px 8px; border-radius:4px; border:1px solid var(--color-border-subtle);">${escapeHtml(p.arena)} · Question #${p.qNum}</span>
                        <strong style="font-size:13.5px; color:var(--color-text-primary);">${escapeHtml(p.title || 'Untitled Project')}</strong>
                    </div>
                    <span class="tv-review-chip track-chip">Track: ${escapeHtml(p.arena || 'Unassigned')}</span>
                </div>
                <div style="font-size:12px; color:var(--color-text-body); margin-bottom:6px; line-height:1.4;">
                    <strong>Problem / Challenge:</strong> ${escapeHtml(p.problem ? (p.problem.length > 140 ? p.problem.slice(0, 140) + '...' : p.problem) : '—')}
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:11.5px; padding-top:6px; border-top:1px dashed var(--color-border-subtle);">
                    <div style="display:flex; align-items:center; gap:5px; font-family:var(--font-mono); color:var(--color-crimson);">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
                        <span>${escapeHtml(p.github || 'No link')}</span>
                    </div>
                    <span style="font-weight:600; color:var(--color-text-muted);">${p.filesCount} evidence image${p.filesCount === 1 ? '' : 's'} attached</span>
                </div>
            </div>
        `).join("");
    }

    // Assemble Review Summary Component
    reviewSummaryContainer.innerHTML = `
        <!-- Card 1: Team & Leader -->
        <div class="tv-review-card">
            <div class="tv-review-card-header">
                <span class="tv-review-card-title">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                    <span>01. Team &amp; Leader Identity</span>
                </span>
                <button type="button" class="tv-review-edit-btn" data-jump-step="1">
                    <span>Edit ✎</span>
                </button>
            </div>
            <div class="tv-review-card-body">
                <div class="tv-review-grid">
                    <div class="tv-review-item">
                        <span class="tv-review-label">Team Name</span>
                        <span class="tv-review-val">${escapeHtml(teamName)}</span>
                    </div>
                    <div class="tv-review-item">
                        <span class="tv-review-label">Assigned Code</span>
                        <span class="tv-review-val">${escapeHtml(teamNumber)}</span>
                    </div>
                    <div class="tv-review-item">
                        <span class="tv-review-label">Leader Full Name</span>
                        <span class="tv-review-val">${escapeHtml(leaderName)}</span>
                    </div>
                    <div class="tv-review-item">
                        <span class="tv-review-label">Leader Email Address</span>
                        <span class="tv-review-val">${escapeHtml(leaderEmail)}</span>
                    </div>
                    <div class="tv-review-item full-width">
                        <span class="tv-review-label">Leader Phone Number</span>
                        <span class="tv-review-val">${escapeHtml(leaderPhone)}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Card 2: Academic Affiliation -->
        <div class="tv-review-card">
            <div class="tv-review-card-header">
                <span class="tv-review-card-title">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>
                    <span>02. Institutional Affiliation &amp; Academic Credentials</span>
                </span>
                <button type="button" class="tv-review-edit-btn" data-jump-step="2">
                    <span>Edit ✎</span>
                </button>
            </div>
            <div class="tv-review-card-body">
                <div class="tv-review-grid">
                    <div class="tv-review-item">
                        <span class="tv-review-label">College / University</span>
                        <span class="tv-review-val">${escapeHtml(collegeName)}</span>
                    </div>
                    <div class="tv-review-item">
                        <span class="tv-review-label">Campus Location</span>
                        <span class="tv-review-val">${escapeHtml(collegeCity)}</span>
                    </div>
                    <div class="tv-review-item">
                        <span class="tv-review-label">Department / Branch</span>
                        <span class="tv-review-val">${escapeHtml(collegeDept || 'General')}</span>
                    </div>
                    <div class="tv-review-item">
                        <span class="tv-review-label">Academic Section</span>
                        <span class="tv-review-val">${escapeHtml(leaderSection)}</span>
                    </div>
                    <div class="tv-review-item full-width">
                        <span class="tv-review-label">Leader Year of Study</span>
                        <span class="tv-review-val">${escapeHtml(leaderYear ? `${leaderYear} Year` : '—')}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Card 3: Members Roster -->
        <div class="tv-review-card">
            <div class="tv-review-card-header">
                <span class="tv-review-card-title">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><line x1="19" y1="8" x2="19" y2="14"></line><line x1="22" y1="11" x2="16" y2="11"></line></svg>
                    <span>03. Team Roster (${membersList.length} Member${membersList.length === 1 ? '' : 's'})</span>
                </span>
                <button type="button" class="tv-review-edit-btn" data-jump-step="3">
                    <span>Edit ✎</span>
                </button>
            </div>
            <div class="tv-review-card-body" style="padding:10px 14px;">
                ${rosterHtml}
            </div>
        </div>

        <!-- Card 4: Arenas & Projects -->
        <div class="tv-review-card">
            <div class="tv-review-card-header">
                <span class="tv-review-card-title">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
                    <span>04. Arenas (${selectedArenas.length}) &amp; Projects (${projectsList.length})</span>
                </span>
                <button type="button" class="tv-review-edit-btn" data-jump-step="4">
                    <span>Edit ✎</span>
                </button>
            </div>
            <div class="tv-review-card-body">
                <div style="margin-bottom:14px;">
                    <span class="tv-review-label">Selected Arenas:</span>
                    <div class="tv-review-chips">
                        ${selectedArenas.length > 0 ? selectedArenas.map(a => `<span class="tv-review-chip"><strong>${escapeHtml(a)}</strong> (${escapeHtml(arenaDescriptions[a] || a)})</span>`).join("") : '<span style="color:var(--color-error); font-size:12px;">No arenas selected</span>'}
                    </div>
                </div>

                <span class="tv-review-label">Project Proposals:</span>
                <div style="margin-top:6px;">
                    ${projectsHtml}
                </div>
            </div>
        </div>
    `;

    // Bind Jump Step Edit Buttons
    reviewSummaryContainer.querySelectorAll(".tv-review-edit-btn[data-jump-step]").forEach(btn => {
        btn.addEventListener("click", () => {
            const step = parseInt(btn.dataset.jumpStep, 10);
            goToStep(step);
        });
    });
}

// ==========================================================================
// FORM SUBMISSION ENGINE (CROSS-STEP VALIDATION & MULTIPART DISPATCH)
// ==========================================================================

if (form) {
    form.addEventListener("submit", async event => {
        event.preventDefault();
        hideStepError();

        // 1. Validate all 4 stages sequentially
        for (let s = 1; s <= 4; s++) {
            if (!validateStep(s)) {
                goToStep(s);
                return;
            }
        }

        // 2. Validate Declaration Checkbox
        const confirmBox = document.getElementById("confirmAccuracyCheckbox");
        if (confirmBox && !confirmBox.checked) {
            showStepError("Please confirm the Declaration of Originality and Academic Integrity checkbox.");
            confirmBox.focus();
            return;
        }

        // 3. Prepare FormData
        const projectCards = [...(projectsContainer ? projectsContainer.querySelectorAll(".project-card") : [])];
        const submitButton = document.getElementById("submitFormBtn") || form.querySelector('button[type="submit"]');
        const submitBtnText = document.getElementById("submitBtnText");

        const formData = new FormData(form);

        // Remove raw/unaligned project keys from the native FormData
        formData.delete("projectArena[]");
        formData.delete("projectTitle[]");
        formData.delete("projectProblem[]");
        formData.delete("projectSolution[]");
        formData.delete("projectGithub[]");

        // Append aligned, ordered project fields and attached image files
        projectCards.forEach((card, index) => {
            const pId = card.dataset.projectId;
            const arenaVal = card.dataset.arena || card.closest(".tv-arena-form-section")?.dataset.arena || card.querySelector(".project-arena-val")?.value.trim() || "";
            const titleVal = card.querySelector(".project-title-input")?.value.trim() || "";
            const problemVal = card.querySelector(".project-problem-input")?.value.trim() || "";
            const solutionVal = card.querySelector(".project-solution-input")?.value.trim() || "";
            const ghVal = card.querySelector(".project-github-input")?.value.trim() || "";
            const files = projectFilesMap.get(pId) || [];

            formData.append("projectArena[]", arenaVal);
            formData.append("projectTitle[]", titleVal);
            formData.append("projectProblem[]", problemVal);
            formData.append("projectSolution[]", solutionVal);
            formData.append("projectGithub[]", ghVal);

            files.forEach(file => {
                formData.append(`projectEvidence_${index}[]`, file, file.name);
            });
        });

        // 4. Set Loading State (Duplicate Protection)
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add("is-submitting");
        }
        if (submitBtnText) {
            submitBtnText.textContent = "Submitting to TechVerse 2026...";
        }
        if (message) {
            message.textContent = "Validating and saving your registration. Please wait...";
        }

        try {
            const response = await fetch("/register", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "Registration failed. Please check the entered data.");
            }

            // Success feedback
            if (message) {
                message.textContent = `${result.message} Registration ID: ${result.registration_id}`;
            }

            // Launch Success Modal
            const successModal = document.getElementById("registrationSuccessModal");
            if (successModal) {
                const displayRegId = document.getElementById("displayRegId");
                const viewIdCardBtn = document.getElementById("viewIdCardBtn");
                if (displayRegId) {
                    displayRegId.textContent = result.registration_id;
                }
                if (viewIdCardBtn) {
                    viewIdCardBtn.href = `/team/${encodeURIComponent(result.registration_id)}/card`;
                }
                successModal.classList.remove("hidden");
            }

            // Reset form & state
            form.reset();
            if (membersBody) {
                membersBody.replaceChildren();
            }
            addMember();
            projectFilesMap.clear();
            renderEmptyArenasNotice();
            furthestStepReached = 1;
            goToStep(1);

        } catch (error) {
            showStepError(error.message || "Could not connect to the registration server. Please try again.");
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.classList.remove("is-submitting");
            }
            if (submitBtnText) {
                submitBtnText.textContent = "Submit Team Registration";
            }
        }
    });
}

// ==========================================================================
// SUCCESS MODAL & ARENA SHOWCASE EVENT HANDLERS
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    // Copy Registration ID Button
    const copyBtn = document.getElementById("copyRegIdBtn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            const regId = document.getElementById("displayRegId")?.textContent || "";
            if (regId && navigator.clipboard) {
                navigator.clipboard.writeText(regId).then(() => {
                    copyBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; vertical-align: -2px;">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span class="copy-text">Copied!</span>
                    `;
                    setTimeout(() => {
                        copyBtn.innerHTML = `
                            <svg class="copy-icon-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; vertical-align: -2px;">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            <span class="copy-text">Copy ID</span>
                        `;
                    }, 2000);
                });
            }
        });
    }

    // Close Success Modal
    const closeBtn = document.getElementById("closeSuccessModal");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            document.getElementById("registrationSuccessModal")?.classList.add("hidden");
        });
    }

    // Homepage Arena Showcase Quick-Selection Actions
    document.querySelectorAll(".tv-arena-card-action[data-arena]").forEach(btn => {
        btn.addEventListener("click", () => {
            const arenaName = btn.dataset.arena;
            if (arenaName) {
                const checkbox = document.querySelector(`input[name="arenas"][value="${arenaName}"]`);
                if (checkbox && !checkbox.checked) {
                    checkbox.checked = true;
                    checkbox.dispatchEvent(new Event("change"));
                }
            }
        });
    });
});
