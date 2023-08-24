// Constants for frequently accessed elements
const STAFF_TABLE = document.getElementById('staffTable');
let nameCount = 0;
const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]

// CSV Fetching and Table Populating
function fetchCSVAndPopulate() {
    fetch('data/staff.csv')
        .then(response => response.text())
        .then(data => {
            populateTable(data.split('\n').slice(1)); // Skip header row
            setStaffCounts();
            updateFooterCounts();
        });
}

function populateTable(rows) {
    const tableBody = STAFF_TABLE.tBodies[0];
    rows.forEach(row => {
        const columns = row.split(',');
        const name = columns[0].trim();
        const tr = document.createElement('tr');

        tr.setAttribute('staff-name', name); // Set data-name attribute
        tr.appendChild(createTableCell(name, 'bold'));
        tr.appendChild(createBooleanTableCell(columns[1], 'cardiac'));
        tr.appendChild(createBooleanTableCell(columns[2], 'charge'));
        tr.appendChild(createTableCell("0", 'assg0'));
        tr.appendChild(createTableCell("0", 'pnts0'));
        tableBody.appendChild(tr);
    });
}

function createTableCell(content, className) {
    const td = document.createElement('td');
    td.innerHTML = content;
    td.classList.add(className);
    return td;
}

function createBooleanTableCell(value, trueClass) {
    const isSet = value.trim() === "TRUE";
    const icon = trueClass == 'cardiac' ? "fa-heart" : trueClass == 'charge' ? "fa-users" : "fa-check-square";
    const td = createTableCell(isSet ? "<i class='fa " + icon + "'></i>" : "");
    if (isSet) {
        td.classList.add(trueClass);
    }
    return td;
}

// Table Sorting
let sortOrder = 'asc';

function sortTable(columnIndex) {
    const rows = Array.from(STAFF_TABLE.tBodies[0].rows);
    const orderMultiplier = sortOrder === 'asc' ? 1 : -1;

    const sortedRows = rows.sort((a, b) => {
        const cellA = a.cells[columnIndex].textContent.trim().toLowerCase();
        const cellB = b.cells[columnIndex].textContent.trim().toLowerCase();
        return cellA.localeCompare(cellB) * orderMultiplier;
    });

    STAFF_TABLE.tBodies[0].innerHTML = '';
    STAFF_TABLE.tBodies[0].append(...sortedRows);

    sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
}

// Count Update
function setStaffCounts() {
    nameCount = STAFF_TABLE.tBodies[0].rows.length;
    const cardiacYesCount = Array.from(STAFF_TABLE.tBodies[0].rows).filter(row => row.cells[1].innerHTML.trim() !== "").length;
    const chargeYesCount = Array.from(STAFF_TABLE.tBodies[0].rows).filter(row => row.cells[2].innerHTML.trim() !== "").length;

    document.getElementById("nameCount").textContent = nameCount.toString();
    document.getElementById("cardiacCount").textContent = cardiacYesCount.toString();
    document.getElementById("chargeCount").textContent = chargeYesCount.toString();
    document.getElementById("assg0Count").textContent = "0";
    document.getElementById("pnts0Count").textContent = "0";
}

// Dropdown Handling
function populateDropdowns(doctorNames) {
    const dropdowns = document.querySelectorAll('.doctor-dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.appendChild(createOption("", ""));  // Default option

        doctorNames.forEach(name => {
            dropdown.appendChild(createOption(name, name));
        });

        handleDropdownChange(dropdown);
    });
}

function createOption(value, textContent) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = textContent;
    return option;
}

function getPrevDay(day) {
    switch (day) {
        case 'mon':
            return 'sun';
        case 'tue':
            return 'mon';
        case 'wed':
            return 'tue';
        case 'thu':
            return 'wed';
        case 'fri':
            return 'thu';
        case 'sat':
            return 'fri';
        case 'sun':
            return 'sat';
        default:
            return '';
    }
}

function getNextDay(day) {
    switch (day) {
        case 'mon':
            return 'tue';
        case 'tue':
            return 'wed';
        case 'wed':
            return 'thu';
        case 'thu':
            return 'fri';
        case 'fri':
            return 'sat';
        case 'sat':
            return 'sun';
        case 'sun':
            return 'mon';
        default:
            return '';
    }
}

// Pre-Call / Post-Call / Pre-Late / Post-Late Dropdowns are only editable via the Call and Late rows
document.addEventListener('DOMContentLoaded', function () {
    const preCallDropdowns = document.querySelectorAll('tr[role-name="Pre Call"] .doctor-dropdown');
    const postCallDropdowns = document.querySelectorAll('tr[role-name="Post Call"] .doctor-dropdown');

    const preLateDropdowns = document.querySelectorAll('tr[role-name="Pre Late"] .doctor-dropdown');
    const postLateDropdowns = document.querySelectorAll('tr[role-name="Post Late"] .doctor-dropdown');

    preCallDropdowns.forEach(dropdown => dropdown.disabled = true);
    postCallDropdowns.forEach(dropdown => dropdown.disabled = true);

    preLateDropdowns.forEach(dropdown => dropdown.disabled = true);
    postLateDropdowns.forEach(dropdown => dropdown.disabled = true);
});

