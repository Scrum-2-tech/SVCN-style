from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ==========================================
    # RUTAS PÚBLICAS
    # ==========================================
    path('', views.index, name='index'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/lista/', views.lista_productos, name='productos'),
    path('acerca-de/', views.acerca_de, name='acerca_de'),

    # ==========================================
    # AUTENTICACIÓN Y ROLES
    # ==========================================
    path('registro/', views.register, name='register'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('redirect/', views.login_redirect, name='login_redirect'),
    path('vendedor/', views.panel_vendedor, name='panel_vendedor'),

    # ==========================================
    # CARRITO DE COMPRAS
    # ==========================================
    path('carrito/', views.carrito_detalle, name='carrito_detalle'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_producto, name='agregar_producto'),
    path('carrito/add/<int:producto_id>/', views.agregar_producto, name='add'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_carrito, name='actualizar_carrito'),

    # ==========================================
    # PROCESOS DEL CLIENTE
    # ==========================================
    path('compra/procesar/', views.procesar_compra, name='procesar_compra'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedido/<int:pedido_id>/', views.detalle_pedido, name='detalle_pedido'),

    # ==========================================
    # PANEL DE ADMINISTRACIÓN Y REPORTES
    # ==========================================
    path('dashboard/', views.dashboard_stats, name='dashboard_stats'),
    path('dashboard/pedidos/', views.gestion_pedidos, name='gestion_pedidos'),
    
    # Rutas para el cambio logístico de estados (Compatibles con Administrador y Vendedor)
    path('dashboard/pedidos/estado/<int:pedido_id>/<str:nuevo_estado>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('dashboard/pedidos/cambiar-estado/<int:pedido_id>/<str:nuevo_estado>/', views.cambiar_estado_pedido, name='cambiar_estado'),
    
    path('dashboard/inventario/', views.mantenimiento_inventario, name='mantenimiento'),
    path('dashboard/inventario/crear/', views.crear_producto_admin, name='crear_producto_admin'),
    path('dashboard/inventario/nuevo/', views.crear_producto_admin, name='agregar_producto_admin'),
    path('dashboard/inventario/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('dashboard/inventario/eliminar/<int:id>/', views.eliminar_producto_admin, name='eliminar_producto_admin'),
    path('dashboard/usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('dashboard/usuarios/rol/<int:usuario_id>/', views.cambiar_rol, name='cambiar_rol'),

    # ==========================================
    # ADICIÓN DE COMPONENTES DE INVENTARIO
    # ==========================================
    path('dashboard/inventario/color/agregar/', views.agregar_color, name='agregar_color'),
    path('dashboard/inventario/talla/agregar/', views.agregar_talla, name='agregar_talla'),
    path('dashboard/inventario/categoria/agregar/', views.agregar_categoria, name='agregar_categoria'),
    path('dashboard/inventario/marca/agregar/', views.agregar_marca, name='agregar_marca'),
    path('dashboard/inventario/ciudad/agregar/', views.agregar_ciudad, name='agregar_ciudad'),

    # ==========================================
    # ELIMINACIÓN DE COMPONENTES DE INVENTARIO
    # ==========================================
    path('dashboard/inventario/marca/eliminar/<int:id>/', views.eliminar_marca, name='eliminar_marca'),
    path('dashboard/inventario/ciudad/eliminar/<int:id>/', views.eliminar_ciudad, name='eliminar_ciudad'),
    path('dashboard/inventario/color/eliminar/<int:id>/', views.eliminar_color, name='eliminar_color'),
    path('dashboard/inventario/talla/eliminar/<int:id>/', views.eliminar_talla, name='eliminar_talla'),
    path('dashboard/inventario/categoria/eliminar/<int:id>/', views.eliminar_categoria, name='eliminar_categoria'),

    # ==========================================
    # EXPORTACIÓN DE ARCHIVOS (PDF / CSV / JSON)
    # ==========================================
    path('reportes/pedidos/pdf/', views.exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reportes/pedidos/pdf/descargar/', views.exportar_reporte_pdf, name='reporte_pdf'),
    path('reportes/pedidos/csv/', views.exportar_reporte_csv, name='exportar_reporte_csv'),
    path('reportes/pedidos/csv/descargar/', views.exportar_reporte_csv, name='reporte_csv'),
    path('reportes/catalogo/csv/', views.exportar_catalogo_csv, name='exportar_catalogo_csv'),
    path('reportes/catalogo/csv/descargar/', views.exportar_catalogo_csv, name='catalogo_csv'),
    path('reportes/catalogo/pdf/', views.exportar_catalogo_pdf, name='exportar_catalogo_pdf'),
    path('reportes/catalogo/pdf/descargar/', views.exportar_catalogo_pdf, name='catalogo_pdf'),
    path('reportes/catalogo/pdf/<int:categoria_id>/', views.exportar_catalogo_pdf, name='exportar_catalogo_pdf_filtrado'),
    path('reportes/catalogo/pdf/filtrado/<int:categoria_id>/', views.exportar_catalogo_pdf, name='exportar_catalogo_pdf_filtrado'),
    
    path('catalogo-externo/', views.catalogo_externo, name='catalogo_externo'),
    path('dashboard/inventario/plantilla-json/', views.descargar_plantilla_json, name='descargar_plantilla_json'),
    path('dashboard/inventario/importar-json/', views.importar_api, name='importar_api'),

    # ==========================================
    # ENDPOINTS DE LA API JSON
    # ==========================================
    path('api/productos/', views.api_lista_productos, name='api_lista_productos'),
    path('api/productos/<int:id>/', views.api_detalle_producto, name='api_detalle_producto'),
    path('api/docs/', views.api_documentacion, name='api_documentacion'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)