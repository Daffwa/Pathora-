(function () {
    const popovers = Array.from(document.querySelectorAll(".topbar-popover"));

    if (!popovers.length) {
        return;
    }

    function syncPopoverState(popover) {
        const summary = popover.querySelector("summary");
        const panel = popover.querySelector(".popover-panel");
        const isOpen = popover.open;

        if (summary) {
            summary.setAttribute("aria-expanded", String(isOpen));
        }

        if (panel) {
            panel.setAttribute("aria-hidden", String(!isOpen));
        }
    }

    function closeTopbarPopovers(exceptPopover) {
        popovers.forEach((popover) => {
            if (popover === exceptPopover) {
                syncPopoverState(popover);
                return;
            }

            popover.open = false;
            syncPopoverState(popover);
        });
    }

    popovers.forEach((popover) => {
        const summary = popover.querySelector("summary");

        syncPopoverState(popover);

        if (summary) {
            summary.addEventListener("click", () => {
                closeTopbarPopovers(popover);
            });
        }

        popover.addEventListener("toggle", () => {
            if (popover.open) {
                closeTopbarPopovers(popover);
            }

            syncPopoverState(popover);
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".topbar-popover")) {
            closeTopbarPopovers();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeTopbarPopovers();
        }
    });
})();

(function () {
    const sidebar = document.getElementById("app-sidebar");
    const menuButton = document.querySelector("[data-mobile-menu-button]");
    const overlay = document.querySelector("[data-sidebar-overlay]");

    if (!sidebar || !menuButton || !overlay) {
        return;
    }

    const mobileQuery = window.matchMedia("(max-width: 768px)");

    function setSidebarOpen(isOpen) {
        sidebar.classList.toggle("is-open", isOpen);
        overlay.classList.toggle("is-open", isOpen);
        overlay.hidden = !isOpen;
        document.body.classList.toggle("sidebar-drawer-open", isOpen);
        menuButton.setAttribute("aria-expanded", String(isOpen));
    }

    menuButton.addEventListener("click", () => {
        setSidebarOpen(!sidebar.classList.contains("is-open"));
    });

    overlay.addEventListener("click", () => setSidebarOpen(false));

    sidebar.addEventListener("click", (event) => {
        if (mobileQuery.matches && event.target.closest("a")) {
            setSidebarOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setSidebarOpen(false);
        }
    });

    mobileQuery.addEventListener("change", (event) => {
        if (!event.matches) {
            setSidebarOpen(false);
        }
    });
})();
