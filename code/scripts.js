// Constants for frequently accessed elements
const STAFF_TABLE = document.getElementById('staffTable');
let STAFF_MEMBERS = [];
const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"]


// Initial Calls
async function init() {
    await fetchCSVAndPopulateStaffTable();
    populateStaffMemberDropdowns();
    clearTable();
}

document.addEventListener('DOMContentLoaded', init);

// CSV Fetching and Table Populating
async function fetchCSVAndPopulateStaffTable() {
    const response = await fetch('data/staff.csv');
    const data = await response.text();
    const rows = data.split('\n').slice(1);  // Skip header row
    populateTable(rows);
}

function createTableRowFromData(data) {
    const columns = data.split(',');
    const name = columns[0].trim();

    const tr = document.createElement('tr');
    tr.setAttribute('staff-name', name); // Set data-name attribute
    tr.appendChild(createTableCell(name, 'bold'));
    tr.appendChild(createBooleanTableCell(columns[1], 'cardiac'));
    tr.appendChild(createBooleanTableCell(columns[2], 'charge'));
    tr.appendChild(createTableCell("0", 'assg0'));
    tr.appendChild(createTableCell("0", 'pnts0'));

    return tr;
}

function populateTable(rows) {
    const tableBody = STAFF_TABLE.tBodies[0];

    // Populate the STAFF_MEMBERS array
    STAFF_MEMBERS = rows.map(row => row.split(',')[0].trim());
    if (STAFF_MEMBERS.length == 0) console.warn('No staff members imported');

    rows.forEach(row => {
        const tr = createTableRowFromData(row);
        tableBody.appendChild(tr);
    });

    const cardiacYesCount = Array.from(STAFF_TABLE.tBodies[0].rows).filter(row => row.cells[1].innerHTML.trim() !== "").length;
    const chargeYesCount = Array.from(STAFF_TABLE.tBodies[0].rows).filter(row => row.cells[2].innerHTML.trim() !== "").length;

    document.querySelector("[data-count-static='name']").textContent = STAFF_MEMBERS.length.toString();
    document.querySelector("[data-count-static='diac']").textContent = cardiacYesCount.toString();
    document.querySelector("[data-count-static='chrg']").textContent = chargeYesCount.toString();
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

// Dropdown Handling

function populateStaffMemberDropdowns() {
    // Check if staffNames array is empty
    if (STAFF_MEMBERS.length === 0) {
        console.warn("No staff names found. Dropdowns will not be populated.");
        return;  // Exit the function early
    }

    const dropdowns = document.querySelectorAll('.doctor-dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.appendChild(createOption("", ""));  // Default option

        STAFF_MEMBERS.forEach(name => {
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
        case 'MON':
            return 'SUN';
        case 'TUE':
            return 'MON';
        case 'WED':
            return 'TUE';
        case 'THU':
            return 'WED';
        case 'FRI':
            return 'THU';
        case 'SAT':
            return 'FRI';
        case 'SUN':
            return 'SAT';
        default:
            return '';
    }
}

function getNextDay(day) {
    switch (day) {
        case 'MON':
            return 'TUE';
        case 'TUE':
            return 'WED';
        case 'WED':
            return 'THU';
        case 'THU':
            return 'FRI';
        case 'FRI':
            return 'SAT';
        case 'SAT':
            return 'SUN';
        case 'SUN':
            return 'MON';
        default:
            return '';
    }
}

// Pre-Call / Post-Call / Pre-Late / Post-Late Dropdowns are only editable via the Call and Late rows
document.addEventListener('DOMContentLoaded', function () {
    // For Pre Call dropdowns, excluding ones with the pre-role-weekend attribute
    const preCallDropdowns = document.querySelectorAll('tr[role-name="Pre Call"] .doctor-dropdown:not([pre-role-weekend])');

    // For Post Call dropdowns, excluding ones with the post-role-weekend attribute
    const postCallDropdowns = document.querySelectorAll('tr[role-name="Post Call"] .doctor-dropdown:not([post-role-weekend])');

    // For Pre Late dropdowns, excluding ones with the pre-role-weekend attribute
    const preLateDropdowns = document.querySelectorAll('tr[role-name="Pre Late"] .doctor-dropdown:not([pre-role-weekend])');

    // For Post Late dropdowns, excluding ones with the post-role-weekend attribute
    const postLateDropdowns = document.querySelectorAll('tr[role-name="Post Late"] .doctor-dropdown:not([post-role-weekend])');

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

            const prevRowDropdown = tableBody.querySelector(`tr[role-name="${prevRole}"] [data-day="${prevDay}"]`);
            const nextRowDropdown = tableBody.querySelector(`tr[role-name="${nextRole}"] [data-day="${nextDay}"]`);

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

        // Use progressive numbering for offsite groups (e.g. Vacation and Gill)
        if (currentRow.classList.contains('group-offsite')) {
            // Extracting the number from the roleName
            const currentNumber = parseInt(roleName.match(/\d+/)[0]);
            const nextRow = tableBody.querySelector(`tr[role-name="${rowName} ${currentNumber + 1}"]`);

            // If the current dropdown value is set, enable the next row dropdown for the same day
            if (nextRow && currentValue) {
                const nextDropdown = nextRow.querySelector(`.doctor-dropdown[data-day="${currentDay}"]`);
                if (nextDropdown) nextDropdown.removeAttribute('disabled');
            }
            // If the current dropdown value is set to default, and it's not the first row, disable its dropdown
            else if (nextRow && !currentValue) {
                const nextDropdown = nextRow.querySelector(`.doctor-dropdown[data-day="${currentDay}"]`);
                if (nextDropdown && !nextDropdown.value) nextDropdown.setAttribute('disabled', 'true');
            }
        }

        // Re-enable the previous value for other dropdowns in the same column
        if (prevValue) enableDropdownOption(`doctor-dropdown[data-day="${currentDay}"]`, prevValue);

        // Disable the current value for other dropdowns in the same column
        if (currentValue) disableDropdownOption(`doctor-dropdown[data-day="${currentDay}"]`, currentValue, this);

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

function updateFooterCounts(day = null, currentValue = null, prevValue = null, roleName = null) {
    const days = day ? [day] : ["MON", "TUE", "WED", "THU", "FRI"];

    function calculateRequestedCounts(day) {
        return Array.from(document.querySelectorAll(`tr[group="admin"]  .doctor-dropdown[data-day="${day}"], tr[group="whine-zone"] .doctor-dropdown[data-day="${day}"]`)).filter(dropdown => dropdown.value).length;
    }

    function calculateAssignedCounts(day) {
        return Array.from(document.querySelectorAll(`.doctor-dropdown[data-day="${day}"]`))
            .filter(dropdown => {
                return dropdown.value && !dropdown.closest('tr[group="whine-zone"]') && !dropdown.closest('tr[group="whine-zone"]');
            }).length;
    }

    days.forEach(day => {
        const preassigned = calculateAssignedCounts(day);
        document.querySelector(`[data-count="set"][data-day-total="${day}"]`).textContent = preassigned.toString();

        const requested = calculateRequestedCounts(day);
        document.querySelector(`[data-count="requested"][data-day-total="${day}"]`).textContent = requested.toString();

        const unassigned = STAFF_MEMBERS.length - preassigned;
        document.querySelector(`[data-count="unset"][data-day-total="${day}"]`).textContent = unassigned.toString();

    });

    // Update the Points column if current or previous value is set
    if (currentValue || prevValue) {
        let grandTotalPointsElem = document.querySelector('[data-count="assg0"]');
        let grandTotalPoints = parseInt(grandTotalPointsElem.textContent);

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

function generateJSONFromTable() {

    const shiftRolesData = {};
    const transitionShiftRolesData = {};
    const whineZoneData = {};
    const adminData = [];

    const offsiteData = getOffsiteGroups().reduce((acc, group) => {
        acc[group] = [];
        return acc;
    }, {});

    const unassignedName = WEEKDAYS.reduce((acc, day) => {
        acc[day] = [];
        return acc;
    }, {});

    const rows = Array.from(document.querySelectorAll('.group-content'));
    rows.forEach(row => {
        const rowObj = {};
        const role = row.getAttribute('role-name'); // Get the 'role-name' attribute

        const columns = Array.from(row.querySelectorAll('.doctor-dropdown'));
        WEEKDAYS.forEach((day, index) => {
            rowObj[day] = columns[index].value;
        });

        const group = row.getAttribute('group'); // Get the 'group' attribute
        if (row.classList.contains('group-offsite')) {
            offsiteData[group].push(rowObj);
        } else if (group === 'admin') {
            adminData.push(rowObj);
        } else if (group === 'transition-shift-roles') {
            transitionShiftRolesData[role] = rowObj;
        } else if (group === 'shift-roles') {
            shiftRolesData[role] = rowObj;
        } else if (group === 'whine-zone') {
            whineZoneData[role] = rowObj;

            columns.forEach((column, index) => {
                // if the column is not empty, add the name to the list for that day
                if (column.value) {
                    unassignedName[WEEKDAYS[index]].push(column.value);
                } else {
                    // get all enabled values in that dropdown and add those to the list
                    const enabledValues = Array.from(column.querySelectorAll('option:not([disabled])'))
                        .map(option => option.value)
                        .filter(val => val !== ''); // Filtering out empty strings

                    // Convert the existing array to a Set
                    let uniqueValuesSet = new Set(unassignedName[WEEKDAYS[index]]);

                    // Add the new values to the Set
                    enabledValues.forEach(val => uniqueValuesSet.add(val));

                    // Convert the Set back to an array
                    unassignedName[WEEKDAYS[index]] = [...uniqueValuesSet];
                }
            });
        } else {
            console.error("Error: " + role + " in group " + group + " unknown what data set to add to.");
        }
    });

    return {
        unassignedPerDay: unassignedName,
        preAllocated: {
            transitionShiftRoles: transitionShiftRolesData,
            shiftRoles: shiftRolesData
        },
        requested: {
            whineZone: whineZoneData,
            admin: adminData.reduce((acc, item) => {
                WEEKDAYS.forEach(day => {
                    if (item[day]) {
                        if (!acc[day]) {
                            acc[day] = [];
                        }
                        acc[day].push(item[day]);
                    }
                });
                return acc;
            }, Object.fromEntries(WEEKDAYS.map(day => [day, []])))
        },
        offsite: Object.keys(offsiteData).reduce((acc, groupKey) => {
            const group = offsiteData[groupKey];
            acc[groupKey] = group.reduce((innerAcc, item) => {
                for (const key in item) {
                    if (item[key]) {
                        if (!innerAcc[key]) {
                            innerAcc[key] = [];
                        }
                        innerAcc[key].push(item[key]);
                    }
                }
                return innerAcc;
            }, {});
            return acc;
        }, {})
    };
}

// Download Button Click Handler
// Reference to the dropdown and button
const saveButton = document.getElementById('saveButton');

// Add event listener to the save button
saveButton.addEventListener('click', () => {
    const jsonData = generateJSONFromTable();

    if (!isValidJSON(jsonData)) {
        console.error('JSON is invalid');
        return;
    }

    const jsonContent = JSON.stringify(data, null, 2); // Use 2-space indent for initial formatting
    let mimeType = 'application/json;charset=utf-8;';

    // Prompt the user for a filename
    let filename = prompt("Enter a name for the file:", "schedule.json");

    // Check if filename has been provided and if not, default to "schedule.json"
    if (!filename) {
        filename = "schedule.json";
    } else if (!filename.endsWith(".json")) {
        filename += ".json"; // Append .json if not already present
    }

    const blob = new Blob([jsonContent], {type: mimeType});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
});


// Reference to the file input, label for displaying the filename, and the table
const fileInput = document.getElementById('fileInput');
const fileNameDisplay = document.getElementById('fileNameDisplay');
const table = document.getElementById('scheduleTable');

fileInput.addEventListener('change', function () {
    const file = fileInput.files[0];

    if (file) {
        const reader = new FileReader();

        reader.onload = function (event) {
            try {
                const jsonData = JSON.parse(event.target.result);

                if (isValidJSON(jsonData)) {
                    updateTableWithData(jsonData);
                    fileNameDisplay.textContent = `Selected: ${file.name}`;
                } else {
                    alert('Invalid JSON structure.');
                }
            } catch (e) {
                alert('Error parsing JSON file.');
            }
        };

        reader.onerror = function () {
            alert('Error reading file.');
        };

        reader.readAsText(file);
    }
});

function getOffsiteGroups() {
    const matchingRows = document.querySelectorAll('#scheduleTable tr.group-content.group-offsite');

    let groups = [];

    matchingRows.forEach(row => {
        const groupValue = row.getAttribute('group');
        if (groupValue && !groups.includes(groupValue)) {
            groups.push(groupValue);
        }
    });

    return groups;
}


function isValidJSON(data) {

    // Check if the object has the required properties
    if (!data.hasOwnProperty('unassignedPerDay')
        || !data.hasOwnProperty('preAllocated')
        || !data.hasOwnProperty('requested')
        || !data.hasOwnProperty('offsite')) {
        return false;
    }

    // Validate the values of unassignedPerDay
    for (const day in data.unassignedPerDay) {
        if (!WEEKDAYS.includes(day)) return false; // Found an invalid day (not in the list of weekdays)
        const dayNames = data.unassignedPerDay[day];
        for (const name of dayNames) {
            if (!STAFF_MEMBERS.includes(name)) {
                return false; // Found an invalid name in the unassigned list
            }
        }
    }

    function validateGroupArray(groupData, groupName) {
        for (const day in groupData) {
            if (!WEEKDAYS.includes(day)) {
                console.error(`Day "${day}" is not a valid day in ${groupName}`)
                return false;
            }
            const dayNames = groupData[day];
            for (const name of dayNames) {
                if (!STAFF_MEMBERS.includes(name)) {
                    console.error(`Name "${name}" is not a valid name in ${groupName}`)
                    return false;
                }
            }
        }
        return true;
    }

    function validateGroup(groupData, groupName) {
        function getRolesByGroup(groupName) {
            const matchingRows = document.querySelectorAll(`#scheduleTable tr[group="${groupName}"]`);
            return [...matchingRows].reduce((acc, row) => {
                const roleNameValue = row.getAttribute('role-name');
                if (roleNameValue) {
                    acc.push(roleNameValue);
                }
                return acc;
            }, []);
        }

        const validRoles = getRolesByGroup(groupName);
        for (const role of validRoles) {
            if (!groupData[role]) {
                console.error(`Role "${role}" missing in ${groupName}`);
                return false;
            }
        }

        for (const role in groupData) {
            if (!validRoles.includes(role)) {
                console.error(`Role "${role}" is not a valid role in ${groupName}`);
                return false;
            }
            for (const day in groupData[role]) {
                if (!WEEKDAYS.includes(day)) {
                    console.error(`Day "${day}" is not a valid day in ${groupName}`);
                    return false;
                }
                const name = groupData[role][day];
                if (name !== "" && !STAFF_MEMBERS.includes(name)) {
                    console.error(`Name "${name}" is not a valid name in ${groupName}`);
                    return false;
                }
            }
        }
        return true;
    }

    // Check if the offsite object has the required properties
    const offsiteGroups = getOffsiteGroups();
    for (const site in data.offsite) {
        if (!offsiteGroups.includes(site)) {
            console.error(`Site "${site}" is not a valid offsite group`);
            return false;
        }
        if (!validateGroupArray(data.offsite[site], site)) return false;
    }

    // Check if the preAllocated object has the required properties
    if (!data.preAllocated) return false;

    if (!validateGroup(data.preAllocated.transitionShiftRoles, 'transition-shift-roles')) return false;

    if (!validateGroup(data.preAllocated.shiftRoles, 'shift-roles')) return false;

    // Check if the requested object has the required properties
    if (!data.requested) return false;
    if (!validateGroup(data.requested.whineZone, 'whine-zone')) return false;

    if (!validateGroupArray(data.requested.admin, 'admin')) return false;

    console.log('JSON is valid')
    return true;
}

document.getElementById('clearButton').addEventListener('click', function () {
    const isSure = confirm("Are you sure you want to clear all?");
    if (isSure) {
        console.log('User asked to clear the table')
        clearTable();
    } else console.log('User cancelled clearing the table')
});

function clearTable() {
    const tableBody = document.querySelector("#scheduleTable tbody");

    // 1. Reset the dropdowns to their default value.
    const dropdowns = tableBody.querySelectorAll('select');
    dropdowns.forEach((dropdown) => {
        dropdown.selectedIndex = 0;
    });

    // 2. Enable all values in the dropdowns.
    const dropdownOptions = tableBody.querySelectorAll('select option');
    dropdownOptions.forEach((option) => {
        option.removeAttribute('disabled');
    });

    // 3. Reset the summary counts to 0 based on data-count attribute.
    const countElements = document.querySelectorAll("#staffTable [data-count], #scheduleTable [data-count]");
    countElements.forEach((element) => {
        element.textContent = "0";
    });

    // 4. Disable all offsite dropdown rows that aren't the first in group
    document.querySelectorAll('.group-offsite:not(.first-in-group) .doctor-dropdown').forEach(dropdown => {
        dropdown.disabled = true;
    });
}


function updateTableWithData(data) {
    // Clear the existing rows, or however you wish to handle merging/overwriting
    clearTable();
    const tableBody = document.querySelector("#scheduleTable tbody");

    function setDropdownValue(dropdown, value) {
        const option = [...dropdown.options].find(opt => opt.value === value);
        if (option) {
            option.selected = true;
            dropdown.dispatchEvent(new Event('change', {'bubbles': true}));
        } else {
            console.error(`Option with value "${value}" not found in dropdown`);
        }
    }

    function fillRowsForGroupByDayArrays(groupName, groupData) {
        const rows = tableBody.querySelectorAll(`tr[group="${groupName}"]`);
        for (const day in groupData) {
            let columnIndex = WEEKDAYS.indexOf(day) + 1;
            groupData[day].forEach((role, rowIndex) => {
                if (rows[rowIndex]) {
                    const cell = rows[rowIndex].cells[columnIndex];
                    const dropdown = cell.querySelector('.doctor-dropdown');
                    if (dropdown) {
                        setDropdownValue(dropdown, role);
                    }
                }
            });
        }
    }

    function fillDropdownForRole(roleName, roleData) {
        const row = tableBody.querySelector(`tr[role-name="${roleName}"]`);
        if (!row) {
            console.error(`Row not found for ${roleName}`);
            return;
        }
        for (const day in roleData) {
            const dropdown = row.querySelector(`.doctor-dropdown[data-day="${day}"]`);
            if (dropdown) {
                setDropdownValue(dropdown, roleData[day]);
            } else {
                console.error(`Dropdown not found for ${roleName} on ${day}`)
            }
        }
    }

    function fillRowsForGroup(groupName, groupData) {
        for (const roleName in groupData) {
            fillDropdownForRole(roleName, groupData[roleName]);
        }
    }

    //
    for (const site in data.offsite) {
        fillRowsForGroupByDayArrays(site, data.offsite[site]);
    }

    fillRowsForGroup('whine-zone', data.requested.whineZone);
    fillRowsForGroupByDayArrays('whine-zone', data.requested.admin);
    fillRowsForGroup('whine-zone', data.preAllocated.shiftRoles);
    fillRowsForGroup('whine-zone', data.preAllocated.transitionShiftRoles);
}
