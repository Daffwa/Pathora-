(function () {
    "use strict";

    const root = document.getElementById("chat-page");
    if (!root) return;

    const conversations = JSON.parse(root.dataset.conversations || "[]");
    const initialSelectedConversationId = JSON.parse(root.dataset.selectedContact || "null");
    const sendMessageUrl = root.dataset.sendUrl || "/chat/messages";

    const chatForm = document.getElementById("chat-composer");
    const chatInput = document.getElementById("chat-message");
    const chatMessages = document.getElementById("chat-messages");
    const conversationList = document.getElementById("conversation-list");
    const chatBackButton = document.getElementById("chat-back-button");
    const searchInput = document.getElementById("message-search");
    const searchClearButton = document.getElementById("chat-search-clear");
    const contactAvatar = document.getElementById("chat-contact-avatar");
    const contactName = document.getElementById("chat-contact-name");
    const contactStatus = document.getElementById("chat-contact-status");
    const attachmentButton = document.getElementById("chat-attachment-button");
    const imageInput = document.getElementById("chat-image-input");
    const attachmentPreview = document.getElementById("chat-attachment-preview");
    const attachmentError = document.getElementById("chat-attachment-error");
    const allowedImageExtensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"];
    const maxImageSize = 5 * 1024 * 1024;
    const jakartaTimeFormatter = new Intl.DateTimeFormat("id-ID", {
        timeZone: "Asia/Jakarta",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
    let selectedConversationId = conversations.some(function (c) { return c.id === initialSelectedConversationId; })
        ? initialSelectedConversationId
        : (conversations[0] ? conversations[0].id : null);
    let filteredConversations = conversations;
    let selectedImage = null;
    var mobileChatQuery = window.matchMedia("(max-width: 768px)");
    let isChatRoomOpen = !mobileChatQuery.matches;

    function updateChatView() {
        var showRoom = !mobileChatQuery.matches || isChatRoomOpen;
        root.classList.toggle("is-chat-open", showRoom);
        root.classList.toggle("is-contact-list-open", !showRoom);
        chatBackButton.hidden = !mobileChatQuery.matches;
    }

    function openChatRoom() {
        isChatRoomOpen = true;
        updateChatView();
    }

    function showConversationList() {
        isChatRoomOpen = false;
        updateChatView();
        searchInput.focus();
    }

    function getSelectedConversation() {
        return conversations.find(function (c) { return c.id === selectedConversationId; }) || null;
    }

    function normalizeText(value) {
        return String(value || "").toLowerCase().trim();
    }

    function conversationMatchesSearch(conversation, keyword) {
        return [conversation.name, conversation.role, conversation.company, conversation.lastMessage]
            .map(normalizeText)
            .some(function (value) { return value.includes(keyword); });
    }

    function updateSearchClearButton() {
        searchClearButton.hidden = searchInput.value.trim() === "";
    }

    function getJakartaTimeLabel(date) {
        date = date || new Date();
        return jakartaTimeFormatter.format(date).replace(/\./g, ":");
    }

    function formatFileSize(bytes) {
        if (bytes >= 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(1) + " MB";
        }
        return Math.max(1, Math.round(bytes / 1024)) + " KB";
    }

    function showAttachmentError(message) {
        attachmentError.textContent = message;
        attachmentError.hidden = false;
    }

    function clearAttachmentError() {
        attachmentError.textContent = "";
        attachmentError.hidden = true;
    }

    function clearSelectedImage() {
        if (selectedImage) {
            URL.revokeObjectURL(selectedImage.previewUrl);
        }
        selectedImage = null;
        imageInput.value = "";
        attachmentPreview.replaceChildren();
        attachmentPreview.classList.add("hidden");
        attachmentPreview.hidden = true;
    }

    function setSelectedImage(file) {
        clearSelectedImage();
        clearAttachmentError();
        selectedImage = { file: file, previewUrl: URL.createObjectURL(file) };

        var previewImage = document.createElement("img");
        previewImage.className = "chat-attachment-thumb";
        previewImage.src = selectedImage.previewUrl;
        previewImage.alt = file.name;

        var previewMeta = document.createElement("div");
        previewMeta.className = "chat-attachment-meta";

        var previewName = document.createElement("strong");
        previewName.textContent = file.name;

        var previewSize = document.createElement("span");
        previewSize.textContent = formatFileSize(file.size);

        var removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "chat-attachment-remove";
        removeButton.dataset.removeImage = "true";
        removeButton.setAttribute("aria-label", "Hapus gambar");
        removeButton.textContent = "\u00d7";

        previewMeta.append(previewName, previewSize);
        attachmentPreview.replaceChildren(previewImage, previewMeta, removeButton);
        attachmentPreview.classList.remove("hidden");
        attachmentPreview.hidden = false;
    }

    function validateImageFile(file) {
        if (!file) return false;
        var fileName = file.name.toLowerCase();
        var hasAllowedExtension = allowedImageExtensions.some(function (ext) { return fileName.endsWith(ext); });
        var hasAllowedMimeType = ["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type);
        if (!hasAllowedExtension || !hasAllowedMimeType) {
            clearSelectedImage();
            showAttachmentError("Hanya file gambar yang dapat dikirim.");
            return false;
        }
        if (file.size > maxImageSize) {
            clearSelectedImage();
            showAttachmentError("Ukuran gambar maksimal 5 MB.");
            return false;
        }
        return true;
    }

    function renderEmptyContactState() {
        var el = document.createElement("div");
        el.className = "chat-empty-contact-state";
        var title = document.createElement("p");
        title.className = "chat-empty-contact-title";
        title.textContent = "Kontak tidak ditemukan";
        var text = document.createElement("p");
        text.className = "chat-empty-contact-text";
        text.textContent = "Coba gunakan nama atau kata kunci lain.";
        el.append(title, text);
        conversationList.appendChild(el);
    }

    function renderConversationList() {
        conversationList.replaceChildren();
        if (!filteredConversations.length) {
            renderEmptyContactState();
            return;
        }
        filteredConversations.forEach(function (conversation) {
            var button = document.createElement("button");
            button.className = "conversation-item";
            button.type = "button";
            button.dataset.conversationId = conversation.id;
            button.setAttribute("aria-pressed", String(conversation.id === selectedConversationId));
            if (conversation.id === selectedConversationId) button.classList.add("active");

            var avatar = document.createElement("span");
            avatar.className = "avatar small-avatar";
            avatar.textContent = conversation.avatar;

            var content = document.createElement("span");
            var name = document.createElement("strong");
            name.textContent = conversation.name;
            var lastMessage = document.createElement("small");
            lastMessage.textContent = conversation.lastMessage;
            content.append(name, lastMessage);

            var time = document.createElement("time");
            time.textContent = conversation.time;

            button.append(avatar, content, time);
            conversationList.appendChild(button);
        });
    }

    function renderChatHeader() {
        var conversation = getSelectedConversation();
        if (!conversation) {
            contactAvatar.textContent = "";
            contactName.textContent = "Pilih percakapan";
            contactStatus.textContent = "Pilih percakapan untuk mulai chat.";
            return;
        }
        contactAvatar.textContent = conversation.avatar;
        contactName.textContent = conversation.name;
        contactStatus.textContent = [conversation.role, conversation.status].filter(Boolean).join(" \u2022 ");
    }

    function appendImageToBubble(bubble, imageUrl, fileName) {
        var img = document.createElement("img");
        img.className = "chat-message-image";
        img.src = imageUrl;
        img.alt = fileName;
        img.addEventListener("error", function () {
            img.remove();
            var fb = document.createElement("span");
            fb.className = "chat-image-fallback";
            fb.textContent = "Gambar tidak dapat dimuat.";
            bubble.prepend(fb);
        });
        bubble.prepend(img);
    }

    function createMessageBubble(message) {
        var bubble = document.createElement("div");
        bubble.className = "chat-message-bubble";
        if (message.imageUrl) {
            bubble.classList.add("has-image");
            appendImageToBubble(bubble, message.imageUrl, message.imageName || "Gambar");
        }
        if (message.text) {
            var p = document.createElement("p");
            p.textContent = message.text;
            bubble.appendChild(p);
        }
        return bubble;
    }

    function createTextBubble(message) {
        var p = document.createElement("p");
        p.textContent = message.text;
        return p;
    }

    function renderMessage(message, conversation) {
        var row = document.createElement("article");
        var isUser = message.sender === "user";
        row.className = "message-row " + (isUser ? "outgoing" : "incoming");
        if (!isUser) {
            var avatar = document.createElement("span");
            avatar.className = "avatar mini-avatar";
            avatar.textContent = conversation.avatar;
            row.appendChild(avatar);
        }
        var content = document.createElement("div");
        content.appendChild(message.imageUrl ? createMessageBubble(message) : createTextBubble(message));
        var time = document.createElement("time");
        time.textContent = message.time || "Baru saja";
        content.appendChild(time);
        row.appendChild(content);
        chatMessages.appendChild(row);
    }

    function renderMessages() {
        var conversation = getSelectedConversation();
        chatMessages.replaceChildren();
        chatInput.disabled = !conversation;
        if (!conversation) {
            var es = document.createElement("div");
            es.className = "chat-empty-state";
            es.textContent = "Pilih percakapan untuk mulai chat.";
            chatMessages.appendChild(es);
            return;
        }
        if (!conversation.messages.length) {
            var es = document.createElement("div");
            es.className = "chat-empty-state";
            es.textContent = conversation.emptyText || "Belum ada pesan. Mulai percakapan ini.";
            chatMessages.appendChild(es);
            return;
        }
        var dateChip = document.createElement("div");
        dateChip.className = "date-chip";
        dateChip.textContent = "Hari Ini";
        chatMessages.appendChild(dateChip);
        conversation.messages.forEach(function (msg) { renderMessage(msg, conversation); });
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function renderChat() {
        renderConversationList();
        renderChatHeader();
        renderMessages();
        updateChatView();
    }

    function filterConversations(query) {
        var keyword = normalizeText(query);
        filteredConversations = keyword
            ? conversations.filter(function (c) { return conversationMatchesSearch(c, keyword); })
            : conversations;
        var selectedIsVisible = filteredConversations.some(function (c) { return c.id === selectedConversationId; });
        if (!selectedIsVisible) {
            selectedConversationId = filteredConversations.length ? filteredConversations[0].id : null;
            clearSelectedImage();
            clearAttachmentError();
        }
        renderChat();
        updateSearchClearButton();
    }

    function selectConversation(conversationId) {
        if (selectedConversationId === conversationId) {
            openChatRoom();
            chatInput.focus();
            return;
        }
        selectedConversationId = conversationId;
        clearSelectedImage();
        clearAttachmentError();
        renderChat();
        openChatRoom();
        chatInput.focus();
    }

    function updateConversationAfterSend(conversation, message) {
        conversation.messages.push(message);
        conversation.lastMessage = message.text || "Mengirim gambar";
        conversation.time = message.contactTime || message.time || getJakartaTimeLabel();
        conversation.sortTime = message.createdAt || new Date().toISOString();
        conversations.sort(function (a, b) { return String(b.sortTime || "").localeCompare(String(a.sortTime || "")); });
        renderChat();
    }

    async function sendChatMessage() {
        var conversation = getSelectedConversation();
        var message = chatInput.value.trim();
        var image = selectedImage;
        if (!conversation || (!message && !image)) return;

        try {
            chatInput.disabled = true;
            var formData = new FormData();
            formData.append("contact_id", conversation.contactId);
            formData.append("message", message);
            if (image) formData.append("image", image.file);

            var response = await fetch(sendMessageUrl, {
                method: "POST",
                headers: window.Pathora ? window.Pathora.withCsrfHeaders() : undefined,
                body: formData,
            });
            var data = await response.json().catch(function () { return ({}); });

            if (!response.ok) throw new Error(data.error || "Pesan belum bisa dikirim.");

            conversation.threadId = data.thread_id;
            chatInput.value = "";
            clearSelectedImage();
            clearAttachmentError();
            updateConversationAfterSend(conversation, data.message);
        } catch (error) {
            showAttachmentError(error.message || "Pesan belum bisa dikirim. Silakan coba lagi.");
            renderChatHeader();
            renderMessages();
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    chatForm.addEventListener("submit", function (event) { event.preventDefault(); sendChatMessage(); });
    chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendChatMessage(); }
    });
    searchInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") { event.preventDefault(); filterConversations(searchInput.value); }
        if (event.key === "Escape") { searchInput.value = ""; filterConversations(""); }
    });
    searchInput.addEventListener("input", updateSearchClearButton);
    searchClearButton.addEventListener("click", function () { searchInput.value = ""; filterConversations(""); searchInput.focus(); });
    attachmentButton.addEventListener("click", function () { imageInput.click(); });
    chatBackButton.addEventListener("click", showConversationList);
    conversationList.addEventListener("click", function (event) {
        var btn = event.target.closest ? event.target.closest("[data-conversation-id]") : null;
        if (btn) selectConversation(btn.dataset.conversationId);
    });
    imageInput.addEventListener("change", function () {
        var file = imageInput.files[0];
        if (validateImageFile(file)) setSelectedImage(file);
    });
    mobileChatQuery.addEventListener("change", function (event) { isChatRoomOpen = !event.matches; updateChatView(); });

    document.addEventListener("click", function (event) {
        var btn = event.target.closest ? event.target.closest("[data-remove-image]") : null;
        if (!btn) return;
        event.preventDefault();
        event.stopPropagation();
        clearSelectedImage();
        clearAttachmentError();
        chatInput.focus();
    });

    clearSelectedImage();
    renderChat();
})();
