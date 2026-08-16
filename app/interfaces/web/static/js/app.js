const isAuthenticated = document.body.dataset.authenticated === "1";
const socket = isAuthenticated ? io() : null;

function initThemeFromStorage() {
    try {
        const savedTheme = localStorage.getItem("edulink-theme");
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const theme = savedTheme || (prefersDark ? "dark" : "light");
        document.documentElement.setAttribute("data-theme", theme);
    } catch (error) {
        document.documentElement.setAttribute("data-theme", "light");
    }
}

initThemeFromStorage();

if (socket) {
    socket.on("connect", () => {
        console.log("Socket connected");
    });

    socket.on("notification", (payload) => {
        const list = document.getElementById("notifications-list");
        if (!list) return;

        const content = payload.content || "";
        const channelId = payload.channel_id;

        const item = document.createElement("li");
        item.className = "timeline-item";

        const dot = document.createElement("span");
        dot.className = "timeline-dot timeline-dot--message";
        dot.setAttribute("aria-hidden", "true");
        dot.innerHTML = '<i class="bi bi-chat-dots"></i>';

        const body = document.createElement("div");
        body.className = "timeline-body";
        const row = document.createElement("div");
        row.className = "d-flex justify-content-between align-items-baseline gap-2";

        const text = document.createElement("div");
        if (channelId) {
            const link = document.createElement("a");
            link.href = `/messages/channels/${channelId}`;
            link.textContent = content;
            text.appendChild(link);
        } else {
            text.appendChild(document.createTextNode(content));
        }
        row.appendChild(text);

        const time = document.createElement("span");
        time.className = "timeline-time";
        time.textContent = new Date().toLocaleTimeString("fr-FR", {
            hour: "2-digit",
            minute: "2-digit",
        });
        row.appendChild(time);

        body.appendChild(row);
        item.appendChild(dot);
        item.appendChild(body);

        list.prepend(item);
    });

    socket.on("channel_message", () => {
        if (window.location.pathname.includes("/messages/channels/")) {
            window.location.reload();
        }
    });
}

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, "+")
        .replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; i += 1) {
        outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
}

function initMemberPicker() {
    document.querySelectorAll("[data-member-picker]").forEach((picker) => {
        const boxes = Array.from(picker.querySelectorAll(".member-checkbox"));
        const groups = Array.from(picker.querySelectorAll("[data-role-group]"));
        const search = picker.querySelector("[data-member-search]");
        const countEl = picker.querySelector("[data-selected-count]");
        const summary = picker.querySelector("[data-selected-summary]");
        const empty = picker.querySelector("[data-search-empty]");
        const clearBtn = picker.querySelector("[data-clear-selection]");
        if (!countEl || !summary) {
            return;
        }

        const updateSummary = () => {
            const selected = boxes.filter((box) => box.checked);
            countEl.textContent = `${selected.length} selectionne${selected.length !== 1 ? "s" : ""}`;
            summary.replaceChildren();
            selected.forEach((box) => {
                const option = box.closest(".member-option");
                const nameEl = option ? option.querySelector(".member-option-name") : null;
                const name = nameEl ? nameEl.textContent.trim() : box.value;
                const chip = document.createElement("span");
                chip.className = "member-chip";
                chip.textContent = name;
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "member-chip-remove";
                remove.setAttribute("aria-label", `Retirer ${name}`);
                remove.innerHTML = "&times;";
                remove.addEventListener("click", () => {
                    box.checked = false;
                    updateSummary();
                });
                chip.appendChild(remove);
                summary.appendChild(chip);
            });
        };

        const applyFilter = () => {
            const term = (search ? search.value : "").trim().toLowerCase();
            let totalVisible = 0;
            groups.forEach((group) => {
                let visible = 0;
                group.querySelectorAll(".member-option").forEach((option) => {
                    const nameEl = option.querySelector(".member-option-name");
                    const name = nameEl ? nameEl.textContent.toLowerCase() : "";
                    const show = !term || name.includes(term);
                    option.hidden = !show;
                    if (show) {
                        visible += 1;
                    }
                });
                group.hidden = visible === 0;
                totalVisible += visible;
            });
            if (empty) {
                empty.hidden = totalVisible !== 0;
            }
        };

        boxes.forEach((box) => box.addEventListener("change", updateSummary));

        groups.forEach((group) => {
            const toggle = group.querySelector("[data-group-toggle]");
            if (!toggle) {
                return;
            }
            toggle.addEventListener("change", () => {
                group.querySelectorAll(".member-checkbox").forEach((box) => {
                    if (!box.hidden && !box.disabled) {
                        box.checked = toggle.checked;
                    }
                });
                updateSummary();
            });
        });

        if (search) {
            search.addEventListener("input", applyFilter);
        }
        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                boxes.forEach((box) => {
                    if (!box.disabled) {
                        box.checked = false;
                    }
                });
                updateSummary();
            });
        }

        updateSummary();
        applyFilter();
    });
}

