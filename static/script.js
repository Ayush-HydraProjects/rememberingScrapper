 /* script.js */

 // let scrapingActive = {{ (scraping_active)|tojson }};
 // console.log(scrapingActive);

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
            scrapingActive = data.scraping_active;  // ✅ Use server's response
            updateScraperUI();
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
            scrapingActive = data.scraping_active;  // ✅ Use server's response
            updateScraperUI();
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
        })
        .catch(error => {
            console.error("Error fetching scraping status:", error);
        });
}

function updateScraperUI() { // NEW FUNCTION to update UI elements based on scrapingActive
    if (scrapingActive) {
        document.getElementById("startButton").disabled = true;
        document.getElementById("stopButton").disabled = false;
        console.log('if part:', scrapingActive);
        document.getElementById("scrapingStatus").textContent = "Scraping running...";
    } else {
        document.getElementById("startButton").disabled = false;
        document.getElementById("stopButton").disabled = true;
        console.log('else part: ', scrapingActive);
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
    setInterval(updateScrapingStatusDisplay, 5000);

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
    document.getElementById("obituaryList").classList.add("hidden");
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
            document.getElementById("obituaryList").classList.remove("hidden");

            const obituaryList = document.querySelector("#obituaryList tbody");
            obituaryList.innerHTML = ""; // Clear existing entries

            if (data.length === 0) {
                document.getElementById("noNewEntries").classList.remove("hidden"); // Show no entries message
            } else {
                document.getElementById("noNewEntries").classList.add("hidden"); // Hide no entries message
                data.forEach(obituary => {
                    const row = `
                        <tr class="hover:bg-gray-100 transition">
                            <td class="border px-4 py-2">${obituary.first_name || "N/A"}</td>
                            <td class="border px-4 py-2">${obituary.last_name || "N/A"}</td>
                            <td class="border px-4 py-2">${obituary.city || "N/A"}</td>
                            <td class="border px-4 py-2">${obituary.province || "N/A"}</td>
                            <td class="border px-4 py-2">${obituary.birth_date || "N/A"}</td>
                            <td class="border px-4 py-2">${obituary.death_date || "N/A"}</td>
                            <td class="border px-4 py-2">
                                <a href="${obituary.obituary_url}" target="_blank" class="text-blue-500 hover:underline">🔗 View</a>
                            </td>
                        </tr>
                    `;
                    obituaryList.innerHTML += row;
                });
            }
        })
        .catch(error => {
            console.error("Search error:", error);
            alert("Error fetching search results.");
            // Hide loading spinner on error
            document.getElementById("loading-spinner").classList.add("hidden");
            document.getElementById("obituaryList").classList.remove("hidden");
        });
}



function refreshObituaries() {
    document.getElementById('loading-spinner').classList.remove('hidden');
    document.getElementById('obituaryList').classList.add('hidden');
    document.getElementById('noNewEntries').classList.add('hidden');


    fetch('/get_obituaries')
        .then(response => response.json())
        .then(data => {
            console.log("Obituary data received:", data)
            // Hide loading spinner
            document.getElementById('loading-spinner').classList.add('hidden');
            document.getElementById('obituaryList').classList.remove('hidden');
            const obituaryList = document.querySelector("#obituaryList tbody");
            obituaryList.innerHTML = "";


            if (data.length === 0) {
                document.getElementById('noNewEntries').classList.remove('hidden');// Show no entries message
            }
            else {
                document.getElementById('noNewEntries').classList.add('hidden');//// Hide no entries message
                data.forEach(obituary => {
                    const row = `
                        <tr class="hover:bg-gray-100 transition">
                            <td class="border px-4 py-2">${obituary.first_name || 'N/A'}</td>
                            <td class="border px-4 py-2">${obituary.last_name || 'N/A'}</td>
                            <td class="border px-4 py-2">${obituary.city || 'N/A'}</td>
                            <td class="border px-4 py-2">${obituary.province || 'N/A'}</td>
                            <td class="border px-4 py-2">${obituary.birth_date || 'N/A'}</td>
                            <td class="border px-4 py-2">${obituary.death_date || 'N/A'}</td>
                            <td class="border px-4 py-2">
                                <a href="${obituary.obituary_url}" target="_blank" class="text-blue-500 hover:underline">🔗 View</a>
                            </td>
                        </tr>
                    `;
                    obituaryList.innerHTML += row;
                });
            }
        })
        .catch(error => {
            console.error("Error refreshing obituaries:", error)
            document.getElementById('loading-spinner').classList.add('hidden');
            document.getElementById('obituaryList').classList.remove('hidden');
        });
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