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

    var roleRadios = document.querySelectorAll('input[name="role"]');
    var companyGroup = document.getElementById("company-group");
    var recruiterPositionSelect = document.getElementById("recruiter-position-select");
    var otherPositionGroup = document.getElementById("other-position-group");

    function toggleRecruiterFields() {
        if (!companyGroup) return;
        var isRecruiter = Array.from(roleRadios).some(function (r) { return r.checked && r.value === "recruiter"; });
        companyGroup.hidden = !isRecruiter;
        if (recruiterPositionSelect) recruiterPositionSelect.hidden = !isRecruiter;
        if (otherPositionGroup) {
            var sel = document.getElementById("company_position");
            otherPositionGroup.hidden = !isRecruiter || !sel || sel.value !== "Other";
        }
    }

    roleRadios.forEach(function (r) { r.addEventListener("change", toggleRecruiterFields); });
    toggleRecruiterFields();

    var positionSelect = document.getElementById("company_position");
    if (positionSelect) {
        positionSelect.addEventListener("change", function () {
            if (otherPositionGroup) {
                otherPositionGroup.hidden = this.value !== "Other";
            }
        });
    }
})();
