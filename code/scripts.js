// This function fetches the CSV and populates the table
function fetchCSVAndPopulate() {
    fetch('../data/staff.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').slice(1); // Skip header row
            const tableBody = document.querySelector("#staffTable tbody");

            rows.forEach(row => {
                const columns = row.split(',');
                const tr = document.createElement('tr');

                // Create name column
                const nameTD = document.createElement('td');
                nameTD.textContent = columns[0];
                nameTD.classList.add('bold');  // Apply bold class to name
                tr.appendChild(nameTD);

                // Create cardiac column
                const cardiacTD = document.createElement('td');
                cardiacTD.textContent = columns[1] === "TRUE" ? "Yes" : "No";
                if (cardiacTD.textContent === "No") {
                    cardiacTD.classList.add('muted');  // Apply muted class if "No"
                } else {
                    cardiacTD.classList.add('cardiac');  // Apply bold class if "Yes"
                }
                tr.appendChild(cardiacTD);

                // Create in charge column
                const inChargeTD = document.createElement('td');
                inChargeTD.textContent = columns[2].trim() === "TRUE" ? "Yes" : "No";
                if (inChargeTD.textContent === "No") {
                    inChargeTD.classList.add('muted');  // Apply muted class if "No"
                } else {
                    inChargeTD.classList.add('charge');  // Apply bold class if "Yes"
                }
                tr.appendChild(inChargeTD);

                tableBody.appendChild(tr);
            });

            // Update the counts
            updateCounts();
        });
}

// Call the function on page load
document.addEventListener('DOMContentLoaded', fetchCSVAndPopulate);


// On click of the table header, sort the table
let sortOrder = 'asc';  // This is used to toggle between ascending and descending order

function sortTable(columnIndex) {
    const table = document.getElementById('staffTable');
    const rows = Array.from(table.tBodies[0].rows);  // Convert rows to an array for easy sorting

    // Determine the sorting order
    const orderMultiplier = sortOrder === 'asc' ? 1 : -1;

    // Sort the rows based on the content of the specified column
    const sortedRows = rows.sort((a, b) => {
        const cellA = a.cells[columnIndex].textContent.trim().toLowerCase();
        const cellB = b.cells[columnIndex].textContent.trim().toLowerCase();

        if (cellA < cellB) return -1 * orderMultiplier;
        if (cellA > cellB) return 1 * orderMultiplier;
        return 0;
    });

    // Clear the current rows and add the sorted rows
    table.tBodies[0].innerHTML = '';
    table.tBodies[0].append(...sortedRows);

    // Toggle the sort order for the next click
    sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
}

// Calculate and display the counts
function updateCounts() {
    const staffTable = document.getElementById('staffTable');

    const nameCount = staffTable.tBodies[0].rows.length;
    const cardiacYesCount = Array.from(staffTable.tBodies[0].rows).filter(row => row.cells[1].textContent.trim() === "Yes").length;
    const chargeYesCount = Array.from(staffTable.tBodies[0].rows).filter(row => row.cells[2].textContent.trim() === "Yes").length;

    document.getElementById("nameCount").textContent = nameCount;
    document.getElementById("cardiacCount").textContent = cardiacYesCount;
    document.getElementById("chargeCount").textContent = chargeYesCount;
}

// Create dropdown options for the table
// Fetch the CSV data
fetch('../data/staff.csv')
    .then(response => response.text())
    .then(data => {
        const lines = data.trim().split("\n");
        const doctorNames = [];

        // Skip the header line and process the rest
        for (let i = 1; i < lines.length; i++) {
            const columns = lines[i].split(",");
            doctorNames.push(columns[0]);
        }

        populateDropdowns(doctorNames);
    });

function populateDropdowns(doctorNames) {
    // Find all dropdowns
    const dropdowns = document.querySelectorAll('.doctor-dropdown');

    dropdowns.forEach(dropdown => {
        // Add an empty default option
        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "";
        dropdown.appendChild(defaultOption);

        // Add the doctor names as options
        doctorNames.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            dropdown.appendChild(option);
        });
    });
}

document.querySelectorAll('.doctor-dropdown').forEach(dropdown => {
    let prevValue = dropdown.value; // Store the initial value

    // When the dropdown value changes, update the table by disabling the selected option in other dropdowns
    dropdown.addEventListener('change', function () {
        const currentValue = this.value;
        let columnClass;

        // Identify the column based on class suffix
        if (this.classList.contains('doctor-dropdown-mon')) {
            columnClass = 'doctor-dropdown-mon';
        } else if (this.classList.contains('doctor-dropdown-tue')) {
            columnClass = 'doctor-dropdown-tue';
        } else if (this.classList.contains('doctor-dropdown-wed')) {
            columnClass = 'doctor-dropdown-wed';
        } else if (this.classList.contains('doctor-dropdown-thu')) {
            columnClass = 'doctor-dropdown-thu';
        } else if (this.classList.contains('doctor-dropdown-fri')) {
            columnClass = 'doctor-dropdown-fri';
        }

        // Re-enable the previous value for other dropdowns in the same column
        if (prevValue) {
            document.querySelectorAll(`.${columnClass}`).forEach(innerDropdown => {
                const option = innerDropdown.querySelector(`option[value="${prevValue}"]`);
                if (option) {
                    option.disabled = false;
                }
            });
        }

        // If a new value is selected, disable it for other dropdowns in the same column
        if (currentValue) {
            document.querySelectorAll(`.${columnClass}`).forEach(innerDropdown => {
                if (innerDropdown !== this) {
                    const option = innerDropdown.querySelector(`option[value="${currentValue}"]`);
                    if (option) {
                        option.disabled = true;
                    }
                }
            });
        }

        prevValue = currentValue;


    });
});

