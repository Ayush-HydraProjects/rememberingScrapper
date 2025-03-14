/* script.js */

const entriesFetchedSpan = document.getElementById("entriesFetched");


function updateEntriesFetchedDisplay(value) {
    entriesFetchedSpan.textContent = value;
}


function startScraping() {
    if (scrapingActive) { // Now checking direct scrapingActive value
        alert("Scraping is already running.");
        return;
    }

    fetch('/start_scrape', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            alert(data.message);
            scrapingActive = data.scraping_active;  // Use server's response
            updateScraperUI();
            if (data.last_scrape_time) { // Update last scrape time after start
                updateLastScrapeTimeDisplay(data.last_scrape_time);
            }
        })
        .catch(error => {
            console.error("Error starting scraping:", error);
            alert("Error starting scraping. Check console for details.");
        });
}

function stopScraping() {
    if (!scrapingActive) { // Now checking direct scrapingActive value
        alert("Scraping is not currently running.");
        return;
    }

    fetch('/stop_scrape', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            alert(data.message);
            scrapingActive = data.scraping_active;  // Use server's response
            updateScraperUI();
            if (data.last_scrape_time) { // Update last scrape time after stop
                updateLastScrapeTimeDisplay(data.last_scrape_time);
            }
        })
        .catch(error => {
            console.error("Error stopping scraping:", error);
            alert("Error stopping scraping. Check console for details.");
        });
}

function updateScrapingStatusDisplay() {
    fetch('/scrape_status')
        .then(response => response.json())
        .then(data => {
            scrapingActive = data.scraping_active; // Update scrapingActive from server status
            updateScraperUI(); // Call updateUI function
            if (data.last_scrape_time) { // Update last scrape time on status update
                updateLastScrapeTimeDisplay(data.last_scrape_time);
            }
        })
        .catch(error => {
            console.error("Error fetching scraping status:", error);
        });
}

function updateScraperUI() { // NEW FUNCTION to update UI elements based on scrapingActive
    if (scrapingActive) {
        document.getElementById("startButton").disabled = true;
        document.getElementById("stopButton").disabled = false;
        document.getElementById("scrapingStatus").textContent = "Scraping running...";
    } else {
        document.getElementById("startButton").disabled = false;
        document.getElementById("stopButton").disabled = true;
        document.getElementById("scrapingStatus").textContent = "Not running";
    }
}


function clearFilters() {
    document.getElementById("firstNameFilter").value = '';
    document.getElementById("lastNameFilter").value = '';
    document.getElementById("cityFilter").value = '';
    document.getElementById("provinceFilter").value = '';
    refreshObituaries();
}


document.addEventListener('DOMContentLoaded', function () {
    refreshObituaries();
    // updateDashboardSummary(); // If you still use this
    updateScrapingStatusDisplay(); // Initial status update on load
    setInterval(updateScrapingStatusDisplay, 20000);

    document.getElementById("filterForm").addEventListener("submit", function (event) {
        event.preventDefault();
        applyFilters();
    });
});


