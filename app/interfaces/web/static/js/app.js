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