function handleDropdownChange(dropdown) {
    let prevValue = dropdown.value;

    dropdown.addEventListener('change', function (event, isRecursive = false) {
        const currentValue = this.value;
        const currentDay = this.getAttribute('data-day');
        const prevDay = getPrevDay(currentDay);
        const nextDay = getNextDay(currentDay);
        const currentRow = this.closest('tr');
        const rowName = currentRow.querySelector('td').textContent.trim();
        const roleName = currentRow.getAttribute('role-name');
        const tableBody = document.querySelector("#scheduleTable tbody");

        if (rowName === "Call" || rowName === "Late") {
            const prevRole = rowName === "Call" ? "Pre Call" : "Pre Late";
            const nextRole = rowName === "Call" ? "Post Call" : "Post Late";

            const prevRowDropdown = tableBody.querySelector(`tr[role-name="${prevRole}"] .doctor-dropdown-${prevDay}`);
            const nextRowDropdown = tableBody.querySelector(`tr[role-name="${nextRole}"] .doctor-dropdown-${nextDay}`);

            if (currentValue) {
                if (prevRowDropdown) {
                    prevRowDropdown.value = currentValue;
                    if (!isRecursive) {
                        prevRowDropdown.dispatchEvent(new CustomEvent('change', {detail: {isRecursive: true}}));
                    }
                }
                if (nextRowDropdown) {
                    nextRowDropdown.value = currentValue;
                    if (!isRecursive) {
                        nextRowDropdown.dispatchEvent(new CustomEvent('change', {detail: {isRecursive: true}}));
                    }
                }
            } else {
                // Reset the values if current dropdown is set to default
                if (prevRowDropdown) {
                    prevRowDropdown.value = "";
                    if (!isRecursive) {
                        prevRowDropdown.dispatchEvent(new CustomEvent('change', {detail: {isRecursive: true}}));
                    }
                }
                if (nextRowDropdown) {
                    nextRowDropdown.value = "";
                    if (!isRecursive) {
                        nextRowDropdown.dispatchEvent(new CustomEvent('change', {detail: {isRecursive: true}}));
                    }
                }
            }
        }

        // Handle Vacation and Gill progressive enabling
        if (rowName === "Vacation" || rowName === "Gill") {
            // Extracting the number from the roleName
            const currentNumber = parseInt(roleName.match(/\d+/)[0]);
            const nextRow = tableBody.querySelector(`tr[role-name="${rowName} ${currentNumber + 1}"]`);

            // If the current dropdown value is set, enable the next row dropdown for the same day
            if (nextRow && currentValue) {
                const nextDropdown = nextRow.querySelector(`.doctor-dropdown-${currentDay}`);
                if (nextDropdown) nextDropdown.removeAttribute('disabled');
            }
            // If the current dropdown value is set to default, and it's not the first row, disable its dropdown
            else if (nextRow && !currentValue) {
                const nextDropdown = nextRow.querySelector(`.doctor-dropdown-${currentDay}`);
                if (nextDropdown && !nextDropdown.value) nextDropdown.setAttribute('disabled', 'true');
            }
        }

        // Re-enable the previous value for other dropdowns in the same column
        if (prevValue) enableDropdownOption(`doctor-dropdown-${currentDay}`, prevValue);

        // Disable the current value for other dropdowns in the same column
        if (currentValue) disableDropdownOption(`doctor-dropdown-${currentDay}`, currentValue, this);

        // Update the counts every time a dropdown changes
        updateFooterCounts(currentDay, currentValue, prevValue, rowName);

        prevValue = currentValue;
    });
}

function enableDropdownOption(columnClass, value) {
    toggleDropdownOption(columnClass, value, false);
}

function disableDropdownOption(columnClass, value, excludingElement) {
    toggleDropdownOption(columnClass, value, true, excludingElement);
}

function toggleDropdownOption(columnClass, value, isDisabled, excludingElement) {
    document.querySelectorAll(`.${columnClass}`).forEach(dropdown => {
        if (dropdown !== excludingElement) {
            const option = dropdown.querySelector(`option[value="${value}"]`);
            if (option) option.disabled = isDisabled;
        }
    });
}