function initAudiencePicker() {
    document.querySelectorAll("[data-audience-toggle]").forEach((radio) => {
        const target = document.getElementById(radio.dataset.audienceToggle);
        if (!target) {
            return;
        }
        const apply = () => {
            target.classList.toggle("d-none", !radio.checked);
        };
        radio.addEventListener("change", apply);
        apply();
    });
}

function initTemplateInsert() {
    document.querySelectorAll("[data-template-picker]").forEach((picker) => {
        picker.querySelectorAll("[data-template-content]").forEach((button) => {
            button.addEventListener("click", () => {
                const textarea = document.getElementById("content");
                if (!textarea) {
                    return;
                }
                const content = button.dataset.templateContent || "";
                if (!content) {
                    return;
                }
                textarea.value = textarea.value
                    ? `${textarea.value}\n${content}`
                    : content;
                textarea.dispatchEvent(new Event("input", { bubbles: true }));
                textarea.focus();
            });
        });
    });
}

function initThemeToggle() {
    const root = document.documentElement;
    const themeButton = document.getElementById("theme-toggle-btn");
    const themeColorMeta = document.querySelector("meta[name='theme-color']");
    if (!themeButton) {
        return;
    }

    const applyThemeUi = (theme) => {
        const isDark = theme === "dark";
        const title = isDark ? "Theme clair" : "Theme sombre";
        const iconClass = isDark ? "bi-sun" : "bi-moon-stars";
        themeButton.setAttribute("title", title);
        themeButton.setAttribute("aria-label", `Basculer vers le ${title.toLowerCase()}`);
        themeButton.innerHTML = `<i class="bi ${iconClass}" aria-hidden="true"></i>`;

        if (themeColorMeta) {
            themeColorMeta.setAttribute("content", isDark ? "#151724" : "#f6f4ee");
        }
    };

    const setTheme = (theme) => {
        root.setAttribute("data-theme", theme);
        localStorage.setItem("edulink-theme", theme);
        applyThemeUi(theme);
    };

    const currentTheme = root.getAttribute("data-theme") || "light";
    applyThemeUi(currentTheme);

    themeButton.addEventListener("click", () => {
        const activeTheme = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
        setTheme(activeTheme === "dark" ? "light" : "dark");
    });
}

function initCharCounters() {
    document.querySelectorAll("[data-maxlength]").forEach((input) => {
        const max = parseInt(input.dataset.maxlength, 10);
        const counter = document.querySelector(`[data-counter-for="${input.id}"]`);
        if (!counter) {
            return;
        }

        const update = () => {
            const length = input.value.length;
            counter.textContent = `${length} / ${max}`;
            counter.classList.toggle("is-over", length > max);
        };

        input.addEventListener("input", update);
        update();
    });
}

function initConfirmDialogs() {
    document.addEventListener("submit", (event) => {
        const confirmMessage = event.submitter && event.submitter.dataset.confirm;
        if (confirmMessage && !window.confirm(confirmMessage)) {
            event.preventDefault();
        }
    });
}

function initCopyButtons() {
    document.querySelectorAll("[data-copy-target]").forEach((button) => {
        button.addEventListener("click", async () => {
            const target = document.getElementById(button.dataset.copyTarget);
            if (!target) {
                return;
            }
            const text = target.value || target.textContent || "";
            if (!text) {
                return;
            }
            try {
                await navigator.clipboard.writeText(text);
                const original = button.innerHTML;
                button.innerHTML =
                    '<i class="bi bi-check-lg me-1" aria-hidden="true"></i>Copie';
                setTimeout(() => {
                    button.innerHTML = original;
                }, 1500);
            } catch (err) {
                target.select();
                target.setSelectionRange(0, target.value.length);
            }
        });
    });
}

