(function () {
    "use strict";

    var roleRadios = document.querySelectorAll('input[name="role"]');
    var jobseekerFields = document.querySelector('[data-role-fields="jobseeker"]');
    var recruiterFields = document.querySelector('[data-role-fields="recruiter"]');
    var companyNameInput = document.getElementById("company_name");
    var companyPositionInput = document.getElementById("company_position");
    var otherPositionFields = document.querySelector("[data-other-position]");
    var otherPositionInput = document.getElementById("company_position_other");

    if (!roleRadios.length || !jobseekerFields || !recruiterFields) {
        return;
    }

    function selectedRole() {
        var checked = document.querySelector('input[name="role"]:checked');
        return checked ? checked.value : "jobseeker";
    }

    function syncOtherPosition() {
        var isRecruiter = selectedRole() === "recruiter";
        var isOther = companyPositionInput && companyPositionInput.value === "Other";

        if (otherPositionFields) {
            otherPositionFields.hidden = !isRecruiter || !isOther;
        }
        if (otherPositionInput) {
            otherPositionInput.required = isRecruiter && isOther;
        }
    }

    function syncRoleFields() {
        var isRecruiter = selectedRole() === "recruiter";
        jobseekerFields.hidden = isRecruiter;
        recruiterFields.hidden = !isRecruiter;

        if (companyNameInput) {
            companyNameInput.required = isRecruiter;
        }
        if (companyPositionInput) {
            companyPositionInput.required = isRecruiter;
        }

        syncOtherPosition();
    }

    roleRadios.forEach(function (radio) {
        radio.addEventListener("change", syncRoleFields);
    });

    if (companyPositionInput) {
        companyPositionInput.addEventListener("change", syncOtherPosition);
    }

    syncRoleFields();
})();