// Content Toggling
document.querySelectorAll('.group-header').forEach(header => {
    header.addEventListener('click', () => {
        let contentRows = header.nextElementSibling;
        while (contentRows && contentRows.classList.contains('group-content')) {
            contentRows.classList.toggle('hidden'); // This will add the class if it's not there, and remove it if it is
            contentRows = contentRows.nextElementSibling;
        }
    });
});

// Count all pre-set values
function calculateRequestedCounts(day) {
    return Array.from(document.querySelectorAll(`.admin-group .doctor-dropdown-${day}, .content-whine-zone .doctor-dropdown-${day}`))
        .filter(dropdown => dropdown.value).length;
}

function calculateAssignedCounts(day) {
    return Array.from(document.querySelectorAll(`.doctor-dropdown-${day}:not(.admin-group .doctor-dropdown, .content-whine-zone .doctor-dropdown)`))
        .filter(dropdown => dropdown.value).length;
}

function updateFooterCounts(day = null, currentValue = null, prevValue = null, roleName = null) {
    const days = day ? [day] : ["mon", "tue", "wed", "thu", "fri"];

    days.forEach(day => {
        const preassigned = calculateAssignedCounts(day);
        document.querySelector(`.set-values-count[data-day-total="${day}"]`).textContent = preassigned.toString();

        const requested = calculateRequestedCounts(day);
        document.querySelector(`.requested-values-count[data-day-total="${day}"]`).textContent = requested.toString();

        const unassigned = nameCount - preassigned;
        document.querySelector(`.unset-values-count[data-day-total="${day}"]`).textContent = unassigned.toString();
    });

    // Update the Points column if current or previous value is set
    if (currentValue || prevValue) {
        let grandTotalPointsElem = document.getElementById('assg0Count');
        let grandTotalPoints = parseInt(grandTotalPointsElem.textContent);

        console.log(grandTotalPoints)
        // Increase the points for currentValue row in the Points column of the Staff table
        if (currentValue) {
            const currentRow = document.querySelector(`tr[staff-name="${currentValue}"]`);
            const currentPoints = currentRow.querySelector('.assg0');
            currentPoints.textContent = (parseInt(currentPoints.textContent) + 1).toString();
            grandTotalPoints = grandTotalPoints + 1;
        }
        // Decrease the points for prevValue row in the Points column of the Staff table
        if (prevValue) {
            const prevRow = document.querySelector(`tr[staff-name="${prevValue}"]`);
            const prevPoints = prevRow.querySelector('.assg0');
            prevPoints.textContent = (parseInt(prevPoints.textContent) - 1).toString();
            grandTotalPoints = grandTotalPoints - 1;
        }
        grandTotalPointsElem.textContent = grandTotalPoints.toString();  // Update the grand total in the table
    }
}

// Initial Calls
document.addEventListener('DOMContentLoaded', () => {
    fetchCSVAndPopulate();
    fetch('../data/staff.csv')
        .then(response => response.text())
        .then(data => populateDropdowns(data.split('\n').slice(1).map(line => line.split(',')[0])));
});

// Create a Function to Generate CSV from Table
function generateCSVFromTable() {
    // Create the CSV content from the table
    const csvContent = [];

    // Add column names (days) to the first row
    const columnNames = ['role'];
    WEEKDAYS.forEach(day => columnNames.push(day));
    csvContent.push(columnNames.join(','));

    const rows = Array.from(document.querySelectorAll('.group-content'));
    const csvRows = rows.map(row => {
        const role = row.getAttribute('role-name'); // Get the 'role-name' attribute
        const columns = Array.from(row.querySelectorAll('.doctor-dropdown'));
        const roleAndColumns = [role, ...columns.map(column => column.value)]; // Prepend the role value
        return roleAndColumns.join(',');
    });

    // Add the CSV rows to the content
    csvContent.push(csvRows.join('\n'));

    return csvContent.join('\n');
}

// Create a Function to Trigger Download
function downloadCSV(filename, csvContent) {
    const blob = new Blob([csvContent], {type: 'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

// Add Event Listener to Save Button
const saveButton = document.getElementById('saveButton'); // Replace with the actual ID of your save button

saveButton.addEventListener('click', () => {
    const csvContent = generateCSVFromTable();
    downloadCSV('schedule.csv', csvContent);
});

// Initially disable all dropdowns for "gill" and "vacation" groups
document.querySelectorAll('.group-gill .doctor-dropdown, .group-vacation .doctor-dropdown').forEach(dropdown => {
    dropdown.disabled = true;
});

// Enable only the first role's dropdowns for each group
document.querySelector('tr[role-name="Gill 1"]').querySelectorAll('.doctor-dropdown').forEach(dropdown => {
    dropdown.removeAttribute('disabled');
});
document.querySelector('tr[role-name="Vacation 1"]').querySelectorAll('.doctor-dropdown').forEach(dropdown => {
    dropdown.removeAttribute('disabled');
});
