from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from orders.models import Order
from carts.models import CartItem
from orders.utils import validate_checkout_data, create_order


# Create your views here.
@login_required
def checkout(request, item_id):
    username = request.user.username
    cart_item = get_object_or_404(CartItem, id=item_id)
    total_price = cart_item.product.price * cart_item.quantity

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')

        validation_result = validate_checkout_data(full_name, username)
        if not validation_result['valid']:
            messages.error(request, validation_result['message'])
            return redirect('checkout', item_id=item_id)

        order = create_order(request.user, total_price, address, phone_number, full_name, cart_item)
        messages.success(request, 'Заказ успешно оформлен!')
        return redirect('order_detail', order_id=order.id)

    return render(request, 'orders/checkout.html', {'cart_item': cart_item, 'total_price': total_price})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user)
    order_items = order.orderitem_set.all()
    return render(request, 'orders/order_detail.html', {'order': order, 'order_items': order_items})

@login_required
def my_orders(request):
    orders = Order.objects.filter(owner=request.user, is_ordered=True)
    return render(request, 'orders/my_orders.html', {'orders': orders})
