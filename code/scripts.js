// Constants for frequently accessed elements
const STAFF_TABLE = document.getElementById('staffTable');

// CSV Fetching and Table Populating
function fetchCSVAndPopulate() {
    fetch('../data/staff.csv')
        .then(response => response.text())
        .then(data => {
            populateTable(data.split('\n').slice(1)); // Skip header row
            updateCounts();
        });
}

function populateTable(rows) {
    const tableBody = STAFF_TABLE.tBodies[0];
    rows.forEach(row => {
        const columns = row.split(',');
        const tr = document.createElement('tr');
        tr.appendChild(createTableCell(columns[0], 'bold'));
        tr.appendChild(createBooleanTableCell(columns[1], 'cardiac'));
        tr.appendChild(createBooleanTableCell(columns[2], 'charge'));
        tableBody.appendChild(tr);
    });
}

function createTableCell(content, className) {
    const td = document.createElement('td');
    td.textContent = content;
    td.classList.add(className);
    return td;
}

function createBooleanTableCell(value, trueClass) {
    const td = createTableCell(value.trim() === "TRUE" ? "Yes" : "No");
    if (td.textContent === "Yes") {
        td.classList.add(trueClass);
    } else {
        td.classList.add('muted');
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
function updateCounts() {
    const nameCount = STAFF_TABLE.tBodies[0].rows.length;
    const cardiacYesCount = Array.from(STAFF_TABLE.tBodies[0].rows).filter(row => row.cells[1].textContent.trim() === "Yes").length;
    const chargeYesCount = Array.from(STAFF_TABLE.tBodies[0].rows).filter(row => row.cells[2].textContent.trim() === "Yes").length;

    document.getElementById("nameCount").textContent = nameCount;
    document.getElementById("cardiacCount").textContent = cardiacYesCount;
    document.getElementById("chargeCount").textContent = chargeYesCount;
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

function getAdjacentColumnClass(currentDay, direction) {
    if (direction === 'prev') {
        return `doctor-dropdown-${getPrevDay(currentDay)}`;
    } else if (direction === 'next') {
        return `doctor-dropdown-${getNextDay(currentDay)}`;
    }
    return '';
}

function handleDropdownChange(dropdown) {
    let prevValue = dropdown.value;

    dropdown.addEventListener('change', function(event, isRecursive = false) {
        const currentValue = this.value;
        const currentColIndex = Array.from(this.parentElement.parentElement.children).indexOf(this.parentElement);
        const rowName = this.closest('tr').querySelector('td').textContent.trim();
        const tableBody = document.querySelector("#scheduleTable tbody");
        const currentDay = this.getAttribute('data-day');
        const prevDay = getPrevDay(currentDay);
        const nextDay = getNextDay(currentDay);

        if (currentValue) {
            if (rowName === "Call") {
                const prevRowDropdown = tableBody.querySelector(`tr[role-name="Pre Call"] .doctor-dropdown-${prevDay}`);
                const nextRowDropdown = tableBody.querySelector(`tr[role-name="Post Call"] .doctor-dropdown-${nextDay}`);

                if (prevRowDropdown) {
                    prevRowDropdown.value = currentValue;
                    if(!isRecursive) {
                        prevRowDropdown.dispatchEvent(new CustomEvent('change', { detail: { isRecursive: true }}));
                    }
                }
                if (nextRowDropdown) {
                    nextRowDropdown.value = currentValue;
                    if(!isRecursive) {
                        nextRowDropdown.dispatchEvent(new CustomEvent('change', { detail: { isRecursive: true }}));
                    }
                }

            } else if (rowName === "Late") {
                const prevRowDropdown = tableBody.querySelector(`tr[role-name="Pre Late"] .doctor-dropdown-${prevDay}`);
                const nextRowDropdown = tableBody.querySelector(`tr[role-name="Post Late"] .doctor-dropdown-${nextDay}`);

                if (prevRowDropdown) {
                    prevRowDropdown.value = currentValue;
                    if(!isRecursive) {
                        prevRowDropdown.dispatchEvent(new CustomEvent('change', { detail: { isRecursive: true }}));
                    }
                }
                if (nextRowDropdown) {
                    nextRowDropdown.value = currentValue;
                    if(!isRecursive) {
                        nextRowDropdown.dispatchEvent(new CustomEvent('change', { detail: { isRecursive: true }}));
                    }
                }
            }
        }

        // Re-enable the previous value for other dropdowns in the same column
        if (prevValue) enableDropdownOption(`doctor-dropdown-${currentDay}`, prevValue);

        // Disable the current value for other dropdowns in the same column
        if (currentValue) disableDropdownOption(`doctor-dropdown-${currentDay}`, currentValue, this);

        prevValue = currentValue;
    });
}

function getColumnClass(element) {
    const suffixes = ['mon', 'tue', 'wed', 'thu', 'fri'];
    for (const suffix of suffixes) {
        if (element.classList.contains(`doctor-dropdown-${suffix}`)) {
            return `doctor-dropdown-${suffix}`;
        }
    }
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
    const daysRow = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    csvContent.push(daysRow.join(','));

    const rows = Array.from(document.querySelectorAll('.group-content'));
    const csvRows = rows.map(row => {
        const columns = Array.from(row.querySelectorAll('.doctor-dropdown'));
        return columns.map(column => column.value).join(',');
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
