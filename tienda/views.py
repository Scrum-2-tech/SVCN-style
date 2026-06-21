from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import requests
import json
import os
from xhtml2pdf import pisa
from collections import defaultdict

from .models import Producto, Color, Talla, Categoria, Marca, Ciudad, PerfilUsuario, Pedido, LineaPedido
from .forms import ColorForm, TallaForm, ProductoForm, RegistroUsuarioForm, FormularioEnvio, PerfilUsuarioForm
from .cart import Cart

# Importaciones para el sistema de autenticación nativo y seguro
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout

# ==========================================
# VISTAS PÚBLICAS (ACCESO PARA TODOS)
# ==========================================

def index(request):
    productos = Producto.objects.filter(disponible=True)
    return render(request, 'index.html', {'productos': productos})

def lista_productos(request):
    categorias = Categoria.objects.all()
    marcas = Marca.objects.all()
    colores = Color.objects.all()
    tallas = Talla.objects.all()
    
    q = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    marca_id = request.GET.get('marca', '')
    color_id = request.GET.get('color', '')
    talla_id = request.GET.get('talla', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    orden = request.GET.get('orden', '')
    
    productos = Producto.objects.filter(disponible=True)
    
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    if marca_id:
        productos = productos.filter(marca_id=marca_id)
    if color_id:
        productos = productos.filter(color_id=color_id)
    if talla_id:
        productos = productos.filter(talla_id=talla_id)
    if precio_min:
        try:
            productos = productos.filter(precio__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            productos = productos.filter(precio__lte=float(precio_max))
        except ValueError:
            pass
            
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    elif orden == 'reciente':
        productos = productos.order_by('-fecha_creacion')
    else:
        productos = productos.order_by('nombre')
        
    context = {
        'productos': productos, 
        'categorias': categorias,
        'marcas': marcas,
        'colores': colores,
        'tallas': tallas,
        'q': q,
        'categoria_actual': int(categoria_id) if categoria_id and categoria_id.isdigit() else None,
        'marca_actual': int(marca_id) if marca_id and marca_id.isdigit() else None,
        'color_actual': int(color_id) if color_id and color_id.isdigit() else None,
        'talla_actual': int(talla_id) if talla_id and talla_id.isdigit() else None,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'orden_actual': orden,
    }
    return render(request, 'productos.html', context)

def acerca_de(request):
    return render(request, 'acerca_de.html')


# ==========================================
# GESTIÓN DE AUTENTICACIÓN, REGISTRO Y ROLES
# ==========================================

def register(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'¡Cuenta creada para {username}! Ya puedes ingresar de forma segura.')
            return redirect('login')
        else:
            messages.error(request, "Error en el registro. Verifica que cumpla los requisitos de seguridad.")
    else:
        form = RegistroUsuarioForm()
    return render(request, 'register.html', {'form': form})

def iniciar_sesion(request):
    """
    VISTA DE LOGIN REAL: Autentica comparando de forma segura 
    el texto plano ingresado contra el HASH de la base de datos.
    """
    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        password_input = request.POST.get('password')

        user = authenticate(request, username=usuario_input, password=password_input)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
            return redirect('login_redirect')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
            
    return render(request, 'login.html')

def cerrar_sesion(request):
    """Cierra la sesión del usuario de forma segura."""
    auth_logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('index')

@login_required
def login_redirect(request):
    """
    REDIRECCIÓN POR ROLES: Envía a cada usuario a su panel correspondiente 
    evaluando de forma estricta el campo 'rol' en PerfilUsuario.
    """
    if hasattr(request.user, 'perfil'):
        rol_usuario = request.user.perfil.rol
        if rol_usuario == 'ADM':
            return redirect('dashboard_stats')
        elif rol_usuario == 'EMP':
            return redirect('panel_vendedor')
            
    return redirect('index')

@login_required
def panel_vendedor(request):
    """
    PANEL OPERATIVO DE VENTAS Y LOGÍSTICA PARA VENDEDORES (SVCN Style)
    Incluye búsqueda multicriterio avanzada para la gestión y reportes.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol not in ['EMP', 'ADM']:
        messages.error(request, "No tienes permisos para acceder al panel de vendedores.")
        return redirect('index')

    # Reutilización de los componentes de filtro multicriterio
    ciudades = Ciudad.objects.all()
    
    cliente = request.GET.get('cliente', '')
    estado = request.GET.get('estado', '')
    ciudad_id = request.GET.get('ciudad', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    
    # Por defecto, si no hay filtro, el vendedor ve los pendientes por despachar (PEN y PRE)
    # Si viene un filtro explícito de estado, usamos ese.
    if estado:
        pedidos = Pedido.objects.filter(estado=estado)
    else:
        pedidos = Pedido.objects.all()

    pedidos = pedidos.select_related('usuario', 'ciudad')
    
    if cliente:
        pedidos = pedidos.filter(
            Q(usuario__username__icontains=cliente) |
            Q(usuario__first_name__icontains=cliente) |
            Q(usuario__last_name__icontains=cliente) |
            Q(usuario__email__icontains=cliente)
        )
    if ciudad_id:
        pedidos = pedidos.filter(ciudad_id=ciudad_id)
    if fecha_inicio:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__gte=fecha_inicio)
        except Exception:
            pass
    if fecha_fin:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__lte=fecha_fin)
        except Exception:
            pass
            
    pedidos = pedidos.order_by('-fecha_pedido')
    
    # Métricas rápidas legibles para el turno
    total_ventas_filtradas = sum(p.total for p in pedidos)
    conteo_pendientes = Pedido.objects.filter(estado__in=['PEN', 'PRE']).count()
    
    # Consulta rápida de inventario (Buscador integrado en el panel)
    q_inv = request.GET.get('q_inv', '')
    productos_inventario = Producto.objects.all()
    if q_inv:
        productos_inventario = productos_inventario.filter(
            Q(nombre__icontains=q_inv) | Q(categoria__nombre__icontains=q_inv)
        )
    productos_inventario = productos_inventario.order_by('stock')[:10]

    context = {
        'pedidos': pedidos,
        'ciudades': ciudades,
        'estados_pedido': Pedido.ESTADOS_PEDIDO,
        'cliente': cliente,
        'estado_actual': estado,
        'ciudad_actual': int(ciudad_id) if ciudad_id and ciudad_id.isdigit() else None,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_ventas_filtradas': total_ventas_filtradas,
        'conteo_pendientes': conteo_pendientes,
        'productos_inventario': productos_inventario,
        'q_inv': q_inv
    }
    return render(request, 'dashboard/panel_vendedor.html', context)


# ==========================================
# GESTIÓN DEL CARRITO COMPLETA Y DINÁMICA
# ==========================================

def carrito_detalle(request):
    cart = Cart(request)
    form_envio = FormularioEnvio()
    return render(request, 'carrito.html', {
        'cart': cart, 
        'form_envio': form_envio
    })

def agregar_producto(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)
    cantidad = int(request.GET.get('cantidad', 1))
    cart.add(producto=producto, cantidad=cantidad)
    return redirect("carrito_detalle")

def eliminar_producto(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)
    cart.remove(producto)
    return redirect("carrito_detalle")

def limpiar_carrito(request):
    cart = Cart(request)
    cart.clear()
    return redirect("carrito_detalle")

def actualizar_carrito(request, producto_id):
    """
    MODIFICACIÓN DINÁMICA DE CANTIDADES: Cambia el número de productos 
    directamente desde el listado del carrito.
    """
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        nueva_cantidad = int(request.POST.get('cantidad', 1))
        
        if nueva_cantidad <= 0:
            cart.remove(producto)
            messages.info(request, f"Se eliminó {producto.nombre} del carrito.")
        elif nueva_cantidad > producto.stock:
            messages.error(request, f"Cantidad no disponible. Solo quedan {producto.stock} unidades de {producto.nombre}.")
        else:
            cart.add(producto=producto, cantidad=nueva_cantidad, update_quantity=True)
            messages.success(request, f"Cantidad de {producto.nombre} actualizada.")
            
    return redirect("carrito_detalle")


# ==========================================
# VISTAS DEL CLIENTE (REQUIEREN LOGIN)
# ==========================================

@login_required
def procesar_compra(request):
    cart = Cart(request)
    total_compra = 0
    
    if "cart" in request.session:
        for key, value in request.session["cart"].items():
            total_compra += float(value["acumulado"])

    if total_compra <= 0:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('index')

    if request.method == 'POST':
        form = FormularioEnvio(request.POST)
        if form.is_valid():
            pedido = Pedido.objects.create(
                usuario=request.user,
                total=total_compra,
                ciudad=form.cleaned_data['ciudad'],
                direccion_exacta=form.cleaned_data['direccion'],
                estado='PEN'
            )

            for key, value in request.session["cart"].items():
                producto = Producto.objects.get(id=value["producto_id"])
                LineaPedido.objects.create(
                    usuario=request.user,
                    producto=producto,
                    pedido=pedido,
                    cantidad=value["cantidad"]
                )
                
                producto.stock -= int(value["cantidad"])
                if producto.stock <= 0:
                    producto.disponible = False
                producto.save()

            cart.clear()
            messages.success(request, f"¡Pedido #{pedido.id} realizado! Pronto llegará a {pedido.ciudad.nombre}.")
            return redirect('mis_pedidos')
    return redirect('carrito_detalle')

@login_required
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-fecha_pedido')
    return render(request, 'mis_pedidos.html', {'pedidos': pedidos})

@login_required
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    detalles = LineaPedido.objects.filter(pedido=pedido)
    return render(request, 'detalle_pedido.html', {'pedido': pedido, 'detalles': detalles})


# ==========================================
# VISTAS DEL ADMINISTRADOR Y REDIRECCIONES (COMPATIBLE CON VENDEDOR)
# ==========================================

@login_required
def cambiar_estado_pedido(request, pedido_id, nuevo_estado):
    """
    CAMBIO DE ESTADO INTELIGENTE: Permite que tanto administradores como
    vendedores cambien el estado del pedido, retornándolos a sus respectivos paneles.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.estado = nuevo_estado
    
    if nuevo_estado == 'ENT':
        pedido.completado = True
        
    pedido.save()
    messages.success(request, f"Estado del pedido #{pedido.id} actualizado.")
    
    # Si el usuario es vendedor operativo ('EMP'), vuelve a su panel de vendedor
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'EMP':
        return redirect('panel_vendedor')
        
    return redirect('gestion_pedidos')

@staff_member_required
def dashboard_stats(request):
    total_dinero = Pedido.objects.aggregate(Sum('total'))['total__sum'] or 0
    cantidad_pedidos = Pedido.objects.count()
    total_clientes = User.objects.filter(is_staff=False).count()
    productos_criticos = Producto.objects.filter(stock__lt=5)
    
    top_ventas = LineaPedido.objects.values('producto__nombre')\
        .annotate(total_vendido=Sum('cantidad'))\
        .order_by('-total_vendido')[:5]

    # --- DATOS PARA GRÁFICOS (CHART.JS) ---
    categorias_ventas = {}
    for lp in LineaPedido.objects.select_related('producto__categoria'):
        cat_name = lp.producto.categoria.nombre
        subtotal = float(lp.cantidad * lp.producto.precio)
        categorias_ventas[cat_name] = categorias_ventas.get(cat_name, 0.0) + subtotal
        
    cat_labels = list(categorias_ventas.keys())
    cat_data = list(categorias_ventas.values())

    meses_ventas = defaultdict(float)
    for p in Pedido.objects.all():
        mes_key = p.fecha_pedido.strftime('%Y-%m')
        meses_ventas[mes_key] += float(p.total)
        
    meses_ordenados = sorted(meses_ventas.keys())
    mes_labels = []
    meses_nombres = {
        '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr', '05': 'May', '06': 'Jun',
        '07': 'Jul', '08': 'Ago', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
    }
    for m in meses_ordenados:
        year, month = m.split('-')
        mes_labels.append(f"{meses_nombres.get(month, month)} {year}")
        
    mes_data = [meses_ventas[m] for m in meses_ordenados]

    context = {
        'total_dinero': total_dinero,
        'cantidad_pedidos': cantidad_pedidos,
        'total_clientes': total_clientes,
        'productos_criticos': productos_criticos,
        'top_ventas': top_ventas,
        'cat_labels_json': json.dumps(cat_labels),
        'cat_data_json': json.dumps(cat_data),
        'mes_labels_json': json.dumps(mes_labels),
        'mes_data_json': json.dumps(mes_data),
    }
    return render(request, 'dashboard/stats.html', context)

@staff_member_required
def gestion_pedidos(request):
    ciudades = Ciudad.objects.all()
    
    cliente = request.GET.get('cliente', '')
    estado = request.GET.get('estado', '')
    ciudad_id = request.GET.get('ciudad', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    total_min = request.GET.get('total_min', '')
    total_max = request.GET.get('total_max', '')
    
    pedidos = Pedido.objects.all().select_related('usuario', 'ciudad')
    
    if cliente:
        pedidos = pedidos.filter(
            Q(usuario__username__icontains=cliente) |
            Q(usuario__first_name__icontains=cliente) |
            Q(usuario__last_name__icontains=cliente) |
            Q(usuario__email__icontains=cliente)
        )
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if ciudad_id:
        pedidos = pedidos.filter(ciudad_id=ciudad_id)
    if fecha_inicio:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__gte=fecha_inicio)
        except Exception:
            pass
    if fecha_fin:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__lte=fecha_fin)
        except Exception:
            pass
    if total_min:
        try:
            pedidos = pedidos.filter(total__gte=float(total_min))
        except ValueError:
            pass
    if total_max:
        try:
            pedidos = pedidos.filter(total__lte=float(total_max))
        except ValueError:
            pass
            
    pedidos = pedidos.order_by('-fecha_pedido')
    
    context = {
        'pedidos': pedidos,
        'ciudades': ciudades,
        'estados_pedido': Pedido.ESTADOS_PEDIDO,
        'cliente': cliente,
        'estado_actual': estado,
        'ciudad_actual': int(ciudad_id) if ciudad_id and ciudad_id.isdigit() else None,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_min': total_min,
        'total_max': total_max,
    }
    return render(request, 'dashboard/pedidos.html', context)
    
@staff_member_required
def mantenimiento_inventario(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    colores = Color.objects.all()
    tallas = Talla.objects.all()
    marcas = Marca.objects.all()
    ciudades = Ciudad.objects.all()
    form_producto = ProductoForm()
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'colores': colores,
        'tallas': tallas,
        'marcas': marcas,
        'ciudades': ciudades,
        'form_producto': form_producto,
    }
    return render(request, 'dashboard/mantenimiento.html', context)

@staff_member_required
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f"¡{producto.nombre} actualizado correctamente!")
            return redirect('mantenimiento')
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'dashboard/editar_producto.html', {
        'form': form,
        'producto': producto
    })

