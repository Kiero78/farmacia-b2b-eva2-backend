"""
============================================================================
ADMIN.PY - Registro de modelos en el Admin de Django (App 'insumos')
============================================================================
Registra todos los modelos de la app 'insumos' en el panel de administración
de Django. Incluye configuración personalizada para cada modelo con
list_display, filtros, búsqueda e inlines.
============================================================================
"""

from django.contrib import admin
from .models import (
    CategoriaInsumo,
    Insumo,
    Carro,
    ItemCarro,
    Solicitud,
    ItemSolicitud,
)


# ============================================================================
# Admin: CategoriaInsumo
# ============================================================================
@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    """Configuración admin para CategoriaInsumo."""
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


# ============================================================================
# Admin: Insumo
# ============================================================================
@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    """Configuración admin para Insumo."""
    list_display = (
        'nombre_comercial', 'principio_activo', 'categoria',
        'lote', 'fecha_vencimiento', 'precio_unitario', 'stock_cajas'
    )
    list_filter = ('categoria', 'fecha_vencimiento')
    search_fields = ('nombre_comercial', 'principio_activo', 'lote')


# ============================================================================
# Inline: ItemCarro (se muestra dentro del admin de Carro)
# ============================================================================
class ItemCarroInline(admin.TabularInline):
    """
    Inline tabular para mostrar los items dentro del formulario del Carro.
    Permite agregar/editar items directamente desde la vista del Carro.
    extra=0: No muestra formularios vacíos extra por defecto.
    """
    model = ItemCarro
    extra = 0


# ============================================================================
# Admin: Carro
# ============================================================================
@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    """Configuración admin para Carro con items inline."""
    list_display = ('user', 'estado')
    list_filter = ('estado',)
    inlines = [ItemCarroInline]


# ============================================================================
# Inline: ItemSolicitud (se muestra dentro del admin de Solicitud)
# ============================================================================
class ItemSolicitudInline(admin.TabularInline):
    """
    Inline tabular para mostrar los items dentro del formulario de Solicitud.
    readonly_fields evita la edición accidental de precios históricos.
    """
    model = ItemSolicitud
    extra = 0
    readonly_fields = ('precio_unitario_historico',)


# ============================================================================
# Admin: Solicitud
# ============================================================================
@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    """Configuración admin para Solicitud con items inline."""
    list_display = ('pk', 'user', 'estado', 'total', 'creado_en')
    list_filter = ('estado', 'creado_en')
    search_fields = ('user__username',)
    inlines = [ItemSolicitudInline]
    readonly_fields = ('creado_en',)
