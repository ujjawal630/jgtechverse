
const membersBody = document.getElementById("membersBody");
const addMemberButton = document.getElementById("addMember");
const arenaDetails = document.getElementById("arenaDetails");
const arenaCheckboxes = document.querySelectorAll('input[name="arenas"]');
const form = document.getElementById("teamForm");
const message = document.getElementById("message");

const arenaDescriptions = {
    Buddhi: "AI Model Building",
    Fiontar: "Startup & Innovation",
    Talos: "Robotic Arena",
    Pegasus: "Drone Fest",
    Promethia: "Coding Challenge",
    Mercatus: "Trading & Financial Analytics"
};

const MAX_ADDITIONAL_MEMBERS = 4; // Maximum 4 additional members + 1 leader = 5 people total
const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];

// Store selected files separately for each arena.
const selectedFilesByInput = new WeakMap();

function updateMemberNumbers() {
    const rows = membersBody.querySelectorAll("tr");

    rows.forEach((row, index) => {
        row.querySelector(".row-number").textContent = index + 1;
        row.querySelector(".remove-btn").disabled = rows.length === 1;
    });

    const isMax = rows.length >= MAX_ADDITIONAL_MEMBERS;
    addMemberButton.disabled = isMax;
    if (isMax) {
        addMemberButton.title = "Maximum 5 total team members reached (1 leader + 4 members).";
    } else {
        addMemberButton.title = "Add team member";
    }
}

