 /* script.js */

let scrapingActive = false;
const entriesFetchedSpan = document.getElementById("entriesFetched");


function updateEntriesFetchedDisplay(value) {
    entriesFetchedSpan.textContent = value;
}


function startScraping() {
    if (scrapingActive) {
        alert("Scraping is already running.");
        return;
    }


    fetch('/scrape', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            alert(data);
            scrapingActive = false;
            document.getElementById("stopButton").disabled = true;
            document.getElementById("startButton").disabled = false;
            document.getElementById("scrapingStatus").textContent = "Scraping finished.";
            refreshObituaries();
            updateDashboardSummary();
        })
        .catch(error => {
            console.error("Error during scraping:", error);
            alert("An error occurred during scraping. Check the console for details.");
            scrapingActive = false;
            document.getElementById("stopButton").disabled = true;
            document.getElementById("startButton").disabled = false;
            document.getElementById("scrapingStatus").textContent = "Scraping encountered an error.";
        });
}

function stopScraping() {
    if (!scrapingActive) {
        alert("Scraping is not currently running.");
        return;
    }

    scrapingActive = false;
    document.getElementById("stopButton").disabled = true;
    document.getElementById("startButton").disabled = false;
    document.getElementById("scrapingStatus").textContent = "Stopping Scraping... (This is a mock function)";
}

function clearFilters() {
    document.getElementById("firstNameFilter").value = '';
    document.getElementById("lastNameFilter").value = '';
    document.getElementById("cityFilter").value = '';
    document.getElementById("provinceFilter").value = '';
    // document.getElementById("birthDateStart").value = '';
    // document.getElementById("birthDateEnd").value = '';
    // document.getElementById("deathDateStart").value = '';
    // document.getElementById("deathDateEnd").value = '';
    refreshObituaries(); // Refresh to show all obituaries
}


document.addEventListener('DOMContentLoaded', function() {
    refreshObituaries(); // Load obituaries on dashboard load
    updateDashboardSummary(); // Initial summary update on load

    document.getElementById("filterForm").addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent default form submission
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

function updateDashboardSummary() {
    fetch('/dashboard_summary')
        .then(response => response.json())
        .then(data => {
            document.getElementById('alumniCount').textContent = data.total_alumni;
            document.getElementById('entriesFetched').textContent = data.total_obituaries;
            document.getElementById('citiesFetched').textContent = data.total_cities;
        })
        .catch(error => console.error("Error fetching dashboard summary:", error));
}