function applyFilters() {
    // Retrieve filter input values
    const firstName = document.getElementById("firstNameFilter").value.trim();
    const lastName = document.getElementById("lastNameFilter").value.trim();
    const city = document.getElementById("cityFilter").value.trim();
    const province = document.getElementById("provinceFilter").value.trim();

    // Show loading spinner
    document.getElementById("loading-spinner").classList.remove("hidden");
    document.getElementById("obituaryAccordionContainer").innerHTML = ""; // Clear accordion container instead of obituaryList
    document.getElementById("noNewEntries").classList.add("hidden");

    // Build query parameters dynamically
    const params = new URLSearchParams();
    if (firstName) params.append("firstName", firstName);
    if (lastName) params.append("lastName", lastName);
    if (city) params.append("city", city);
    if (province) params.append("province", province);


    fetch(`/search_obituaries?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            // Hide loading spinner
            document.getElementById("loading-spinner").classList.add("hidden");

            if (data.length === 0) {
                document.getElementById("noNewEntries").classList.remove("hidden"); // Show no entries message
            } else {
                document.getElementById("noNewEntries").classList.add("hidden"); // Hide no entries message
                renderYearAccordion(data); // Render accordion with filtered data, now YEAR accordion
            }
        })
        .catch(error => {
            console.error("Search error:", error);
            alert("Error fetching search results.");
            // Hide loading spinner on error
            document.getElementById("loading-spinner").classList.add("hidden");
        });
}


function refreshObituaries() { // Modified refreshObituaries to use year accordion
    document.getElementById('loading-spinner').classList.remove('hidden');
    document.getElementById('obituaryAccordionContainer').innerHTML = ""; // Clear previous accordion
    document.getElementById('noNewEntries').classList.add('hidden');

    fetch('/get_obituaries')
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').classList.add('hidden');

            if (data.length === 0) {
                document.getElementById('noNewEntries').classList.remove('hidden');
            } else {
                document.getElementById('noNewEntries').classList.add('hidden');
                renderYearAccordion(data); // Call function to render YEAR accordion
            }
        })
        .catch(error => {
            console.error("Error refreshing obituaries:", error);
            document.getElementById('loading-spinner').classList.add('hidden');
        });
}

function renderYearAccordion(obituaries) { // Renamed function to render YEAR accordion
    const accordionContainer = document.getElementById('obituaryAccordionContainer');
    const yearGroups = groupObituariesByYear(obituaries); // Group data by year (new function below)
    const yearOrder = ["2025", "2024", "2023", "2022", "Before 2022"]; // Define year order
    let firstAccordionSection = true; // Flag to track the first accordion

    yearOrder.forEach(year => { // Use yearOrder to control the order of accordion sections
        if (yearGroups.hasOwnProperty(year)) {
            const yearObituaries = yearGroups[year];
            if (yearObituaries.length > 0) { // Only create accordion if there are obituaries for the year
                const yearAccordion = createYearAccordionSection(year, yearObituaries, firstAccordionSection); // Create year accordion section (new function below), pass firstAccordionSection
                accordionContainer.appendChild(yearAccordion);
                if (firstAccordionSection) {
                    firstAccordionSection = false; // Set flag to false after creating the first section
                }
            }
        }
    });
}


function groupObituariesByYear(obituaries) { // NEW function to group by YEAR
    const yearGroups = { // Initialize with all year groups to maintain order and include empty groups
        "2025": [],
        "2024": [],
        "2023": [],
        "2022": [],
        "Before 2022": []
    };

    obituaries.forEach(obituary => {
        let publicationYear = 'Unknown Year'; // Default year if extraction fails
        if (obituary.publication_date) {
            const year = new Date(obituary.publication_date).getFullYear();
            if (!isNaN(year)) { // Check if year is a valid number
                publicationYear = String(year); // Convert year to string for grouping
            } else {
                publicationYear = 'Unknown Year';
            }
        }

        if (publicationYear === '2025') yearGroups["2025"].push(obituary);
        else if (publicationYear === '2024') yearGroups["2024"].push(obituary);
        else if (publicationYear === '2023') yearGroups["2023"].push(obituary);
        else if (publicationYear === '2022') yearGroups["2022"].push(obituary);
        else if (publicationYear !== 'Unknown Year' && parseInt(publicationYear) < 2022) yearGroups["Before 2022"].push(obituary); // Group years before 2022
        // else yearGroups["Unknown Year"].push(obituary); // Optional: Handle 'Unknown Year' if needed, or just ignore
    });
    return yearGroups;
}


function createYearAccordionSection(year, obituaries, isFirstSection) { // NEW function to create YEAR accordion section, added isFirstSection parameter
    const yearSection = document.createElement('div');
    yearSection.classList.add('accordion-section'); // You can keep 'accordion-section' class for styling

    const yearHeading = document.createElement('button');
    yearHeading.classList.add('accordion-button'); // Keep 'accordion-button' class for styling
    yearHeading.textContent = year; // Set the year as the button text
    yearHeading.addEventListener('click', () => { // Accordion toggle functionality (same as before)
        yearContent.classList.toggle('hidden');
        yearHeading.classList.toggle('active'); // Toggle active class on header
    });
    yearSection.appendChild(yearHeading);

    const yearContent = document.createElement('div');
    yearContent.classList.add('accordion-content'); // Keep 'accordion-content' class
    if (!isFirstSection) { // Add 'hidden' class only if it's NOT the first section
        yearContent.classList.add('hidden');
    }

    // Create the table
    const obituaryTable = document.createElement('table');
    obituaryTable.classList.add('obituary-table'); // Keep 'obituary-table' class for table styling

    // Create table header (<thead>)
    const tableHeader = document.createElement('thead');
    tableHeader.innerHTML = `
        <tr>
            <th class="border px-4 py-2">First Name</th>
            <th class="border px-4 py-2">Last Name</th>
            <th class="border px-4 py-2">City</th>  <!-- Keep City and Province if you want to display them -->
            <th class="border px-4 py-2">Province</th> <!-- Keep City and Province if you want to display them -->
            <th class="border px-4 py-2">Birth Date</th>
            <th class="border px-4 py-2">Death Date</th>
            <th class="border px-4 py-2">View</th>
        </tr>
    `;
    obituaryTable.appendChild(tableHeader);

     // Create a paragraph for "No obituaries in this year" if obituaries array is empty
    if (!obituaries || obituaries.length === 0) {
        const noObituariesPara = document.createElement('p');
        noObituariesPara.textContent = "No obituaries in this year.";
        yearContent.appendChild(noObituariesPara);
        yearSection.appendChild(yearContent);
        return yearSection; // Return early if no obituaries
    }


    // Create table body (<tbody>)
    const tableBody = document.createElement('tbody');
    obituaries.forEach(obituary => {
        const row = document.createElement('tr');
        row.classList.add("hover:bg-gray-100", "transition"); // Optional row styling
        row.innerHTML = `
            <td class="border px-4 py-2">${obituary.first_name || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.last_name || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.city || 'N/A'}</td> <!-- Keep City and Province if you want to display them -->
            <td class="border px-4 py-2">${obituary.province || 'N/A'}</td> <!-- Keep City and Province if you want to display them -->
            <td class="border px-4 py-2">${obituary.birth_date || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.death_date || 'N/A'}</td>
            <td class="border px-4 py-2">
                <a href="/obituary/${obituary.id}" class="text-blue-500 hover:underline">🔗 View</a>
            </td>
        `;
        tableBody.appendChild(row);
    });
    obituaryTable.appendChild(tableBody);
    yearContent.appendChild(obituaryTable); // Append the table to the content div
    yearSection.appendChild(yearContent);

    if (isFirstSection) { // If it's the first section, set max-height to open it
        yearHeading.classList.add('active'); // Add active class to the first header
        // yearContent.style.maxHeight = yearContent.scrollHeight + "px"; // Expand the first content
    }


    return yearSection;
}

function updateLastScrapeTimeDisplay(timeString) { // NEW function to update last scrape time
    const lastScrapeTimeSpan = document.getElementById("lastScrapeTimeDisplay");
    if (timeString) {
        const formattedTime = new Date(timeString).toLocaleString(); // Format the ISO string to local date and time
        lastScrapeTimeSpan.textContent = formattedTime;
    } else {
        lastScrapeTimeSpan.textContent = "Never"; // Or "N/A", or leave it blank, as you prefer for no time yet
    }
}