function initAutoGrow() {
    document.querySelectorAll("[data-auto-grow]").forEach((el) => {
        const resize = () => {
            el.style.height = "auto";
            el.style.height = `${el.scrollHeight}px`;
        };
        el.addEventListener("input", resize);
        resize();
    });
}

function initChatScroll() {
    const container = document.getElementById("messages-container");
    if (!container) {
        return;
    }

    const hasBefore = new URLSearchParams(window.location.search).has("before");
    container.scrollTop = hasBefore ? 0 : container.scrollHeight;
}

function initFileZone() {
    const zone = document.querySelector("[data-file-label]");
    if (!zone) {
        return;
    }

    const input = document.getElementById(zone.getAttribute("for"));
    if (!input) {
        return;
    }

    const updateLabel = () => {
        const name = input.files && input.files[0] ? input.files[0].name : null;
        const strong = zone.querySelector("strong");
        const hint = zone.querySelector(".text-muted");
        if (name) {
            if (strong) {
                strong.textContent = name;
            }
            if (hint) {
                hint.textContent = "Pret a etre publie.";
            }
        } else if (strong && hint) {
            strong.textContent = "Deposer un PDF";
            hint.textContent = "Maximum 5 Mo, format PDF.";
        }
    };

    input.addEventListener("change", updateLabel);

    ["dragenter", "dragover"].forEach((eventName) => {
        zone.addEventListener(eventName, (event) => {
            event.preventDefault();
            zone.classList.add("is-dragover");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        zone.addEventListener(eventName, (event) => {
            event.preventDefault();
            zone.classList.remove("is-dragover");
        });
    });

    zone.addEventListener("drop", (event) => {
        if (event.dataTransfer && event.dataTransfer.files.length) {
            input.files = event.dataTransfer.files;
            updateLabel();
        }
    });
}

initThemeToggle();

initCharCounters();

initConfirmDialogs();

initAutoGrow();

initChatScroll();

initFileZone();

initMemberPicker();

initAudiencePicker();

initTemplateInsert();

initCopyButtons();

if (isAuthenticated) {
    initPushNotifications().catch((error) => {
        console.error("Push init failed", error);
    });
}

async function initPushNotifications() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        return;
    }

    const enableButton = document.getElementById("enable-push-btn");
    if (!enableButton) {
        return;
    }

    const showStatus = (text, className, iconClass, disabled = true) => {
        enableButton.className = `btn btn-sm me-2 ${className}`;
        enableButton.disabled = disabled;
        enableButton.classList.remove("d-none");
        enableButton.setAttribute("title", text);
        enableButton.setAttribute("aria-label", text);
        enableButton.innerHTML = `<i class="bi ${iconClass}" aria-hidden="true"></i>`;
    };

    const response = await fetch("/push/public-key", { credentials: "same-origin" });
    if (!response.ok) {
        showStatus("Push indisponible", "btn-outline-warning", "bi-bell-slash", true);
        return;
    }

    const data = await response.json();
    const publicKey = data.publicKey;
    if (!publicKey) {
        showStatus("Push non configure", "btn-outline-warning", "bi-bell-slash", true);
        return;
    }

    const registration = await navigator.serviceWorker.register("/service-worker.js");
    const existingSubscription = await registration.pushManager.getSubscription();
    if (existingSubscription) {
        showStatus("Push mobile active", "btn-success", "bi-bell-fill", true);
        return;
    }

    showStatus("Activer push mobile", "btn-warning", "bi-bell", false);
    enableButton.addEventListener("click", async () => {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
            showStatus("Permission refusee", "btn-outline-danger", "bi-bell-slash", true);
            return;
        }

        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey),
        });

        const csrfToken = document.querySelector("meta[name='csrf-token']")?.content || "";
        await fetch("/push/subscribe", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(subscription),
        });

        showStatus("Push mobile active", "btn-success", "bi-bell-fill", true);
    });
}