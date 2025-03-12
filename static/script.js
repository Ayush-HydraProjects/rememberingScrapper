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
    // const birthDateStart = document.getElementById("birthDateStart").value.trim();
    // const birthDateEnd = document.getElementById("birthDateEnd").value.trim();
    // const deathDateStart = document.getElementById("deathDateStart").value.trim();
    // const deathDateEnd = document.getElementById("deathDateEnd").value.trim();

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
    // if (birthDateStart) params.append("birthDateStart", birthDateStart);
    // if (birthDateEnd) params.append("birthDateEnd", birthDateEnd);
    // if (deathDateStart) params.append("deathDateStart", deathDateStart);
    // if (deathDateEnd) params.append("deathDateEnd", deathDateEnd);


    fetch(`/search_obituaries?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            // Hide loading spinner
            document.getElementById("loading-spinner").classList.add("hidden");
            // document.getElementById("obituaryList").classList.remove("hidden"); // No need to show/hide obituaryList anymore

            // const obituaryList = document.querySelector("#obituaryList tbody"); // No longer needed
            // obituaryList.innerHTML = ""; // Clear existing entries // No longer needed

            if (data.length === 0) {
                document.getElementById("noNewEntries").classList.remove("hidden"); // Show no entries message
            } else {
                document.getElementById("noNewEntries").classList.add("hidden"); // Hide no entries message
                renderObituaryAccordion(data); // Render accordion with filtered data
            }
        })
        .catch(error => {
            console.error("Search error:", error);
            alert("Error fetching search results.");
            // Hide loading spinner on error
            document.getElementById("loading-spinner").classList.add("hidden");
            // document.getElementById("obituaryList").classList.remove("hidden"); // No need to show/hide obituaryList anymore
        });
}


//
// function refreshObituaries() {
//     document.getElementById('loading-spinner').classList.remove('hidden');
//     document.getElementById('obituaryList').classList.add('hidden');
//     document.getElementById('noNewEntries').classList.add('hidden');
//
//
//     fetch('/get_obituaries')
//         .then(response => response.json())
//         .then(data => {
//             console.log("Obituary data received:", data)
//             // Hide loading spinner
//             document.getElementById('loading-spinner').classList.add('hidden');
//             document.getElementById('obituaryList').classList.remove('hidden');
//             const obituaryList = document.querySelector("#obituaryList tbody");
//             obituaryList.innerHTML = "";
//
//
//             if (data.length === 0) {
//                 document.getElementById('noNewEntries').classList.remove('hidden');// Show no entries message
//             }
//             else {
//                 document.getElementById('noNewEntries').classList.add('hidden');//// Hide no entries message
//                 console.log(data)
//                 data.forEach(obituary => {
//                     const row = `
//                         <tr class="hover:bg-gray-100 transition">
//                             <td class="border px-4 py-2">${obituary.first_name || 'N/A'}</td>
//                             <td class="border px-4 py-2">${obituary.last_name || 'N/A'}</td>
//                             <td class="border px-4 py-2">${obituary.city || 'N/A'}</td>
//                             <td class="border px-4 py-2">${obituary.province || 'N/A'}</td>
//                             <td class="border px-4 py-2">${obituary.birth_date || 'N/A'}</td>
//                             <td class="border px-4 py-2">${obituary.death_date || 'N/A'}</td>
//                             <td class="border px-4 py-2">
//                                 <a href="/obituary/${obituary.id}" class="text-blue-500 hover:underline">🔗 View</a>
//                             </td>
//                         </tr>
//                     `;
//                     obituaryList.innerHTML += row;
//                 });
//             }
//         })
//         .catch(error => {
//             console.error("Error refreshing obituaries:", error)
//             document.getElementById('loading-spinner').classList.add('hidden');
//             document.getElementById('obituaryList').classList.remove('hidden');
//         });
// }

 function refreshObituaries() {
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
                renderObituaryAccordion(data); // Call function to render accordion
            }
        })
        .catch(error => {
            console.error("Error refreshing obituaries:", error);
            document.getElementById('loading-spinner').classList.add('hidden');
        });
}

function renderObituaryAccordion(obituaries) {
    const accordionContainer = document.getElementById('obituaryAccordionContainer');
    const cityGroups = groupObituariesByCity(obituaries); // Group data by city

    for (const city in cityGroups) {
        if (cityGroups.hasOwnProperty(city)) {
            const cityObituaries = cityGroups[city];
            const cityAccordion = createCityAccordionSection(city, cityObituaries);
            accordionContainer.appendChild(cityAccordion);
        }
    }
}


function groupObituariesByCity(obituaries) {
    const cityGroups = {};
    obituaries.forEach(obituary => {
        const city = obituary.city || 'Unknown City'; // Use 'Unknown City' if city is null/undefined
        if (!cityGroups[city]) {
            cityGroups[city] = [];
        }
        cityGroups[city].push(obituary);
    });
    return cityGroups;
}


function createCityAccordionSection(city, obituaries) {
    const citySection = document.createElement('div');
    citySection.classList.add('accordion-section');

    const cityHeading = document.createElement('button');
    cityHeading.classList.add('accordion-button');
    cityHeading.textContent = city;
    cityHeading.addEventListener('click', () => {
        cityContent.classList.toggle('hidden');
    });
    citySection.appendChild(cityHeading);

    const cityContent = document.createElement('div');
    cityContent.classList.add('accordion-content', 'hidden');

    // Create the table
    const obituaryTable = document.createElement('table');
    obituaryTable.classList.add('obituary-table'); // Add class for table styling

    // Create table header (<thead>)
    const tableHeader = document.createElement('thead');
    tableHeader.innerHTML = `
        <tr>
            <th class="border px-4 py-2">First Name</th>
            <th class="border px-4 py-2">Last Name</th>
            <th class="border px-4 py-2">City</th>
            <th class="border px-4 py-2">Province</th>
            <th class="border px-4 py-2">Birth Date</th>
            <th class="border px-4 py-2">Death Date</th>
            <th class="border px-4 py-2">View</th>
        </tr>
    `;
    obituaryTable.appendChild(tableHeader);

    // Create table body (<tbody>)
    const tableBody = document.createElement('tbody');
    obituaries.forEach(obituary => {
        const row = document.createElement('tr');
        row.classList.add("hover:bg-gray-100", "transition"); // Optional row styling
        row.innerHTML = `
            <td class="border px-4 py-2">${obituary.first_name || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.last_name || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.city || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.province || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.birth_date || 'N/A'}</td>
            <td class="border px-4 py-2">${obituary.death_date || 'N/A'}</td>
            <td class="border px-4 py-2">
                <a href="/obituary/${obituary.id}" class="text-blue-500 hover:underline">🔗 View</a>
            </td>
        `;
        tableBody.appendChild(row);
    });
    obituaryTable.appendChild(tableBody);
    cityContent.appendChild(obituaryTable); // Append the table to the content div
    citySection.appendChild(cityContent);

    return citySection;
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

// function updateDashboardSummary() {
//     fetch('/dashboard_summary')
//         .then(response => response.json())
//         .then(data => {
//             document.getElementById('alumniCount').textContent = data.total_alumni;
//             document.getElementById('entriesFetched').textContent = data.total_obituaries;
//             document.getElementById('citiesFetched').textContent = data.total_cities;
//         })
//         .catch(error => console.error("Error fetching dashboard summary:", error));
// }