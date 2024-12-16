document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing Chart...');
    let currentChart = null;

    // Add this conversion function near the top of the file
    function convertEthToMYR(ethAmount) {
        // Using a fixed rate for example - you might want to fetch real-time rates
        const ethToMYRRate = 14000; // 1 ETH = RM 14,000 (example rate)
        return {
            myr: ethAmount * ethToMYRRate,
            eth: ethAmount
        };
    }

    // Function to get formatted date range for x-axis
    function getDateRange(period) {
        const today = new Date();
        const dates = [];
        let startDate;

        switch(period) {
            case 'daily':
                // Get last 7 days including today
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 6); // Start from 6 days ago
                while (startDate <= today) {
                    dates.push(new Date(startDate));
                    startDate.setDate(startDate.getDate() + 1);
                }
                break;
            
            case 'weekly':
                // Get last 4 weeks including current week
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 21); // Start from 3 weeks ago
                while (startDate <= today) {
                    dates.push(new Date(startDate));
                    startDate.setDate(startDate.getDate() + 7);
                }
                break;
            
            case 'monthly':
                // Get last 6 months including current month
                startDate = new Date(today);
                startDate.setMonth(today.getMonth() - 5); // Start from 5 months ago
                startDate.setDate(1); // Start from first day of month
                while (startDate <= today) {
                    dates.push(new Date(startDate));
                    startDate.setMonth(startDate.getMonth() + 1);
                }
                break;
        }
        return dates;
    }

    // Function to format date labels
    function formatDateLabel(date, period) {
        switch(period) {
            case 'daily':
                return date.toLocaleDateString('en-US', {
                    weekday: 'short', // Show day name
                    month: 'short',
                    day: 'numeric'
                });
            case 'weekly':
                const weekEnd = new Date(date);
                weekEnd.setDate(date.getDate() + 6);
                return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
            case 'monthly':
                return date.toLocaleDateString('en-US', {
                    month: 'short',
                    year: 'numeric'
                });
        }
    }

    // Function to group data by time period
    function groupDataByPeriod(data, period) {
        console.log('Raw data received:', data); // Debug log

        const dateRange = getDateRange(period);
        const groupedData = {};
        
        // Initialize all dates with 0
        dateRange.forEach(date => {
            const key = formatDateLabel(date, period);
            groupedData[key] = 0;
        });

        // Group the actual data
        data.forEach(sale => {
            try {
                if (!sale.OrderDate || !sale.DailySales) {
                    console.warn('Invalid sale data:', sale);
                    return;
                }

                const saleDate = new Date(sale.OrderDate);
                if (isNaN(saleDate.getTime())) {
                    console.warn('Invalid date:', sale.OrderDate);
                    return;
                }

                let key;
                switch(period) {
                    case 'daily':
                        key = saleDate.toLocaleDateString('en-US', { 
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric'
                        });
                        break;
                    case 'weekly':
                        // Get the Monday of the week
                        const day = saleDate.getDay();
                        const diff = saleDate.getDate() - day + (day === 0 ? -6 : 1);
                        const monday = new Date(saleDate);
                        monday.setDate(diff);
                        const sunday = new Date(monday);
                        sunday.setDate(monday.getDate() + 6);
                        key = `${monday.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric'
                        })} - ${sunday.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric'
                        })}`;
                        break;
                    case 'monthly':
                        key = saleDate.toLocaleDateString('en-US', { 
                            month: 'short',
                            year: 'numeric'
                        });
                        break;
                }

                const saleAmount = convertEthToMYR(parseFloat(sale.DailySales));
                if (!isNaN(saleAmount.myr)) {
                    if (key in groupedData) {
                        groupedData[key] += saleAmount.myr;
                    } else {
                        groupedData[key] = saleAmount.myr;
                    }
                    console.log(`Added RM ${saleAmount.myr.toFixed(2)} (${saleAmount.eth.toFixed(4)} ETH) to ${key}`);
                }
            } catch (error) {
                console.error('Error processing sale:', error, sale);
            }
        });

        console.log('Grouped data:', groupedData); // Debug log

        return {
            dates: Object.keys(groupedData),
            sales: Object.values(groupedData)
        };
    }

    // Function to create/update chart
    function updateChart(period = 'weekly') {
        try {
            // Validate period
            const validPeriods = ['daily', 'weekly', 'monthly'];
            if (!period || !validPeriods.includes(period)) {
                console.warn('Invalid period provided, defaulting to weekly');
                period = 'weekly';
            }

            const chartElement = document.getElementById('salesChart');
            if (!chartElement) {
                throw new Error('Chart element not found');
            }

            const dailySalesStr = chartElement.getAttribute('data-sales');
            if (!dailySalesStr) {
                throw new Error('No sales data found');
            }

            let dailySales;
            try {
                dailySales = JSON.parse(dailySalesStr);
            } catch (e) {
                throw new Error('Invalid sales data format');
            }

            if (!Array.isArray(dailySales)) {
                throw new Error('Sales data must be an array');
            }

            const chartData = groupDataByPeriod(dailySales, period);
            const ctx = chartElement.getContext('2d');
            
            if (currentChart) {
                currentChart.destroy();
            }

            // Create new chart with modified configuration
            currentChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'Sales (RM)',
                        data: chartData.sales,
                        borderColor: '#00a8ff',
                        backgroundColor: 'rgba(0, 168, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#00a8ff',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#000',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: `${period.charAt(0).toUpperCase() + period.slice(1)} Sales Report`,
                            color: '#000',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: 20
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            titleFont: {
                                size: 14,
                                weight: 'bold'
                            },
                            callbacks: {
                                title: function(tooltipItems) {
                                    const item = tooltipItems[0];
                                    if (period === 'weekly') {
                                        return `Week of ${item.label}`;
                                    }
                                    return item.label;
                                },
                                label: function(context) {
                                    return `Sales: RM ${context.parsed.y.toLocaleString('en-MY', {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    })}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)',
                                drawBorder: true,
                                borderColor: 'rgba(0, 0, 0, 0.3)'
                            },
                            border: {
                                display: true,
                                color: 'rgba(0, 0, 0, 0.3)'
                            },
                            title: {
                                display: true,
                                text: 'Sales Amount (RM)',
                                color: '#000',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                },
                                padding: {
                                    bottom: 10
                                }
                            },
                            ticks: {
                                color: '#000',
                                font: {
                                    size: 12
                                },
                                padding: 10,
                                callback: function(value) {
                                    return 'RM ' + value.toLocaleString('en-MY', {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    });
                                }
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)',
                                drawBorder: true,
                                borderColor: 'rgba(0, 0, 0, 0.3)'
                            },
                            border: {
                                display: true,
                                color: 'rgba(0, 0, 0, 0.3)'
                            },
                            title: {
                                display: true,
                                text: period === 'weekly' ? 'Week Period' : 
                                      period === 'daily' ? 'Date' : 'Month',
                                color: '#000',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                },
                                padding: {
                                    top: 10
                                }
                            },
                            ticks: {
                                color: '#000',
                                font: {
                                    size: 12
                                },
                                padding: 10,
                                maxRotation: 45,
                                minRotation: 45
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    elements: {
                        line: {
                            tension: 0.4
                        }
                    }
                }
            });

            console.log(`Chart created successfully for ${period} period`);

            // Add this: Calculate total sales for the selected period
            const totalSales = chartData.sales.reduce((sum, sale) => sum + sale, 0);
            
            // Add this: Update the total sales card
            updateTotalSalesCard(totalSales, period);

        } catch (error) {
            console.error('Chart update error:', error);
            const chartContainer = document.querySelector('.chart-container');
            if (chartContainer) {
                chartContainer.innerHTML = `
                    <div style="color: #ff4444; padding: 20px; text-align: center;">
                        <p>Failed to load chart: ${error.message}</p>
                        <p>Please ensure sales data is properly loaded.</p>
                    </div>
                `;
            }
        }
    }

    // Set up event listeners for period buttons
    const buttons = document.querySelectorAll('.report-controls .btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const period = this.getAttribute('data-period');
            if (period) {
                buttons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                updateChart(period);
            }
        });
    });

    // Initialize with weekly data
    setTimeout(() => {
        try {
            // Find the weekly button and simulate a click
            const weeklyButton = document.querySelector('.report-controls .btn[data-period="weekly"]');
            if (weeklyButton) {
                weeklyButton.click();
            } else {
                updateChart('weekly');
            }
        } catch (error) {
            console.error('Failed to initialize chart:', error);
        }
    }, 100);

    // Handle window resize
    window.addEventListener('resize', function() {
        if (currentChart) {
            currentChart.resize();
        }
    });

    // Store the original progress bars data
    let originalProgressBars;

    function initializeData() {
        // Store original progress bars on page load
        originalProgressBars = Array.from(document.querySelectorAll('.progress-bar')).map(bar => bar.cloneNode(true));
    }

    function populateEventSelector() {
        const eventSelector = document.getElementById('eventSelector');
        const uniqueEvents = new Map();

        // Get unique events from the original progress bars
        originalProgressBars.forEach(bar => {
            const eventId = bar.getAttribute('data-event-id');
            const eventTitle = bar.querySelector('.progress-label').textContent.split(' - ')[0];
            
            if (!uniqueEvents.has(eventId)) {
                uniqueEvents.set(eventId, eventTitle);
            }
        });

        // Clear existing options
        eventSelector.innerHTML = '<option value="all">All events</option>';
        
        // Add unique events to selector
        uniqueEvents.forEach((eventTitle, eventId) => {
            const option = document.createElement('option');
            option.value = eventId;
            option.textContent = eventTitle;
            eventSelector.appendChild(option);
        });
    }

    function getUniqueEvents() {
        const events = new Map();

        // Get unique events and sum their totals
        originalProgressBars.forEach(bar => {
            const eventId = bar.getAttribute('data-event-id');
            const eventTitle = bar.querySelector('.progress-label').textContent.split(' - ')[0];
            const ticketInfo = bar.querySelector('.progress-text').textContent.split('/');
            const soldTickets = parseInt(ticketInfo[0]);
            const totalTickets = parseInt(ticketInfo[1]);
            const revenueInfo = bar.querySelector('.progress-info').textContent;

            if (!events.has(eventId)) {
                events.set(eventId, {
                    title: eventTitle,
                    soldTickets: soldTickets,
                    totalTickets: totalTickets,
                    revenue: revenueInfo,
                    orderCount: 0
                });
            } else {
                // Sum up the tickets for the same event
                const existing = events.get(eventId);
                existing.soldTickets += soldTickets;
                existing.totalTickets += totalTickets;
            }
        });

        return events;
    }

    function updateProgressBars(selectedEventId) {
        const progressContainer = document.querySelector('.progress-container');
        const progressCircle = progressContainer.querySelector('.progress-circle');
        const progressBars = progressContainer.querySelector('.progress-bars');
        
        // Clear existing progress bars
        progressBars.innerHTML = '';

        if (selectedEventId === 'all') {
            // Show total tickets for each event
            const uniqueEvents = getUniqueEvents();
            
            uniqueEvents.forEach((eventData, eventId) => {
                const percentage = Math.round((eventData.soldTickets / eventData.totalTickets) * 100) || 0;
                
                const progressBar = document.createElement('div');
                progressBar.className = 'progress-bar';
                progressBar.setAttribute('data-event-id', eventId);
                progressBar.innerHTML = `
                    <div class="progress-label">${eventData.title}</div>
                    <div class="progress-info">${eventData.revenue}</div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width: ${percentage}%;"></div>
                    </div>
                    <div class="progress-text">${eventData.soldTickets}/${eventData.totalTickets} tickets sold</div>
                `;
                progressBars.appendChild(progressBar);
            });

            // Calculate total percentage for all events
            const totalSold = Array.from(uniqueEvents.values()).reduce((sum, event) => sum + event.soldTickets, 0);
            const totalCapacity = Array.from(uniqueEvents.values()).reduce((sum, event) => sum + event.totalTickets, 0);
            const totalPercentage = Math.round((totalSold / totalCapacity) * 100) || 0;
            
            // Update progress circle
            progressCircle.setAttribute('data-percentage', totalPercentage);
            progressCircle.querySelector('.progress-text').textContent = `${totalPercentage}%`;
        } else {
            // Show ticket types for selected event
            let totalSold = 0;
            let totalCapacity = 0;

            originalProgressBars.forEach(bar => {
                if (bar.getAttribute('data-event-id') === selectedEventId) {
                    const clone = bar.cloneNode(true);
                    progressBars.appendChild(clone);

                    // Calculate totals for the selected event
                    const ticketInfo = clone.querySelector('.progress-text').textContent.split('/');
                    totalSold += parseInt(ticketInfo[0]);
                    totalCapacity += parseInt(ticketInfo[1].split(' ')[0]);
                }
            });

            // Update progress circle for selected event
            const percentage = Math.round((totalSold / totalCapacity) * 100) || 0;
            progressCircle.setAttribute('data-percentage', percentage);
            progressCircle.querySelector('.progress-text').textContent = `${percentage}%`;
        }
    }

    // Initialize the page
    initializeData();
    
    // Populate event selector with unique events
    populateEventSelector();
    
    // Set up event selector
    const eventSelector = document.getElementById('eventSelector');
    eventSelector.addEventListener('change', function() {
        updateProgressBars(this.value);
    });

    // Initial display
    updateProgressBars('all');

    // Add print functionality
    document.getElementById('printReport').addEventListener('click', async function() {
        try {
            // Create print-specific chart with modified options
            const printChartCanvas = document.createElement('canvas');
            // Set explicit dimensions for the canvas
            printChartCanvas.width = 800;  // Set fixed width
            printChartCanvas.height = 400; // Set fixed height
            const printCtx = printChartCanvas.getContext('2d');
            
            // Get current chart data and period
            const currentData = currentChart.data;
            const currentPeriod = document.querySelector('.report-controls .btn.active').getAttribute('data-period');

            // Create print-specific chart
            const printChart = new Chart(printCtx, {
                type: 'line',
                data: currentData,
                options: {
                    responsive: false, // Disable responsiveness for print
                    animation: false, // Disable animations
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Sales Trend',
                            color: '#000',
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            padding: 10
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)',
                            },
                            ticks: {
                                color: '#000',
                                font: { size: 10 },
                                callback: function(value) {
                                    return 'RM ' + value.toLocaleString('en-MY', {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    });
                                }
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)',
                            },
                            ticks: {
                                color: '#000',
                                font: { size: 10 },
                                maxRotation: 45,
                                minRotation: 45
                            }
                        }
                    }
                }
            });

            // Wait for chart to render
            await new Promise(resolve => setTimeout(resolve, 100));

            // Get chart image
            const chartImage = printChartCanvas.toDataURL('image/png', 1.0);

            // Create print window content
            let printContent = `
                <html>
                <head>
                    <title>Sales Report</title>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            padding: 15px;
                            color: #333;
                            max-width: 800px;
                            margin: 0 auto;
                        }
                        .report-header { 
                            text-align: center; 
                            margin-bottom: 15px;
                        }
                        .report-header h1 {
                            font-size: 18px;
                            margin: 0 0 5px 0;
                        }
                        .report-header p {
                            font-size: 12px;
                            margin: 3px 0;
                            color: #666;
                        }
                        .summary-grid { 
                            display: grid; 
                            grid-template-columns: repeat(4, 1fr); 
                            gap: 10px; 
                            margin-bottom: 15px; 
                        }
                        .summary-item { 
                            padding: 8px; 
                            border: 1px solid #ddd; 
                            border-radius: 4px; 
                        }
                        .summary-item h3 {
                            font-size: 11px;
                            margin: 0 0 3px 0;
                        }
                        .summary-item p {
                            font-size: 13px;
                            margin: 0;
                            font-weight: bold;
                        }
                        .chart-section {
                            margin: 10px 0;
                        }
                        .chart-container {
                            text-align: center;
                            margin: 10px auto;
                        }
                        .chart-image {
                            max-width: 100%;
                            height: auto;
                            display: block;
                            margin: 0 auto;
                        }
                        .section-title {
                            font-size: 14px;
                            margin: 8px 0;
                            color: #2c3e50;
                        }
                        .progress-section { 
                            margin-top: 10px;
                        }
                        .progress-bar {
                            margin: 4px 0;
                            padding: 6px;
                            border: 1px solid #ddd;
                            font-size: 11px;
                        }
                        @media print {
                            body { padding: 0; }
                            .chart-container { page-break-inside: avoid; }
                        }
                    </style>
                </head>
                <body>
                    <div class="report-header">
                        <h1>TicketPro Sales Report</h1>
                        <p>Generated on ${new Date().toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                        })}</p>
                        <p>Period: ${currentPeriod.charAt(0).toUpperCase() + currentPeriod.slice(1)}</p>
                    </div>

                    <div class="summary-grid">
                        <div class="summary-item">
                            <h3>Total Sales This Week</h3>
                            <p>${document.querySelector('.summary-card:nth-child(1) .large-number').textContent}</p>
                        </div>
                        <div class="summary-item">
                            <h3>New Orders</h3>
                            <p>${document.querySelector('.summary-card:nth-child(2) .large-number').textContent}</p>
                        </div>
                        <div class="summary-item">
                            <h3>Number of Events</h3>
                            <p>${document.querySelector('.summary-card:nth-child(3) .large-number').textContent}</p>
                        </div>
                        <div class="summary-item">
                            <h3>New Customers</h3>
                            <p>${document.querySelector('.summary-card:nth-child(4) .large-number').textContent}</p>
                        </div>
                    </div>

                    <div class="chart-section">
                        <h2 class="section-title">Sales Trend</h2>
                        <div class="chart-container">
                            <img src="${chartImage}" alt="Sales Chart" class="chart-image">
                        </div>
                    </div>

                    <div class="progress-section">
                        <h2 class="section-title">Ticket Sales Summary</h2>
                        <div class="progress-bars">
                            ${document.querySelector('.progress-bars').innerHTML}
                        </div>
                    </div>
                </body>
                </html>
            `;

            const printWindow = window.open('', '_blank');
            printWindow.document.write(printContent);
            printWindow.document.close();

            // Wait for images to load before printing
            printWindow.onload = function() {
                setTimeout(() => {
                    printWindow.print();
                }, 500);
            };

        } catch (error) {
            console.error('Error generating print report:', error);
            alert('Failed to generate print report. Please try again.');
        }
    });

    // Add this new function
    function updateTotalSalesCard(totalSales, period) {
        const salesCard = document.querySelector('.summary-card:first-child');
        if (!salesCard) return;

        // Get ETH value (assuming 14000 MYR/ETH rate)
        const ethValue = totalSales / 14000;

        // Update card title based on period
        const cardTitle = salesCard.querySelector('h3');
        cardTitle.textContent = `Total Sales This ${period.charAt(0).toUpperCase() + period.slice(1)}`;

        // Update sales amount
        const largeNumber = salesCard.querySelector('.large-number');
        largeNumber.innerHTML = `
            RM ${totalSales.toLocaleString('en-MY', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}
            <span class="eth-value">(${ethValue.toFixed(4)} ETH)</span>
        `;

        // Calculate and update the change percentage
        const changeElement = salesCard.querySelector('.change');
        if (changeElement) {
            // You'll need to implement the logic to calculate the change percentage
            // based on the previous period's data
            const previousPeriodTotal = calculatePreviousPeriodTotal(period);
            const changePercentage = previousPeriodTotal ? 
                ((totalSales - previousPeriodTotal) / previousPeriodTotal * 100) : 0;

            changeElement.className = `change ${changePercentage >= 0 ? 'positive' : 'negative'}`;
            changeElement.textContent = `${changePercentage.toFixed(1)}% vs last ${period}`;
        }
    }

    // Add this helper function to calculate previous period's total
    function calculatePreviousPeriodTotal(period) {
        const chartElement = document.getElementById('salesChart');
        const dailySalesStr = chartElement.getAttribute('data-sales');
        const dailySales = JSON.parse(dailySalesStr);

        const now = new Date();
        const previousPeriodSales = dailySales.filter(sale => {
            const saleDate = new Date(sale.OrderDate);
            switch(period) {
                case 'daily':
                    // Previous day
                    const yesterday = new Date(now);
                    yesterday.setDate(now.getDate() - 1);
                    return saleDate.toDateString() === yesterday.toDateString();
                
                case 'weekly':
                    // Previous week
                    const lastWeekStart = new Date(now);
                    lastWeekStart.setDate(now.getDate() - 14);
                    const lastWeekEnd = new Date(now);
                    lastWeekEnd.setDate(now.getDate() - 7);
                    return saleDate >= lastWeekStart && saleDate < lastWeekEnd;
                
                case 'monthly':
                    // Previous month
                    const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
                    return saleDate >= lastMonthStart && saleDate <= lastMonthEnd;
            }
        });

        return previousPeriodSales.reduce((sum, sale) => sum + (parseFloat(sale.DailySales) * 14000), 0);
    }
});
