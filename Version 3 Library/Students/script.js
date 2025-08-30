document.addEventListener("DOMContentLoaded", () => {
    // --- DATE & CLOCK LOGIC ---
    const clockElement = document.getElementById("digital-clock");
    const dateElement = document.getElementById("digital-date");

    function updateClock() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const dateString = now.toLocaleDateString('en-US', dateOptions);

        if (clockElement) clockElement.textContent = `${hours}:${minutes}:${seconds}`;
        if (dateElement) dateElement.textContent = dateString;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- LOGIN OVERLAY SYSTEM ---
    // (This part of the code remains unchanged)
    const loginOverlay = document.getElementById("login-overlay");
    const loginId = document.getElementById("login-id");
    const loginPass = document.getElementById("login-pass");
    const loginBtn = document.getElementById("login-submit");
    const loginError = document.getElementById("login-error");
    let failedAttempts = 0;
    let lockoutUntil = null;
    const sessionData = JSON.parse(localStorage.getItem("studentSession"));

    if (sessionData && new Date(sessionData.expiry) > new Date()) {
        loginOverlay.style.display = "none";
        initMainUI();
    } else {
        loginOverlay.style.display = "flex";
        loginBtn.addEventListener("click", () => {
            if (lockoutUntil && Date.now() < lockoutUntil) {
                const remaining = Math.ceil((lockoutUntil - Date.now()) / 1000);
                loginError.textContent = `Locked out. Try again in ${remaining} seconds.`;
                return;
            }
            const id = loginId.value.trim();
            const pass = loginPass.value.trim();
            if (!id || !pass) {
                loginError.textContent = "Enter ID and password.";
                return;
            }
            fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id, pass })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        failedAttempts = 0;
                        const expiry = new Date();
                        expiry.setHours(23, 59, 59, 999);
                        localStorage.setItem("studentSession", JSON.stringify({ id, expiry: expiry.toISOString() }));
                        loginOverlay.style.display = "none";
                        initMainUI();
                    } else {
                        failedAttempts++;
                        loginError.textContent = "Invalid credentials.";
                        if (failedAttempts >= 5) {
                            lockoutUntil = Date.now() + 15 * 60 * 1000; // 15-minute lockout
                            startLockoutCountdown();
                        }
                    }
                })
                .catch(err => {
                    loginError.textContent = "Login failed. Please check connection.";
                    console.error(err);
                });
        });
    }

    function startLockoutCountdown() {
        const timer = setInterval(() => {
            const remaining = Math.ceil((lockoutUntil - Date.now()) / 1000);
            if (remaining <= 0) {
                clearInterval(timer);
                loginError.textContent = "";
                failedAttempts = 0;
                lockoutUntil = null;
            } else {
                loginError.textContent = `Locked out. Try again in ${remaining} seconds.`;
            }
        }, 1000);
    }

    // --- LIVE STATS (NEW) ---
    function updateLiveStats() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                document.getElementById('entries-today').textContent = data.total_entries_today;
                document.getElementById('currently-inside').textContent = data.currently_inside;
                document.getElementById('peak-hour').textContent = data.peak_hour_today;
            })
            .catch(error => console.error('Error fetching live stats:', error));
    }

    // --- MAIN UI INITIALIZATION ---
    function initMainUI() {
        const logo = document.getElementById("logo");
        const loginPanel = document.getElementById("loginPanel");
        const roleSelection = document.getElementById("roleSelection");
        const roleOptions = document.querySelectorAll(".role-option");
        const enrollment = document.getElementById("enrollment");
        const enrollInput = document.getElementById("enrollInput");
        const submitBtn = document.getElementById("submitBtn");
        const enrollError = document.getElementById("enrollError");
        const enrollForm = document.getElementById("enrollForm");
        const hiddenRole = document.getElementById("hiddenRole");
        const hiddenEnroll = document.getElementById("hiddenEnroll");
        const clickPrompt = document.getElementById("click-prompt"); // New prompt message

        let step = 0; // 0: idle, 1: role, 2: enrollment
        let selectedRoleIndex = 0;

        function updateHighlight(options, selectedIndex) {
            options.forEach((opt, idx) => {
                opt.classList.toggle("selected", idx === selectedIndex);
            });
        }

        function showPanel(panelToShow) {
            [roleSelection, enrollment].forEach(panel => {
                panel.classList.toggle("hidden", panel !== panelToShow);
            });
        }

        function showLoginPanel() {
            if (step !== 0) return;
            clickPrompt.style.display = 'none'; // Hide prompt
            logo.style.transform = "scale(1.2)";
            setTimeout(() => {
                loginPanel.classList.add("visible");
                showPanel(roleSelection);
                step = 1;
            }, 400);
        }

        function hideLoginPanel() {
            loginPanel.classList.remove("visible");
            setTimeout(() => {
                logo.style.transform = "scale(1)";
                clickPrompt.style.display = 'block'; // Show prompt again
                enrollInput.value = "";
                enrollError.textContent = "";
                step = 0;
                selectedRoleIndex = 0;
                updateHighlight(roleOptions, selectedRoleIndex);
                showPanel(null);
            }, 500);
        }

        enrollInput.addEventListener("input", () => {
            const selectedRole = roleOptions[selectedRoleIndex].dataset.role;
            const maxLength = selectedRole === 'Student' ? 5 : 4;
            enrollInput.value = enrollInput.value.replace(/\D/g, "").slice(0, maxLength);
            enrollError.textContent = "";
        });

        submitBtn.addEventListener("click", () => {
            const selectedRole = roleOptions[selectedRoleIndex].dataset.role;
            const expectedLength = selectedRole === 'Student' ? 5 : 4;
            const value = enrollInput.value;

            if (value.length !== expectedLength) {
                enrollError.textContent = `Please enter exactly ${expectedLength} digits.`;
                return;
            }
            enrollError.textContent = "";

            const formData = new FormData();
            formData.append('registry_last_digits', value);
            formData.append('role', selectedRole);

            // This now directly submits the form instead of showing reasons
            fetch('/check-status', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // No matter if user is inside or outside, the action is the same: submit the main form.
                        // The backend /check route will handle both entry and exit.
                        hiddenEnroll.value = value;
                        hiddenRole.value = selectedRole;
                        enrollForm.submit();
                    } else {
                        enrollError.textContent = data.error || "Invalid user or role.";
                    }
                })
                .catch(error => {
                    enrollError.textContent = "System error. Please try again.";
                    console.error(error);
                });
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") { hideLoginPanel(); return; }
            if (step === 0 && e.key === "Enter") { showLoginPanel(); return; }
            if (!loginPanel.classList.contains('visible')) return;

            if (e.key === "Enter") {
                e.preventDefault();
                if (step === 1) { // Role selection
                    showPanel(enrollment);
                    enrollInput.focus();
                    step = 2;
                } else if (step === 2) { // Enrollment input
                    submitBtn.click();
                }
            }

            if (step === 1) { // Arrow keys for role
                if (e.key === "ArrowDown") selectedRoleIndex = (selectedRoleIndex + 1) % roleOptions.length;
                if (e.key === "ArrowUp") selectedRoleIndex = (selectedRoleIndex - 1 + roleOptions.length) % roleOptions.length;
                updateHighlight(roleOptions, selectedRoleIndex);
            }
        });

        logo.addEventListener("click", showLoginPanel);

        roleOptions.forEach((option, idx) => {
            option.addEventListener("click", () => {
                selectedRoleIndex = idx;
                updateHighlight(roleOptions, selectedRoleIndex);
                setTimeout(() => {
                    showPanel(enrollment);
                    enrollInput.focus();
                    step = 2;
                }, 200);
            });
        });

        const toast = document.getElementById("toast");
        if (toast) {
            const message = toast.getAttribute("data-message");
            const isError = toast.getAttribute("data-type") === "error";
            if (message) {
                toast.textContent = message;
                toast.style.backgroundColor = isError ? "#d9534f" : "#4169e1";
                toast.classList.add("show");
                setTimeout(() => toast.classList.remove("show"), 4000);
            }
        }

        // Initial and periodic fetch for live stats
        updateLiveStats();
        setInterval(updateLiveStats, 15000); // Update every 15 seconds
    }

    // This check ensures main UI logic only runs after successful login
    if (loginOverlay.style.display === 'none') {
        initMainUI();
    }
});