@staff_member_required
def crear_producto_admin(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            messages.success(request, "¡Producto creado con éxito!")
        else:
            messages.error(request, "Error en el formulario.")
    return redirect('mantenimiento')

@staff_member_required
def eliminar_producto_admin(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    messages.success(request, "Producto eliminado correctamente.")
    return redirect('mantenimiento')


# ==========================================
# CREACIÓN DE COMPONENTES DE INVENTARIO
# ==========================================

@staff_member_required
def agregar_color(request):
    if request.method == 'POST':
        form = ColorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Color agregado.")
    return redirect('mantenimiento')

@staff_member_required
def agregar_talla(request):
    if request.method == 'POST':
        form = TallaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Talla agregada.")
    return redirect('mantenimiento')

@staff_member_required
def agregar_categoria(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            Categoria.objects.create(nombre=nombre)
            messages.success(request, f"Categoría '{nombre}' agregada con éxito.")
    return redirect('mantenimiento')

@staff_member_required
def agregar_marca(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            Marca.objects.get_or_create(nombre=nombre)
            messages.success(request, "Marca agregada.")
    return redirect('mantenimiento')

@staff_member_required
def agregar_ciudad(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        depto = request.POST.get('departamento')
        if nombre and depto:
            Ciudad.objects.get_or_create(nombre=nombre, departamento=depto)
            messages.success(request, "Ciudad agregada.")
    return redirect('mantenimiento')


# ==========================================
# ELIMINACIÓN DE COMPONENTES DE INVENTARIO
# ==========================================

@staff_member_required
def eliminar_marca(request, id):
    get_object_or_404(Marca, id=id).delete()
    return redirect('mantenimiento')

@staff_member_required
def eliminar_ciudad(request, id):
    get_object_or_404(Ciudad, id=id).delete()
    return redirect('mantenimiento')

@staff_member_required
def eliminar_color(request, id):
    get_object_or_404(Color, id=id).delete()
    return redirect('mantenimiento')

@staff_member_required
def eliminar_talla(request, id):
    get_object_or_404(Talla, id=id).delete()
    return redirect('mantenimiento')

@staff_member_required
def eliminar_categoria(request, id):
    get_object_or_404(Categoria, id=id).delete()
    return redirect('mantenimiento')


# ==========================================
# REPORTES Y EXPORTACIÓN DE DATOS (PDF/CSV)
# ==========================================

def exportar_reporte_pdf(request):
    cliente = request.GET.get('cliente', '')
    estado = request.GET.get('estado', '')
    ciudad_id = request.GET.get('ciudad', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    total_min = request.GET.get('total_min', '')
    total_max = request.GET.get('total_max', '')

    pedidos = Pedido.objects.all().select_related('usuario', 'ciudad')

    if cliente:
        pedidos = pedidos.filter(
            Q(usuario__username__icontains=cliente) |
            Q(usuario__first_name__icontains=cliente) |
            Q(usuario__last_name__icontains=cliente) |
            Q(usuario__email__icontains=cliente)
        )
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if ciudad_id:
        pedidos = pedidos.filter(ciudad_id=ciudad_id)
    if fecha_inicio:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__gte=fecha_inicio)
        except Exception:
            pass
    if fecha_fin:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__lte=fecha_fin)
        except Exception:
            pass
    if total_min:
        try:
            pedidos = pedidos.filter(total__gte=float(total_min))
        except ValueError:
            pass
    if total_max:
        try:
            pedidos = pedidos.filter(total__lte=float(total_max))
        except ValueError:
            pass

    pedidos = pedidos.order_by('-fecha_pedido')
    total_ventas = sum(p.total for p in pedidos)
    
    context = {
        'pedidos': pedidos,
        'total_ventas': total_ventas,
        'fecha': datetime.now(),
        'empresa': 'SVCN STYLE'
    }
    
    template = get_template('reportes/pdf_reporte.html')
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas_svcn.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el reporte', status=500)
    return response

@staff_member_required
def exportar_reporte_csv(request):
    import csv
    cliente = request.GET.get('cliente', '')
    estado = request.GET.get('estado', '')
    ciudad_id = request.GET.get('ciudad', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    total_min = request.GET.get('total_min', '')
    total_max = request.GET.get('total_max', '')

    pedidos = Pedido.objects.all().select_related('usuario', 'ciudad')

    if cliente:
        pedidos = pedidos.filter(
            Q(usuario__username__icontains=cliente) |
            Q(usuario__first_name__icontains=cliente) |
            Q(usuario__last_name__icontains=cliente) |
            Q(usuario__email__icontains=cliente)
        )
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if ciudad_id:
        pedidos = pedidos.filter(ciudad_id=ciudad_id)
    if fecha_inicio:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__gte=fecha_inicio)
        except Exception:
            pass
    if fecha_fin:
        try:
            pedidos = pedidos.filter(fecha_pedido__date__lte=fecha_fin)
        except Exception:
            pass
    if total_min:
        try:
            pedidos = pedidos.filter(total__gte=float(total_min))
        except ValueError:
            pass
    if total_max:
        try:
            pedidos = pedidos.filter(total__lte=float(total_max))
        except ValueError:
            pass

    pedidos = pedidos.order_by('-fecha_pedido')

    response = HttpResponse(content_type='text/csv')
    response.write('\ufeff'.encode('utf8'))
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas_svcn.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['ID Pedido', 'Cliente', 'Correo', 'Destino (Ciudad)', 'Dirección', 'Total', 'Estado', 'Fecha'])

    for p in pedidos:
        writer.writerow([
            f"#{p.id}",
            f"{p.usuario.first_name} {p.usuario.last_name} ({p.usuario.username})",
            p.usuario.email,
            p.ciudad.nombre if p.ciudad else 'N/A',
            p.direccion_exacta,
            int(p.total),
            p.get_estado_display(),
            p.fecha_pedido.strftime('%Y-%m-%d %H:%M')
        ])
    return response

def exportar_catalogo_csv(request):
    import csv
    q = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    marca_id = request.GET.get('marca', '')
    color_id = request.GET.get('color', '')
    talla_id = request.GET.get('talla', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    
    productos = Producto.objects.filter(disponible=True)
    
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    if marca_id:
        productos = productos.filter(marca_id=marca_id)
    if color_id:
        productos = productos.filter(color_id=color_id)
    if talla_id:
        productos = productos.filter(talla_id=talla_id)
    if precio_min:
        try:
            productos = productos.filter(precio__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            productos = productos.filter(precio__lte=float(precio_max))
        except ValueError:
            pass

    response = HttpResponse(content_type='text/csv')
    response.write('\ufeff'.encode('utf8'))
    response['Content-Disposition'] = 'attachment; filename="catalogo_productos_svcn.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nombre', 'Categoría', 'Marca', 'Talla', 'Color', 'Precio', 'Stock', 'Disponible'])

    for p in productos:
        writer.writerow([
            p.nombre,
            p.categoria.nombre,
            p.marca.nombre if p.marca else 'Genérico',
            p.talla.nombre if p.talla else 'Única',
            p.color.nombre if p.color else 'N/A',
            int(p.precio),
            p.stock,
            'Sí' if p.disponible else 'No'
        ])
    return response

def exportar_catalogo_pdf(request, categoria_id=None):
    if categoria_id:
        productos = Producto.objects.filter(categoria_id=categoria_id)
        nombre_cat = "Filtrado"
    else:
        productos = Producto.objects.all()
        nombre_cat = "Completo"

    productos_limpios = []
    for p in productos:
        productos_limpios.append({
            'nombre': p.nombre if p.nombre else "Producto sin nombre",
            'marca': p.marca.nombre if p.marca else "SVCN Style",
            'talla': p.talla.nombre if p.talla else "Única",
            'color': p.color.nombre if p.color else "N/A",
            'precio': p.precio if p.precio is not None else 0,
        })

    context = {
        'productos': productos_limpios,
        'categoria': nombre_cat,
        'fecha': timezone.now()
    }

    try:
        template = get_template('reportes/pdf_catalogo.html')
        html = template.render(context)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="catalogo_svcn.pdf"'
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error técnico al crear PDF', status=500)
        return response
    except Exception as e:
        return HttpResponse(f'Error crítico: {e}', status=500)


# ==========================================
# GESTIÓN DE ROLES E IMPORTACIÓN EXTERNA (JSON)
# ==========================================

@staff_member_required
def gestion_usuarios(request):
    query = request.GET.get('q', '')
    rol_filtro = request.GET.get('rol', '')
    
    perfiles = PerfilUsuario.objects.all().select_related('usuario')
    
    if query:
        perfiles = perfiles.filter(
            Q(usuario__username__icontains=query) |
            Q(usuario__first_name__icontains=query) |
            Q(usuario__last_name__icontains=query) |
            Q(usuario__email__icontains=query) |
            Q(telefono__icontains=query)
        )
    if rol_filtro:
        perfiles = perfiles.filter(rol=rol_filtro)
        
    context = {
        'perfiles': perfiles,
        'query': query,
        'rol_filtro': rol_filtro,
        'roles': PerfilUsuario.ROLES
    }
    return render(request, 'dashboard/roles.html', context)

@staff_member_required
def cambiar_rol(request, usuario_id):
    perfil = get_object_or_404(PerfilUsuario, usuario_id=usuario_id)
    if request.method == 'POST':
        nuevo_rol = request.POST.get('rol')
        if nuevo_rol in dict(PerfilUsuario.ROLES):
            perfil.rol = nuevo_rol
            perfil.save()
            messages.success(request, f"¡Rol de {perfil.usuario.username} actualizado a {perfil.get_rol_display()}!")
        else:
            messages.error(request, "Rol no válido.")
    return redirect('gestion_usuarios')

def catalogo_externo(request):
    ruta_json = os.path.join(settings.BASE_DIR, 'productos_oversized.json')
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            productos_api = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        productos_api = []
        messages.error(request, "No se pudo cargar el archivo del catálogo externo.")
        
    return render(request, 'catalogo_externo.html', {'productos': productos_api})

@staff_member_required
def descargar_plantilla_json(request):
    plantilla = [
        {
            "title": "Hoodie Minimalist Sand - Premium",
            "brand": "SVCN Style",
            "color": "Beige",
            "size": "L",
            "price": 135000,
            "description": "Algodón peinado premium de 400g. Horma Boxy.",
            "category": "Hoodies",
            "image": "productos/h-sand.jpg"
        }
    ]
    response = HttpResponse(json.dumps(plantilla, indent=4), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="plantilla_productos_svcn.json"'
    return response

@staff_member_required
def importing_api(request):
    pass

@staff_member_required
def importar_api(request):
    if request.method == "POST":
        archivo = request.FILES.get('archivo_json')
        datos = []
        
        try:
            if archivo:
                contenido = archivo.read().decode('utf-8')
                datos = json.loads(contenido)
            else:
                ruta_json = os.path.join(settings.BASE_DIR, 'productos_oversized.json')
                with open(ruta_json, 'r', encoding='utf-8') as f:
                    datos = json.load(f)

            if not isinstance(datos, list):
                messages.error(request, "El archivo JSON debe contener una lista de productos.")
                return redirect('mantenimiento')
                
            creados = 0
            actualizados = 0
            errores = 0
            
            for item in datos:
                try:
                    titulo = item.get('title')
                    precio = item.get('price')
                    categoria_nombre = item.get('category')
                    
                    if not titulo or precio is None or not categoria_nombre:
                        errores += 1
                        continue
                    
                    cat, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)
                    marca_obj, _ = Marca.objects.get_or_create(nombre=item.get('brand', 'SVCN Style'))
                    color_obj, _ = Color.objects.get_or_create(nombre=item.get('color', 'N/A'))
                    talla_obj, _ = Talla.objects.get_or_create(nombre=item.get('size', 'Única'))
                    
                    img_path = item.get('image', '')
                    ruta_limpia = img_path.replace('/static/', '')
                    if ruta_limpia.startswith('/'):
                        ruta_limpia = ruta_limpia[1:]
                        
                    producto, created = Producto.objects.get_or_create(
                        nombre=titulo,
                        defaults={
                            'precio': precio,
                            'descripcion': item.get('description', ''),
                            'categoria': cat,
                            'marca': marca_obj,
                            'color': color_obj,
                            'talla': talla_obj,
                            'stock': 25,
                            'disponible': True,
                            'imagen': ruta_limpia
                        }
                    )
                    
                    if created:
                        creados += 1
                    else:
                        producto.precio = precio
                        producto.descripcion = item.get('description', '')
                        producto.categoria = cat
                        producto.marca = marca_obj
                        producto.color = color_obj
                        producto.talla = talla_obj
                        producto.save()
                        actualizados += 1
                except Exception:
                    errores += 1
            
            messages.success(
                request, 
                f"Proceso de importación finalizado: {creados} creados, "
                f"{actualizados} actualizados, {errores} omitidos por inconsistencias."
            )
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo JSON: {e}")
            
    return redirect('mantenimiento')


# ==========================================
# ENDPOINTS END-API (SOLUCIONES JSON)
# ==========================================

def api_lista_productos(request):
    categoria = request.GET.get('categoria')
    productos = Producto.objects.filter(disponible=True)
    if categoria:
        productos = productos.filter(categoria__nombre__icontains=categoria)
        
    data = []
    for p in productos:
        data.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio': float(p.precio),
            'stock': p.stock,
            'categoria': p.categoria.nombre,
            'marca': p.marca.nombre if p.marca else 'SVCN Style',
            'talla': p.talla.nombre if p.talla else 'Única',
            'color': p.color.nombre if p.color else 'N/A',
            'imagen_url': request.build_absolute_uri(p.imagen.url) if p.imagen else None,
        })
    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})

def api_detalle_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    data = {
        'id': producto.id,
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'precio': float(producto.precio),
        'stock': producto.stock,
        'categoria': producto.categoria.nombre,
        'marca': producto.marca.nombre if producto.marca else 'SVCN Style',
        'talla': producto.talla.nombre if producto.talla else 'Única',
        'color': producto.color.nombre if producto.color else 'N/A',
        'imagen_url': request.build_absolute_uri(producto.imagen.url) if producto.imagen else None,
    }
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})

def api_documentacion(request):
    ejemplo_url = request.build_absolute_uri('/api/productos/')
    return render(request, 'api_docs.html', {'ejemplo_url': ejemplo_url})