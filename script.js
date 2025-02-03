document.addEventListener('DOMContentLoaded', function() {
    const symbolSelect = document.getElementById('symbol-select');
    const bidsTableBody = document.getElementById('bids-tbody');
    const asksTableBody = document.getElementById('asks-tbody');

    function updateOrderBook() {
        const symbol = symbolSelect.value;
        fetch(`/orderbook_data?symbol=${symbol}`)
            .then(response => response.json())
            .then(data => {
                const { bids, asks } = data;
                // Clear existing rows
                bidsTableBody.innerHTML = '';
                asksTableBody.innerHTML = '';

                // Populate bids
                bids.forEach(row => {
                    const tr = document.createElement('tr');
                    const [price, qty, timestamp] = row;
                    tr.innerHTML = `<td>${price}</td><td>${qty}</td><td>${timestamp}</td>`;
                    bidsTableBody.appendChild(tr);
                });

                // Populate asks
                asks.forEach(row => {
                    const tr = document.createElement('tr');
                    const [price, qty, timestamp] = row;
                    tr.innerHTML = `<td>${price}</td><td>${qty}</td><td>${timestamp}</td>`;
                    asksTableBody.appendChild(tr);
                });
            })
            .catch(err => console.error('Error updating order book:', err));
    }

    // Update the order book every 5 seconds
    setInterval(updateOrderBook, 5000);
    updateOrderBook(); // Initial load
});
