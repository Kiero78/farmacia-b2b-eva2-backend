"""
============================================================================
URLS.PY - Enrutamiento de la App 'usuarios'
============================================================================
Este módulo define las rutas URL para los endpoints de la app 'usuarios':
- Login JWT (obtención de tokens).
- Refresh JWT (renovación de access token).
- Registro de nuevos usuarios.

Convención de URLs:
--------------------
Todas las URLs de esta app se incluirán bajo el prefijo /api/ definido
en el urls.py principal del proyecto. Así las rutas completas serán:
- POST /api/token/          → Login (obtener access + refresh tokens).
- POST /api/token/refresh/  → Refresh (renovar access token).
- POST /api/registro/       → Registro de nuevo usuario.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# path: Función de Django para definir rutas URL.
# Sintaxis: path(ruta, vista, name=nombre_interno)
# - ruta: Patrón de URL (string).
# - vista: Función o clase que maneja la petición.
# - name: Nombre interno para resolver URLs inversas (reverse()).
from django.urls import path

# TokenRefreshView: Vista de SimpleJWT que maneja POST /api/token/refresh/.
# Recibe un refresh token y retorna un nuevo access token.
# No necesitamos personalizarla porque la renovación no requiere
# claims adicionales (los claims se agregan al generar, no al renovar).
from rest_framework_simplejwt.views import TokenRefreshView

# Importamos nuestras vistas personalizadas.
from usuarios.views import (
    CustomTokenObtainPairView,
    RegistroUsuarioView,
)


# ============================================================================
# URL PATTERNS
# ============================================================================
# app_name: Namespace de la app para evitar colisiones de nombres de URL.
# Permite usar 'usuarios:token_obtain' en reverse() en lugar de solo
# 'token_obtain', evitando conflictos con otras apps que tengan URLs
# con el mismo nombre.
app_name = 'usuarios'

# urlpatterns: Lista de rutas URL de esta app.
# Cada path() mapea un patrón de URL a una vista.
urlpatterns = [
    # -----------------------------------------------------------------------
    # Endpoint: Login JWT (obtener tokens)
    # -----------------------------------------------------------------------
    # URL completa: POST /api/token/
    # Vista: CustomTokenObtainPairView (hereda de TokenObtainPairView)
    # Serializador: CustomTokenObtainPairSerializer (con claims de rol)
    #
    # .as_view(): Convierte la clase CBV (Class-Based View) en una función
    # callable que Django puede usar como vista. Es necesario porque
    # urlpatterns espera funciones, no clases.
    #
    # Request:  {"username": "hospital_uc", "password": "pass123"}
    # Response: {"access": "eyJ...", "refresh": "eyJ..."}
    path(
        'token/',
        CustomTokenObtainPairView.as_view(),
        name='token_obtain'
    ),

    # -----------------------------------------------------------------------
    # Endpoint: Refresh JWT (renovar access token)
    # -----------------------------------------------------------------------
    # URL completa: POST /api/token/refresh/
    # Vista: TokenRefreshView (de SimpleJWT, sin personalizar)
    #
    # Cuando el access token expira (después de ACCESS_TOKEN_LIFETIME),
    # el cliente envía su refresh token a este endpoint para obtener
    # un nuevo access token sin necesidad de re-autenticarse.
    #
    # Si ROTATE_REFRESH_TOKENS=True (configurado en settings.py),
    # también retorna un nuevo refresh token.
    #
    # Request:  {"refresh": "eyJ..."}
    # Response: {"access": "eyJ...", "refresh": "eyJ..."} (si rotation=True)
    path(
        'token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    # -----------------------------------------------------------------------
    # Endpoint: Registro de usuarios
    # -----------------------------------------------------------------------
    # URL completa: POST /api/registro/
    # Vista: RegistroUsuarioView (CreateAPIView)
    # Permisos: AllowAny (público)
    #
    # Permite a nuevos usuarios registrarse en el sistema.
    # El serializador hashea el password y crea el perfil automáticamente.
    #
    # Request:  {"username": "...", "password": "...", "email": "...",
    #            "perfil": {"rol": "INSTITUCION", "nombre_institucion": "..."}}
    # Response: 201 Created con los datos del usuario (sin password).
    path(
        'registro/',
        RegistroUsuarioView.as_view(),
        name='registro'
    ),
]
