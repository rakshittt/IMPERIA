document.addEventListener('DOMContentLoaded', () => {
    let portfolio = [];

    const tickerInput = document.getElementById('ticker-input');
    const weightInput = document.getElementById('weight-input');
    const addAssetBtn = document.getElementById('add-asset-btn');
    const portfolioList = document.getElementById('portfolio-list');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultsDashboard = document.getElementById('results-dashboard');
    const inputSection = document.querySelector('.input-section');

    // Default mock data to show visually appealing UI right away
    addAssetToPortfolio('AAPL', 1.0);

    addAssetBtn.addEventListener('click', () => {
        const ticker = tickerInput.value.trim().toUpperCase();
        const weight = parseFloat(weightInput.value);

        if (ticker && !isNaN(weight) && weight > 0) {
            addAssetToPortfolio(ticker, weight);
            tickerInput.value = '';
            weightInput.value = '';
        } else {
            alert('Please enter a valid ticker and a positive weight.');
        }
    });

    function addAssetToPortfolio(ticker, weight) {
        // Check if exists, update weight
        const existing = portfolio.find(item => item.ticker === ticker);
        if (existing) {
            existing.weight = weight;
        } else {
            portfolio.push({ ticker, weight });
        }
        renderPortfolio();
    }

    function removeAsset(ticker) {
        portfolio = portfolio.filter(item => item.ticker !== ticker);
        renderPortfolio();
    }

    function renderPortfolio() {
        portfolioList.innerHTML = '';
        portfolio.forEach(item => {
            const div = document.createElement('div');
            div.className = 'portfolio-item';
            div.innerHTML = `
                <i class="fa-solid fa-chart-pie"></i>
                <span>${item.ticker} (${item.weight})</span>
                <button onclick="window.removeAsset('${item.ticker}')"><i class="fa-solid fa-xmark"></i></button>
            `;
            portfolioList.appendChild(div);
        });

        analyzeBtn.disabled = portfolio.length === 0;
    }

    // Expose for inline onclick
    window.removeAsset = removeAsset;

    analyzeBtn.addEventListener('click', async () => {
        if (portfolio.length === 0) return;

        // Normalize weights to 1.0
        const totalWeight = portfolio.reduce((sum, item) => sum + item.weight, 0);
        const normalizedPortfolio = portfolio.map(item => ({
            ticker: item.ticker,
            weight: item.weight / totalWeight
        }));

        // UI State: Loading
        inputSection.classList.add('hidden');
        resultsDashboard.classList.add('hidden');
        loadingOverlay.classList.remove('hidden');

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    portfolio: normalizedPortfolio,
                    date: new Date().toISOString().split('T')[0],
                    profile: {
                        risk_tolerance: "moderate",
                        time_horizon: "medium-term"
                    }
                })
            });

            if (!response.ok) {
                throw new Error('Analysis failed.');
            }

            const data = await response.json();
            
            // Map the API response to the DOM
            document.getElementById('manager-report').innerHTML = marked.parse(data.final_portfolio_feedback || "*No final feedback available.*");
            document.getElementById('market-report').innerHTML = marked.parse(data.market_report || "*No market data available.*");
            document.getElementById('social-report').innerHTML = marked.parse(data.sentiment_report || "*No social sentiment available.*");
            document.getElementById('news-report').innerHTML = marked.parse(data.news_report || "*No news data available.*");
            document.getElementById('macro-report').innerHTML = marked.parse(data.macro_report || "*No macro analysis available.*");
            document.getElementById('fundamentals-report').innerHTML = marked.parse(data.fundamentals_report || "*No fundamentals available.*");
            document.getElementById('research-report').innerHTML = marked.parse(data.research_synthesis || "*No research synthesis available.*");
            document.getElementById('trader-report').innerHTML = marked.parse(data.trader_report || "*No trader assessment available.*");
            document.getElementById('risk-report').innerHTML = marked.parse(data.risk_report || "*No risk report available.*");

            // UI State: Done
            loadingOverlay.classList.add('hidden');
            resultsDashboard.classList.remove('hidden');
            inputSection.classList.remove('hidden');

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during analysis: ' + error.message);
            loadingOverlay.classList.add('hidden');
            inputSection.classList.remove('hidden');
        }
    });
});
