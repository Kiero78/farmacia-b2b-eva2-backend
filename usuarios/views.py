"""
============================================================================
VIEWS.PY - App 'usuarios'
============================================================================
Este módulo define las vistas de la API para la app 'usuarios'.
Incluye la vista personalizada de obtención de tokens JWT y la vista
de registro de nuevos usuarios.

Vistas definidas:
------------------
- CustomTokenObtainPairView: Login JWT con claims personalizados.
- RegistroUsuarioView: Registro público de nuevos usuarios.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# generics: Módulo de DRF con vistas genéricas que implementan patrones
# CRUD comunes. CreateAPIView maneja automáticamente POST requests
# para crear nuevos objetos.
from rest_framework import generics

# AllowAny: Permiso que permite acceso a CUALQUIER usuario, incluso
# no autenticados. Se usa para endpoints públicos como registro y login.
from rest_framework.permissions import AllowAny

# TokenObtainPairView: Vista de SimpleJWT que maneja POST /api/token/.
# Recibe username + password, valida credenciales y retorna tokens JWT.
# La heredamos para usar nuestro serializador personalizado.
from rest_framework_simplejwt.views import TokenObtainPairView

# Importamos nuestros serializadores personalizados.
from usuarios.serializers import (
    CustomTokenObtainPairSerializer,
    RegistroUsuarioSerializer,
)


# ============================================================================
# VISTA: CustomTokenObtainPairView (Login JWT)
# ============================================================================
# Vista personalizada para el endpoint de login (POST /api/token/).
# Hereda de TokenObtainPairView de SimpleJWT y usa nuestro
# CustomTokenObtainPairSerializer que agrega claims de rol al token.
#
# Flujo:
# 1. Cliente envía POST /api/token/ con {"username": "...", "password": "..."}
# 2. SimpleJWT valida las credenciales contra la tabla auth_user.
# 3. Si son válidas, CustomTokenObtainPairSerializer genera los tokens
#    con claims personalizados (user_id, username, email, rol).
# 4. Responde con {"access": "<jwt_token>", "refresh": "<jwt_token>"}.
# 5. Si son inválidas, responde con 401 Unauthorized.
# ============================================================================
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista de login JWT con claims personalizados.

    Endpoint: POST /api/token/
    Permisos: AllowAny (público, no requiere autenticación).
    Serializador: CustomTokenObtainPairSerializer.

    Request body:
        {"username": "hospital_uc", "password": "MiPassword123"}

    Response 200 OK:
        {"access": "eyJ0eXAi...", "refresh": "eyJ0eXAi..."}

    Response 401 Unauthorized:
        {"detail": "No active account found with the given credentials"}
    """
    # serializer_class: Apunta a nuestro serializador personalizado.
    # Esto sobrescribe el serializador por defecto de TokenObtainPairView
    # para incluir los claims adicionales (user_id, username, email, rol)
    # en el payload del access token.
    serializer_class = CustomTokenObtainPairSerializer


# ============================================================================
# VISTA: RegistroUsuarioView (Registro público)
# ============================================================================
# Vista para registrar nuevos usuarios en el sistema.
# Usa CreateAPIView, una vista genérica de DRF que:
# 1. Acepta solo peticiones POST.
# 2. Deserializa y valida los datos con el serializador especificado.
# 3. Llama a serializer.save() → ejecuta create() del serializador.
# 4. Responde con 201 Created y los datos del objeto creado.
#
# Es un endpoint PÚBLICO (AllowAny) porque los usuarios necesitan
# registrarse ANTES de poder autenticarse.
# ============================================================================
class RegistroUsuarioView(generics.CreateAPIView):
    """
    Vista de registro de nuevos usuarios.

    Endpoint: POST /api/registro/
    Permisos: AllowAny (público, no requiere autenticación).
    Serializador: RegistroUsuarioSerializer.

    Request body:
        {
            "username": "hospital_uc",
            "password": "MiPassword123",
            "email": "admin@hospitaluc.cl",
            "first_name": "Juan",
            "last_name": "Pérez",
            "perfil": {
                "rol": "INSTITUCION",
                "nombre_institucion": "Hospital Clínico UC"
            }
        }

    Response 201 Created:
        {
            "username": "hospital_uc",
            "email": "admin@hospitaluc.cl",
            "first_name": "Juan",
            "last_name": "Pérez",
            "perfil": {
                "rol": "INSTITUCION",
                "nombre_institucion": "Hospital Clínico UC"
            }
        }

    Response 400 Bad Request:
        {"username": ["A user with that username already exists."]}
    """
    # serializer_class: Serializador que maneja la creación del usuario
    # con hashing de password y creación del perfil.
    serializer_class = RegistroUsuarioSerializer

    # permission_classes: Lista de permisos requeridos.
    # AllowAny permite acceso sin autenticación.
    # Se define como lista para poder ser extendido fácilmente.
    permission_classes = [AllowAny]
