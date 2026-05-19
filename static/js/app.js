(function () {
    "use strict";

    document.querySelectorAll("[data-pct]").forEach(function (el) {
        el.style.setProperty("--pct", el.dataset.pct + "%");
    });

    document.querySelectorAll("[data-confirm]").forEach(function (el) {
        el.addEventListener("submit", function (e) {
            if (!confirm(el.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    document.querySelectorAll("[data-sync-select]").forEach(function (sel) {
        var target = document.getElementById(sel.dataset.syncSelect);
        if (target) {
            sel.addEventListener("change", function () { target.value = this.value; });
        }
    });

    document.querySelectorAll("[data-set-value]").forEach(function (btn) {
        var parts = (btn.dataset.setValue || "").split("|");
        if (parts.length === 2) {
            var target = document.getElementById(parts[0]);
            if (target) {
                btn.addEventListener("click", function () { target.value = parts[1]; });
            }
        }
    });

    document.querySelectorAll("[data-select-all-target]").forEach(function (checkbox) {
        var targetId = checkbox.dataset.selectAllTarget;
        if (!targetId) return;
        var target = document.getElementById(targetId);
        if (!target) return;

        checkbox.addEventListener("change", function () {
            var checked = checkbox.checked;
            target.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
                cb.checked = checked;
            });
        });
    });

})();
