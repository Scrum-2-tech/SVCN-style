from decimal import Decimal
from django.conf import settings
from .models import Producto

class Cart:
    """
    CLASE DE CONTROL DEL CARRITO: Maneja la persistencia de los productos
    seleccionados por el usuario utilizando la sesión del navegador.
    """
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, producto, cantidad=1, update_quantity=False):
        """
        Añade un producto al carrito o actualiza su cantidad.
        Si 'update_quantity' es True, reemplaza la cantidad existente (esencial para la modificación dinámica).
        """
        producto_id = str(producto.id)
        
        if producto_id not in self.cart:
            self.cart[producto_id] = {
                'producto_id': producto.id,
                'nombre': producto.nombre,
                'precio': str(producto.precio),
                'cantidad': 0,
                'acumulado': str(producto.precio),
                'imagen_url': producto.imagen.url if producto.imagen else None
            }

        if update_quantity:
            self.cart[producto_id]['cantidad'] = cantidad
        else:
            self.cart[producto_id]['cantidad'] += cantidad

        # Recalcula el subtotal acumulado de esta prenda
        self.cart[producto_id]['acumulado'] = str(
            Decimal(self.cart[producto_id]['precio']) * self.cart[producto_id]['cantidad']
        )
        self.save()

    def save(self):
        """Marca la sesión como modificada para asegurar que se guarde."""
        self.session.modified = True

    def remove(self, producto):
        """Elimina un producto por completo del carrito."""
        producto_id = str(producto.id)
        if producto_id in self.cart:
            del self.cart[producto_id]
            self.save()

    def __iter__(self):
        """
        Itera sobre los elementos del carrito y recupera los objetos 
        Producto directamente de la base de datos.
        """
        producto_ids = self.cart.keys()
        productos = Producto.objects.filter(id__in=producto_ids)
        
        cart_copy = self.cart.copy()
        for producto in productos:
            cart_copy[str(producto.id)]['producto'] = producto

        for item in cart_copy.values():
            item['precio'] = Decimal(item['precio'])
            item['acumulado'] = Decimal(item['acumulado'])
            yield item

    def __len__(self):
        """Cuenta la cantidad total de prendas individuales en el carrito."""
        return sum(item['cantidad'] for item in self.cart.values())

    def get_total_price(self):
        """Calcula el costo total de la compra actual en el carrito."""
        return sum(Decimal(item['precio']) * item['cantidad'] for item in self.cart.values())

    def clear(self):
        """Vacía el carrito por completo eliminando la variable de la sesión."""
        del self.session[settings.CART_SESSION_ID]
        self.save()