"""
============================================================================
URLS.PY - Enrutamiento Principal del Proyecto farmacia_b2b
============================================================================
Este es el archivo de enrutamiento RAÍZ del proyecto Django.
Todas las peticiones HTTP pasan por aquí antes de ser redirigidas
a las URLs de las apps específicas.

Estructura de URLs:
--------------------
/admin/              → Panel de administración de Django.
/api/                → Prefijo para TODOS los endpoints de la API REST.
  /api/token/        → Login JWT (obtener tokens).
  /api/token/refresh/→ Refresh JWT (renovar access token).
  /api/registro/     → Registro público de usuarios.
  /api/categorias/   → CRUD de categorías (Router).
  /api/insumos/      → CRUD de insumos con filtros (Router).
  /api/carro/        → Carrito de compras (INSTITUCION).
  /api/solicitudes/  → Solicitudes de pedido (Router + acciones custom).
  /api/docs/         → Documentación Swagger UI (drf-spectacular).
  /api/schema/       → Schema OpenAPI 3.0 en formato JSON/YAML.

Fallback 404 JSON:
-------------------
Al final de urlpatterns se incluye un re_path con regex catch-all (r'^.*$')
que captura CUALQUIER ruta que no coincida con las anteriores y retorna
una respuesta JSON uniforme con status 404.

¿Por qué un fallback JSON personalizado?
Django por defecto retorna páginas HTML para errores 404.
En una API REST pura (sin frontend Django), el cliente espera
SIEMPRE respuestas JSON, incluso para errores.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

"""
============================================================================
URLS.PY - Enrutamiento Principal del Proyecto farmacia_b2b
============================================================================
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.http import JsonResponse

# Importamos las vistas web (templates)
from insumos.views import catalogo_web, carro_web, solicitudes_web, login_web


def fallback_404(request):
    """
    Fallback 404 en formato JSON para endpoints que no existan.
    """
    return JsonResponse(
        {
            'error': 'Ruta no encontrada',
            'detalle': 'El recurso solicitado no existe en la API de farmacia B2B',
        },
        status=404
    )


urlpatterns = [
    # -----------------------------------------------------------------------
    # Vistas Web Institucionales (Templates HTML)
    # -----------------------------------------------------------------------
    path('', catalogo_web, name='catalogo_web'),
    path('login/', login_web, name='login_web'),
    path('carro/', carro_web, name='carro_web'),
    path('solicitudes/', solicitudes_web, name='solicitudes_web'),

    # -----------------------------------------------------------------------
    # Panel de administración de Django
    # -----------------------------------------------------------------------
    path('admin/', admin.site.urls),

    # -----------------------------------------------------------------------
    # APIs REST
    # -----------------------------------------------------------------------
    path('api/', include('usuarios.urls')),
    path('api/', include('insumos.urls')),

    # -----------------------------------------------------------------------
    # Documentación Swagger / OpenAPI
    # -----------------------------------------------------------------------
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Servir archivos multimedia (recetas subidas) en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# -----------------------------------------------------------------------
# FALLBACK CATCH-ALL JSON (Debe ir estrictamente al final)
# -----------------------------------------------------------------------
urlpatterns += [
    re_path(r'^.*$', fallback_404, name='fallback-404'),
]