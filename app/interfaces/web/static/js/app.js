const socket = io();

socket.on("connect", () => {
    console.log("Socket connected");
});

socket.on("notification", (payload) => {
    const list = document.getElementById("notifications-list");
    if (!list) return;

    const item = document.createElement("li");
    item.className = "list-group-item fw-semibold";
    item.textContent = payload.content;
    list.prepend(item);
});

socket.on("channel_message", () => {
    if (window.location.pathname.includes("/messages/channels/")) {
        window.location.reload();
    }
});

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
            themeColorMeta.setAttribute("content", isDark ? "#282a36" : "#f4f7fc");
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

async function initPushNotifications() {
    const isAuthenticated = document.body.dataset.authenticated === "1";
    if (!isAuthenticated) {
        return;
    }

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

initThemeToggle();

initPushNotifications().catch((error) => {
    console.error("Push init failed", error);
});
