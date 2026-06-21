from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==========================================
# MODELOS DE COMPONENTES DEL PRODUCTO
# ==========================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Categoría")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Marca")

    def __str__(self):
        return self.nombre


class Color(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Color")
    codigo_hex = models.CharField(max_length=7, default="#000000", verbose_name="Código Hexadecimal")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Colores"


class Talla(models.Model):
    nombre = models.CharField(max_length=10, unique=True, verbose_name="Talla")

    def __str__(self):
        return self.nombre


# ==========================================
# MODELO PRINCIPAL: PRODUCTO (INVENTARIO)
# ==========================================

class Producto(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    precio = models.DecimalField(max_length=10, max_digits=10, decimal_places=2, verbose_name="Precio")
    stock = models.IntegerField(default=0, verbose_name="Cantidad en Stock")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen del Producto")
    disponible = models.BooleanField(default=True, verbose_name="Disponible para la venta")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    # Relaciones del producto
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos', verbose_name="Categoría")
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Marca")
    talla = models.ForeignKey(Talla, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Talla")
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Color")

    def __str__(self):
        return f"{self.nombre} - Talla {self.talla.nombre if self.talla else 'Única'}"


# ==========================================
# GESTIÓN DE GEOGRAFÍA Y ENVÍOS
# ==========================================

class Ciudad(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Ciudad/Municipio")
    departamento = models.CharField(max_length=100, verbose_name="Departamento")

    def __str__(self):
        return f"{self.nombre} ({self.departamento})"

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"


# ==========================================
# PERFIL DE USUARIO (CONTROL DE ROLES)
# ==========================================

class PerfilUsuario(models.Model):
    """
    PERFIL EXTENDIDO: Almacena de manera estricta el rol del usuario en la plataforma.
    Soporta los tres roles requeridos: Administrador, Empleado (Vendedor) y Cliente.
    """
    ROLES = [
        ('ADM', 'Administrador'),
        ('EMP', 'Empleado / Vendedor'),
        ('CLI', 'Cliente'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=3, choices=ROLES, default='CLI', verbose_name="Rol en la plataforma")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")

    def __str__(self):
        return f"{self.usuario.username} - Rol: {self.get_rol_display()}"


# --- Señales automáticas para extender el modelo User ---
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Si el usuario es superusuario de Django, le asignamos rol Administrador por defecto
        rol_defecto = 'ADM' if instance.is_superuser else 'CLI'
        PerfilUsuario.objects.get_or_create(usuario=instance, defaults={'rol': rol_defecto})

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()


# ==========================================
# MODELOS DE PEDIDOS Y TRANSACCIONES
# ==========================================

class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ('PEN', 'Pendiente de Pago'),
        ('PRE', 'En Preparación'),
        ('ENV', 'Enviado'),
        ('ENT', 'Entregado'),
        ('CAN', 'Cancelado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Cliente")
    fecha_pedido = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Compra")
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Pagado")
    estado = models.CharField(max_length=3, choices=ESTADOS_PEDIDO, default='PEN', verbose_name="Estado del Pedido")
    completado = models.BooleanField(default=False, verbose_name="¿Entregado y Cerrado?")
    
    # Datos de destino
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True, verbose_name="Ciudad de Destino")
    direccion_exacta = models.CharField(max_length=255, verbose_name="Dirección de Envío")

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username} - Total: ${self.total}"


class LineaPedido(models.Model):
    """
    DETALLE DEL PEDIDO: Rompe la relación muchos a muchos guardando la cantidad
    exacta de cada prenda adquirida por el usuario.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name="Prenda")
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    cantidad = models.IntegerField(default=1, verbose_name="Cantidad Comprada")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (Pedido #{self.pedido.id})"

    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedidos"