(function () {
    "use strict";

    var form = document.getElementById("applicant-bulk-form");
    var selectAll = document.getElementById("select-all-applicants");

    if (!form || !selectAll) {
        return;
    }

    var checkboxes = Array.from(form.querySelectorAll('input[name="application_ids"]'));

    function syncSelectAll() {
        var selectedCount = checkboxes.filter(function (checkbox) {
            return checkbox.checked;
        }).length;

        selectAll.checked = checkboxes.length > 0 && selectedCount === checkboxes.length;
        selectAll.indeterminate = selectedCount > 0 && selectedCount < checkboxes.length;
    }

    selectAll.addEventListener("change", function () {
        checkboxes.forEach(function (checkbox) {
            checkbox.checked = selectAll.checked;
        });
        syncSelectAll();
    });

    checkboxes.forEach(function (checkbox) {
        checkbox.addEventListener("change", syncSelectAll);
    });

    syncSelectAll();
})();
