let count = 1;

        function incrementCount() {
            count++;
            updateCount();
        }

        function decrementCount() {
            if (count > 1) {
                count--;
                updateCount();
            }
        }

        function updateCount() {
            document.getElementById('count').innerText = count;
            updateTotal();
        }

        function updateTotal() {
            const pricePerItem = 20; // Цена за единицу продукта
            const total = count * pricePerItem;
            document.querySelector('.total').innerText = `Общая стоимость: $${total}`;
        }