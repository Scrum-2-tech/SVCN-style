from django.contrib import admin
from .models import Categoria, Producto, Pedido, LineaPedido, Marca, Ciudad, Color, Talla, PerfilUsuario

# Configuración del detalle de pedidos dentro del mismo panel de Pedido
class LineaPedidoInline(admin.TabularInline):
    model = LineaPedido
    extra = 0
    readonly_fields = ['producto', 'cantidad']

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'ciudad', 'total', 'estado', 'fecha_pedido', 'completado']
    list_filter = ['estado', 'completado', 'fecha_pedido', 'ciudad']
    search_fields = ['id', 'usuario__username', 'usuario__email', 'direccion_exacta']
    list_editable = ['estado', 'completado']
    inlines = [LineaPedidoInline]

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio', 'stock', 'categoria', 'marca', 'talla', 'color', 'disponible']
    list_filter = ['disponible', 'categoria', 'marca', 'talla', 'color']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['precio', 'stock', 'disponible']

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'rol', 'telefono']
    list_filter = ['rol']
    search_fields = ['usuario__username', 'usuario__email', 'telefono']
    list_editable = ['rol']

# Registros simples para el resto de componentes de inventario y logística
admin.site.register(Categoria)
admin.site.register(Marca)
admin.site.register(Color)
admin.site.register(Talla)
admin.site.register(Ciudad)