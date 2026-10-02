"""
============================================================================
URLS.PY - Enrutamiento de la App 'insumos'
============================================================================
Este módulo define las rutas URL para los endpoints de la app 'insumos'.
Utiliza el DefaultRouter de DRF para generar automáticamente las URLs
de los ViewSets, y rutas explícitas para las vistas del carrito.

DefaultRouter de DRF:
----------------------
El Router es una herramienta de DRF que genera automáticamente las URL
patterns para los ViewSets registrados. Por cada ViewSet registrado,
el Router crea las siguientes rutas:

    Prefijo/{pk}/  → GET (retrieve), PUT (update), PATCH, DELETE (destroy)
    Prefijo/       → GET (list), POST (create)

Además, si el ViewSet tiene acciones @action, el Router genera
rutas adicionales:
    Prefijo/{pk}/accion/  → Para acciones con detail=True
    Prefijo/accion/       → Para acciones con detail=False

DefaultRouter vs SimpleRouter:
- DefaultRouter: Agrega una vista raíz que lista todas las URLs registradas.
  Útil para exploración de la API. URL raíz: /api/
- SimpleRouter: No agrega la vista raíz. Más limpio en producción.

Rutas generadas por este módulo:
----------------------------------
Router (automáticas):
  GET    /api/categorias/                           → Lista categorías
  POST   /api/categorias/                           → Crear categoría (GESTOR)
  GET    /api/categorias/{id}/                      → Detalle categoría
  PUT    /api/categorias/{id}/                      → Actualizar categoría (GESTOR)
  DELETE /api/categorias/{id}/                      → Eliminar categoría (GESTOR)

  GET    /api/insumos/                              → Lista insumos (con filtros)
  POST   /api/insumos/                              → Crear insumo (GESTOR)
  GET    /api/insumos/{id}/                         → Detalle insumo
  PUT    /api/insumos/{id}/                         → Actualizar insumo (GESTOR)
  DELETE /api/insumos/{id}/                         → Eliminar insumo (GESTOR)

  GET    /api/solicitudes/                          → Lista solicitudes (filtrada por rol)
  GET    /api/solicitudes/{id}/                     → Detalle solicitud
  POST   /api/solicitudes/confirmar/                → Confirmar carrito (INSTITUCION)
  PATCH  /api/solicitudes/{id}/cambiar-estado/      → Cambiar estado (GESTOR)

Explícitas (manuales):
  GET    /api/carro/                                → Ver carrito activo (INSTITUCION)
  DELETE /api/carro/                                → Vaciar carrito (INSTITUCION)
  POST   /api/carro/items/                          → Agregar item (INSTITUCION)
  PUT    /api/carro/items/{item_id}/                → Modificar cantidad (INSTITUCION)
  DELETE /api/carro/items/{item_id}/                → Eliminar item (INSTITUCION)

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# path: Función de Django para definir rutas URL explícitas.
from django.urls import path, include

# DefaultRouter: Router de DRF que genera URLs automáticas para ViewSets.
from rest_framework.routers import DefaultRouter

# Importamos los ViewSets y vistas de la app 'insumos'.
from insumos.views import (
    CategoriaInsumoViewSet,
    InsumoViewSet,
    CarroView,
    ItemCarroView,
    SolicitudViewSet,
    RecetaMedicaViewSet,
)


# ============================================================================
# CONFIGURACIÓN DEL ROUTER
# ============================================================================
# Creamos una instancia del DefaultRouter.
# El Router mantiene un registro de ViewSets y genera las URL patterns.
router = DefaultRouter()

# -----------------------------------------------------------------------
# Registro de ViewSets en el Router
# -----------------------------------------------------------------------
# router.register(prefijo, viewset, basename):
#
# - prefijo: Segmento de URL para este ViewSet.
#   'categorias' → /api/categorias/ y /api/categorias/{pk}/
#
# - viewset: Clase del ViewSet a registrar.
#
# - basename: Nombre base para las URLs generadas (para reverse()).
#   Si el ViewSet tiene 'queryset', basename se infiere del modelo.
#   Lo definimos explícitamente por claridad:
#   - basename='categoria' genera nombres: categoria-list, categoria-detail
#   - basename='insumo' genera: insumo-list, insumo-detail
#   - basename='solicitud' genera: solicitud-list, solicitud-detail,
#     solicitud-confirmar, solicitud-cambiar-estado

# Categorías de insumos médicos
router.register(
    r'categorias',          # Prefijo URL: /api/categorias/
    CategoriaInsumoViewSet, # ViewSet que maneja las peticiones
    basename='categoria'    # Nombre base para reverse()
)

# Insumos médicos (catálogo)
router.register(
    r'insumos',             # Prefijo URL: /api/insumos/
    InsumoViewSet,          # ViewSet con filtros y búsqueda
    basename='insumo'       # Nombre base para reverse()
)

# Solicitudes de pedido
router.register(
    r'solicitudes',         # Prefijo URL: /api/solicitudes/
    SolicitudViewSet,       # ViewSet con acciones custom
    basename='solicitud'    # Nombre base para reverse()
)

# Auditoría de recetas médicas (Tenant Admin / Superadmin)
router.register(
    r'recetas',             # Prefijo URL: /api/recetas/
    RecetaMedicaViewSet,    # ViewSet para auditar recetas
    basename='receta'       # Nombre base para reverse()
)


# ============================================================================
# URL PATTERNS
# ============================================================================
# app_name: Namespace de la app para evitar colisiones.
app_name = 'insumos'

urlpatterns = [
    # -----------------------------------------------------------------------
    # URLs generadas automáticamente por el Router
    # -----------------------------------------------------------------------
    # include(router.urls): Incluye TODAS las URLs generadas por el Router
    # en un solo path. Esto equivale a listar manualmente cada URL del CRUD
    # para cada ViewSet, pero de forma automática y menos propensa a errores.
    #
    # El Router genera URLs como:
    #   categorias/          → CategoriaInsumoViewSet (list, create)
    #   categorias/<pk>/     → CategoriaInsumoViewSet (retrieve, update, destroy)
    #   insumos/             → InsumoViewSet (list, create)
    #   insumos/<pk>/        → InsumoViewSet (retrieve, update, destroy)
    #   solicitudes/         → SolicitudViewSet (list)
    #   solicitudes/<pk>/    → SolicitudViewSet (retrieve)
    #   solicitudes/confirmar/ → SolicitudViewSet.confirmar (custom action)
    #   solicitudes/<pk>/cambiar-estado/ → SolicitudViewSet.cambiar_estado
    path('', include(router.urls)),

    # -----------------------------------------------------------------------
    # URLs explícitas del carrito (no son ViewSet, son APIView)
    # -----------------------------------------------------------------------
    # El carrito no usa ViewSet porque su lógica no es CRUD estándar:
    # - GET/DELETE sobre el carrito como unidad (CarroView).
    # - POST/PUT/DELETE sobre items individuales (ItemCarroView).
    # Por eso definimos las rutas manualmente con path().

    # GET /api/carro/ → Ver carrito activo
    # DELETE /api/carro/ → Vaciar carrito
    path(
        'carro/',
        CarroView.as_view(),
        name='carro'
    ),

    # POST /api/carro/items/ → Agregar item al carrito
    path(
        'carro/items/',
        ItemCarroView.as_view(),
        name='carro-items'
    ),

    # PUT /api/carro/items/{item_id}/ → Modificar cantidad de un item
    # DELETE /api/carro/items/{item_id}/ → Eliminar un item del carrito
    #
    # <int:item_id>: Captura un parámetro numérico de la URL.
    # - <int:...>: Converter que acepta solo números enteros positivos.
    # - item_id: Nombre del parámetro que se pasa a la vista como kwarg.
    # Django pasa este valor al método de la vista: put(request, item_id=5)
    path(
        'carro/items/<int:item_id>/',
        ItemCarroView.as_view(),
        name='carro-item-detalle'
    ),

    # Aliases exactos según la Matriz de Evaluación
    path(
        'carro-insumos/',
        CarroView.as_view(),
        name='carro-insumos'
    ),
    path(
        'carro-insumos/items/',
        ItemCarroView.as_view(),
        name='carro-insumos-items'
    ),
    path(
        'carro-insumos/items/<int:item_id>/',
        ItemCarroView.as_view(),
        name='carro-insumos-item-detalle'
    ),
    path(
        'mis-solicitudes/',
        SolicitudViewSet.as_view({'get': 'list'}),
        name='mis-solicitudes'
    ),
]