function addMember() {
    if (membersBody.querySelectorAll("tr").length >= MAX_ADDITIONAL_MEMBERS) {
        return;
    }

    const row = document.createElement("tr");

    row.innerHTML = `
        <td class="row-number"></td>
        <td>
            <input type="text" name="memberName[]"
                   placeholder="Full name" required>
        </td>
        <td>
            <input type="email" name="memberEmail[]"
                   placeholder="Email address" required>
        </td>
        <td>
            <select name="memberSection[]" required>
                <option value="">Select</option>
                <option>A</option>
                <option>B</option>
                <option>C</option>
                <option>D</option>
                <option>E</option>
                <option>F</option>
                <option>Other</option>
            </select>
        </td>
        <td>
            <select name="memberYear[]" required>
                <option value="">Select</option>
                <option value="1">1st Year</option>
                <option value="2">2nd Year</option>
                <option value="3">3rd Year</option>
                <option value="4">4th Year</option>
            </select>
        </td>
        <td>
            <button type="button" class="remove-btn"
                    aria-label="Remove member">✕</button>
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

addMemberButton.addEventListener("click", addMember);
addMember();

function validateFiles(files) {
    for (const file of files) {
        if (!ALLOWED_TYPES.includes(file.type)) {
            return `${file.name}: Please select PNG, JPG or WEBP images only.`;
        }

        if (file.size > MAX_FILE_SIZE) {
            return `${file.name} is larger than 5 MB.`;
        }
    }

    return "";
}

function updateFileNames(input, output) {
    const files = selectedFilesByInput.get(input) || [];

    if (files.length === 0) {
        output.textContent = "No files selected.";
        return;
    }

    output.textContent =
        `${files.length} file(s) selected: ` +
        files.map(file => file.name).join(", ");
}

function createArenaDetails() {
    const selectedArenas = [...arenaCheckboxes]
        .filter(checkbox => checkbox.checked)
        .map(checkbox => checkbox.value);

    // Keep existing arena sections and their selected files.
    const existingSections = new Map(
        [...arenaDetails.querySelectorAll(".arena-detail")]
            .map(section => [
                section.dataset.arena,
                section
            ])
    );

    arenaDetails.replaceChildren();

    selectedArenas.forEach(arena => {
        let section = existingSections.get(arena);

        if (section) {
            arenaDetails.appendChild(section);
            return;
        }

        section = document.createElement("section");
        section.className = "arena-detail";
        section.dataset.arena = arena;

        section.innerHTML = `
            <h3>
                ${arena}
                <span>— ${arenaDescriptions[arena]}</span>
            </h3>

            <div class="arena-fields">
                <label class="wide">
                    Problem Statement *
                    <textarea name="problem_${arena}"
                        placeholder="What problem are you solving?"
                        maxlength="2000" required></textarea>
                </label>

                <label class="wide">
                    Proposed Solution *
                    <textarea name="solution_${arena}"
                        placeholder="Explain your proposed solution..."
                        maxlength="4000" required></textarea>
                </label>

                <label class="wide">
                    GitHub Repository Link (optional)
                    <input type="url" name="github_${arena}"
                        placeholder="https://github.com/your-team/project">
                </label>

                <label class="wide">
                    Evidence for ${arena} *
                    <input type="file"
                        name="evidence_${arena}[]"
                        accept="image/png,image/jpeg,image/webp"
                        multiple>
                    <small>
                        Select multiple images. Maximum 5 MB per image.
                    </small>
                </label>

                <p class="file-names wide" aria-live="polite">
                    No files selected.
                </p>
            </div>
        `;

        const input = section.querySelector('input[type="file"]');
        const output = section.querySelector(".file-names");

        selectedFilesByInput.set(input, []);

        input.addEventListener("change", () => {
            const newlySelected = [...input.files];
            const existing = selectedFilesByInput.get(input) || [];

            // Merge selections while avoiding accidental duplicates.
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

            // Validate only the new selection first. Keep existing valid files.
            const newFiles = newlySelected.filter(file =>
                !existing.some(oldFile =>
                    oldFile.name === file.name &&
                    oldFile.size === file.size &&
                    oldFile.lastModified === file.lastModified
                )
            );

            const error = validateFiles(newFiles);

            if (error) {
                message.textContent = error;
                input.value = "";
                updateFileNames(input, output);
                return;
            }

            selectedFilesByInput.set(input, merged);

            // Clear the native input so selecting the same file again
            // can trigger change; the File objects remain stored above.
            input.value = "";

            updateFileNames(input, output);
            message.textContent = "";
        });

        arenaDetails.appendChild(section);
    });
}

arenaCheckboxes.forEach(checkbox => {
    checkbox.addEventListener("change", createArenaDetails);
});

form.addEventListener("submit", async event => {
    event.preventDefault();
    message.textContent = "";

    // Validate normal form fields without requiring the native file input.
    if (!form.checkValidity()) {
        form.reportValidity();
        message.textContent =
            "Please fill in all required fields correctly.";
        return;
    }

    if (![...arenaCheckboxes].some(checkbox => checkbox.checked)) {
        message.textContent = "Please select at least one arena.";

        document.getElementById("arenas-title")?.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        return;
    }

    const fileInputs = [
        ...arenaDetails.querySelectorAll('input[type="file"]')
    ];

    for (const input of fileInputs) {
        const files = selectedFilesByInput.get(input) || [];

        if (files.length === 0) {
            message.textContent =
                "Please select at least one image for each arena.";
            input.focus();
            return;
        }

        const error = validateFiles(files);

        if (error) {
            message.textContent = error;
            input.focus();
            return;
        }
    }

    const submitButton = form.querySelector(
        'button[type="submit"], input[type="submit"]'
    );

    // Include normal form fields and append all stored image files.
    const formData = new FormData(form);

    for (const input of fileInputs) {
        formData.delete(input.name);

        const files = selectedFilesByInput.get(input) || [];

        for (const file of files) {
            formData.append(input.name, file, file.name);
        }
    }

    if (submitButton) {
        submitButton.disabled = true;
    }

    message.textContent = "Submitting registration...";

    try {
        const response = await fetch("/register", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message || "Registration failed. Please try again."
            );
        }

        message.textContent =
            `${result.message} Registration ID: ${result.registration_id}`;

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

        form.reset();
        membersBody.replaceChildren();
        addMember();
        arenaDetails.replaceChildren();

    } catch (error) {
        message.textContent =
            error.message || "Could not connect to the server.";
    } finally {
        if (submitButton) {
            submitButton.disabled = false;
        }
    }
});

// Success Modal Event Handlers
document.addEventListener("DOMContentLoaded", () => {
    const copyBtn = document.getElementById("copyRegIdBtn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            const regId = document.getElementById("displayRegId")?.textContent || "";
            if (regId && navigator.clipboard) {
                navigator.clipboard.writeText(regId).then(() => {
                    copyBtn.textContent = "✅ Copied!";
                    setTimeout(() => {
                        copyBtn.textContent = "📋 Copy ID";
                    }, 2000);
                });
            }
        });
    }

    const closeBtn = document.getElementById("closeSuccessModal");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            document.getElementById("registrationSuccessModal")?.classList.add("hidden");
        });
    }
});

