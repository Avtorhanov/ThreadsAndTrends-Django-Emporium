
        // корзина, инкремент, дикремент подсчет общей стоимости

        if (document.querySelector('.total')) {
            document.addEventListener('DOMContentLoaded', function() {
                updateTotalPrice();
            });

            function updateTotalPrice() {
                const totalElement = document.querySelector('.total');
                const items = document.querySelectorAll('.product');

                let totalPrice = 0;

                items.forEach(item => {
                    const quantity = parseInt(item.querySelector('.decr-counter span').innerText);
                    const price = parseFloat(item.querySelector('.product-info .price').innerText);
                    totalPrice += quantity * price;
                });

                totalElement.innerText = `Общая стоимость: ${totalPrice.toFixed(1)} ₽`;
            }
        }

        function updateCount(itemId, newCount) {
            const csrfToken = document.getElementById('csrf_token').value;
            fetch(`/update_cart_item/${itemId}/${newCount}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById(`count${itemId}`).innerText = newCount;
                updateTotalPrice(); // Обновляем общую стоимость после изменения количества товаров
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }

        function incrementCount(itemId) {
            const currentCount = parseInt(document.getElementById(`count${itemId}`).innerText);
            updateCount(itemId, currentCount + 1);
        }

        function decrementCount(itemId) {
            const currentCount = parseInt(document.getElementById(`count${itemId}`).innerText);
            if (currentCount > 1) {
                updateCount(itemId, currentCount - 1);
            }
        }

        function removeFromCart(itemId) {
            const csrfToken = document.getElementById('csrf_token').value;
            fetch(`/remove_from_cart/${itemId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log(data);
                location.reload();
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }


        // код из блока продукта, добавление товара в корзину

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.startsWith(name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        function addToCart(productId, productPrice) {
            fetch(`/add_to_cart/${productId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ product_price: productPrice })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success')
                location.reload();
                console.log(data);
            })
            .catch(error => {
                console.error('Error:', error);пше

            });
        }