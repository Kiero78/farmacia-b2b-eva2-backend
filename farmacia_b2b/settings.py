"""
============================================================================
SETTINGS.PY - Configuración principal del proyecto farmacia_b2b
============================================================================
Este archivo contiene toda la configuración del proyecto Django para el
sistema de "Pedidos de Insumos Médicos y Farmacia (Salud / B2B)".

Secciones principales:
1. Imports y lectura de variables de entorno (.env)
2. Seguridad (SECRET_KEY, DEBUG, ALLOWED_HOSTS)
3. Aplicaciones instaladas (INSTALLED_APPS)
4. Middleware
5. Configuración de base de datos PostgreSQL
6. Configuración de Django REST Framework (DRF)
7. Configuración de SimpleJWT (autenticación por tokens)
8. Configuración de drf-spectacular (documentación OpenAPI)
9. Internacionalización y zona horaria

Autor: Equipo EVA-2
Fecha: Septiembre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================
from pathlib import Path  # Manejo de rutas multiplataforma (Windows/Linux/Mac)
from datetime import timedelta  # Para definir la duración de los tokens JWT

# python-decouple: Función 'config' lee variables del archivo .env
# Esto permite separar credenciales y configuración sensible del código fuente,
# siguiendo el principio de los 12 factores (https://12factor.net/config).
# Parámetro 'cast' convierte el valor string a otro tipo (ej: bool).
# Parámetro 'default' establece un valor por defecto si la variable no existe.
from decouple import config

# ============================================================================
# RUTAS BASE DEL PROYECTO
# ============================================================================
# BASE_DIR: Ruta absoluta al directorio raíz del proyecto.
# Path(__file__) = ruta de este archivo (settings.py)
# .resolve() = convierte a ruta absoluta
# .parent = sube un nivel (de farmacia_b2b/ a la raíz)
# .parent = sube otro nivel (del directorio del proyecto a la raíz)
BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================================
# SEGURIDAD
# ============================================================================

# SECRET_KEY: Clave secreta utilizada por Django para:
# - Firmar cookies de sesión
# - Generar tokens CSRF (Cross-Site Request Forgery)
# - Hashing de contraseñas
# NUNCA debe exponerse en código fuente ni en repositorios públicos.
# Se lee desde .env usando python-decouple para mantenerla segura.
SECRET_KEY = config('SECRET_KEY')

# DEBUG: Modo de depuración.
# True  → Muestra errores detallados con traceback completo (SOLO desarrollo).
# False → Muestra páginas de error genéricas (producción).
# cast=bool convierte el string "True"/"False" del .env a tipo booleano Python.
# default=False asegura que si no existe la variable, el modo debug está OFF
# (principio de seguridad: "fail secure").
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS: Lista de dominios/IPs desde los que Django acepta peticiones.
# En desarrollo con DEBUG=True, Django permite localhost automáticamente.
# En producción se deben listar los dominios reales del servidor.
# '*' permite cualquier host (SOLO para desarrollo, NUNCA en producción).
ALLOWED_HOSTS = ['*']


# ============================================================================
# APLICACIONES INSTALADAS (INSTALLED_APPS)
# ============================================================================
# Django busca modelos, migraciones, archivos estáticos y templates en cada
# app registrada aquí. El orden puede importar para resolución de dependencias.
INSTALLED_APPS = [
    # -----------------------------------------------------------------------
    # Apps nativas de Django (incluidas por defecto)
    # -----------------------------------------------------------------------
    'django.contrib.admin',         # Panel de administración de Django
    'django.contrib.auth',          # Sistema de autenticación (User, permisos)
    'django.contrib.contenttypes',  # Framework de tipos de contenido (requerido por auth)
    'django.contrib.sessions',      # Manejo de sesiones del lado del servidor
    'django.contrib.messages',      # Framework de mensajes (flash messages)
    'django.contrib.staticfiles',   # Servicio de archivos estáticos (CSS, JS, imgs)

    # -----------------------------------------------------------------------
    # Apps de terceros
    # -----------------------------------------------------------------------
    'rest_framework',               # Django REST Framework: toolkit para APIs REST
    'django_filters',               # django-filter: filtrado declarativo de querysets
    'drf_spectacular',              # Documentación OpenAPI 3.0 automática (Swagger/ReDoc)

    # -----------------------------------------------------------------------
    # Apps propias del proyecto
    # -----------------------------------------------------------------------
    # 'usuarios': Gestión de perfiles de usuario con roles
    # (Institución Médica / Gestor de Bodega). Extiende el modelo User de Django
    # mediante un Perfil OneToOne.
    'usuarios',

    # 'insumos': Núcleo del negocio B2B. Gestiona el catálogo de insumos
    # médicos, el carrito de compras, y las solicitudes de pedido con su
    # ciclo de vida (PENDIENTE → PAGADO → ENTREGADO / CANCELADO).
    'insumos',
]


# ============================================================================
# MIDDLEWARE
# ============================================================================
# Los middlewares son capas de procesamiento que interceptan cada request/response.
# Se ejecutan en orden de arriba hacia abajo para requests,
# y de abajo hacia arriba para responses.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',        # Cabeceras de seguridad HTTP (HSTS, etc.)
    'django.contrib.sessions.middleware.SessionMiddleware',  # Manejo de sesiones
    'django.middleware.common.CommonMiddleware',             # Normalización de URLs (trailing slash, etc.)
    'django.middleware.csrf.CsrfViewMiddleware',            # Protección contra CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Asocia usuario autenticado al request
    'django.contrib.messages.middleware.MessageMiddleware',  # Soporte para mensajes flash
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Protección contra clickjacking (X-Frame-Options)
]


# ============================================================================
# CONFIGURACIÓN DE URLS Y WSGI
# ============================================================================
# ROOT_URLCONF: Módulo Python donde Django busca las URL patterns raíz.
ROOT_URLCONF = 'farmacia_b2b.urls'

# TEMPLATES: Configuración del motor de plantillas.
# Aunque en una API REST pura no se usan templates HTML extensivamente,
# Django Admin y las páginas de error las necesitan.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI_APPLICATION: Punto de entrada para servidores WSGI (Gunicorn, uWSGI).
# WSGI = Web Server Gateway Interface, el estándar Python para servir apps web.
WSGI_APPLICATION = 'farmacia_b2b.wsgi.application'


# ============================================================================
# BASE DE DATOS - PostgreSQL
# ============================================================================
# Configuración de la conexión a PostgreSQL usando python-decouple.
# Cada parámetro se lee del archivo .env para no exponer credenciales.
#
# PostgreSQL fue elegido por:
# - Soporte completo de transacciones ACID (Atomicidad, Consistencia,
#   Aislamiento, Durabilidad), crítico para operaciones financieras/inventario.
# - Integridad referencial robusta con claves foráneas.
# - Tipos de datos avanzados (JSONB, arrays, rangos).
# - Escalabilidad y rendimiento en entornos de producción.
DATABASES = {
    'default': {
        # ENGINE: Driver de base de datos. 'django.db.backends.postgresql'
        # utiliza psycopg2 (instalado como psycopg2-binary) para comunicarse
        # con PostgreSQL mediante el protocolo nativo.
        'ENGINE': 'django.db.backends.postgresql',

        # NAME: Nombre de la base de datos. Debe existir en PostgreSQL antes
        # de ejecutar las migraciones (CREATE DATABASE farmacia_b2b;).
        'NAME': config('DB_NAME'),

        # USER: Usuario de PostgreSQL con permisos CRUD sobre la base de datos.
        'USER': config('DB_USER'),

        # PASSWORD: Contraseña del usuario. Se lee del .env por seguridad.
        'PASSWORD': config('DB_PASSWORD'),

        # HOST: Dirección del servidor PostgreSQL.
        # 'localhost' para desarrollo local.
        'HOST': config('DB_HOST', default='localhost'),

        # PORT: Puerto TCP de PostgreSQL (por defecto 5432).
        # Se lee como string porque Django lo espera así.
        'PORT': config('DB_PORT', default='5432'),
    }
}


# ============================================================================
# VALIDADORES DE CONTRASEÑA
# ============================================================================
# Django valida las contraseñas de los usuarios contra estos validadores
# para garantizar seguridad mínima. Se aplican al crear/cambiar contraseñas.
AUTH_PASSWORD_VALIDATORS = [
    {
        # Verifica que la contraseña no sea similar al nombre de usuario,
        # email u otros atributos del usuario.
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        # Exige una longitud mínima (por defecto 8 caracteres).
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        # Rechaza contraseñas comunes (lista de ~20,000 contraseñas frecuentes).
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        # Rechaza contraseñas que sean completamente numéricas.
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ============================================================================
# INTERNACIONALIZACIÓN Y ZONA HORARIA
# ============================================================================
# LANGUAGE_CODE: Idioma por defecto de Django (mensajes de error, admin, etc.).
# 'es' = español, lo que hace que el admin y los mensajes se muestren en español.
LANGUAGE_CODE = 'es'

# TIME_ZONE: Zona horaria del servidor.
# 'America/Santiago' = Chile continental (UTC-3 / UTC-4 según horario de verano).
# Django almacena fechas en UTC en la BD y las convierte a esta zona para mostrar.
TIME_ZONE = 'America/Santiago'

# USE_I18N: Activa el sistema de internacionalización (traducciones).
USE_I18N = True

# USE_TZ: Activa el soporte de zonas horarias (timezone-aware datetimes).
# Con True, Django almacena datetimes en UTC y los convierte al mostrar.
# Esto evita problemas con cambios de horario y comparaciones de fechas.
USE_TZ = True


# ============================================================================
# ARCHIVOS ESTÁTICOS
# ============================================================================
# STATIC_URL: Prefijo URL para servir archivos estáticos (CSS, JS, imágenes).
# En producción, estos archivos deben ser servidos por Nginx/Apache, no Django.
STATIC_URL = 'static/'

# MEDIA_URL y MEDIA_ROOT: Manejo de archivos subidos por usuarios (Recetas Médicas, etc.)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# DEFAULT_AUTO_FIELD: Tipo de campo por defecto para las claves primarias
# auto-generadas de los modelos. BigAutoField usa BIGINT (64 bits),
# soportando hasta 9.2 × 10^18 registros (más que suficiente).
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================================
# CONFIGURACIÓN DE DJANGO REST FRAMEWORK (DRF)
# ============================================================================
# Esta sección centraliza la configuración global de DRF.
# Cada opción define el comportamiento por defecto para TODAS las vistas API.
REST_FRAMEWORK = {
    # -----------------------------------------------------------------------
    # DEFAULT_AUTHENTICATION_CLASSES
    # -----------------------------------------------------------------------
    # Define cómo DRF autentica las peticiones entrantes.
    # JWTAuthentication: Valida tokens JWT enviados en el header
    # 'Authorization: Bearer <token>'. Es stateless (no requiere sesiones
    # en el servidor), lo que permite escalar horizontalmente.
    # SessionAuthentication: Permite autenticación por sesión/cookie,
    # útil para el Browsable API de DRF y el Django Admin.
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),

    # -----------------------------------------------------------------------
    # DEFAULT_FILTER_BACKENDS
    # -----------------------------------------------------------------------
    # Define los backends de filtrado disponibles globalmente.
    # DjangoFilterBackend: Permite filtrar querysets usando parámetros GET.
    # Ejemplo: GET /api/insumos/?categoria=1&stock_cajas__gte=10
    # Se configura por vista con 'filterset_fields' o 'filterset_class'.
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),

    # -----------------------------------------------------------------------
    # DEFAULT_SCHEMA_CLASS
    # -----------------------------------------------------------------------
    # Define la clase que genera el esquema OpenAPI para la documentación.
    # AutoSchema de drf-spectacular genera documentación OpenAPI 3.0
    # automáticamente a partir de los serializadores y vistas.
    # Esto habilita Swagger UI y ReDoc para explorar la API interactivamente.
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',)
}


# ============================================================================
# CONFIGURACIÓN DE SIMPLE JWT
# ============================================================================
# SimpleJWT genera dos tipos de tokens:
# - Access Token: Token de corta duración para autenticar peticiones.
# - Refresh Token: Token de larga duración para obtener nuevos access tokens
#   sin necesidad de enviar usuario/contraseña nuevamente.
#
# Flujo de autenticación:
# 1. Cliente envía POST /api/token/ con username y password.
# 2. Servidor responde con {access: "...", refresh: "..."}.
# 3. Cliente usa access token en header: Authorization: Bearer <access_token>.
# 4. Cuando access token expira, envía POST /api/token/refresh/ con refresh token.
# 5. Servidor responde con nuevo access token.
SIMPLE_JWT = {
    # ACCESS_TOKEN_LIFETIME: Duración del access token.
    # 60 minutos es un balance entre seguridad (tokens de corta duración
    # limitan la ventana de ataque si son interceptados) y usabilidad
    # (el usuario no tiene que re-autenticarse constantemente).
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),

    # REFRESH_TOKEN_LIFETIME: Duración del refresh token.
    # 1 día permite al usuario mantener su sesión durante una jornada
    # laboral completa sin necesidad de volver a iniciar sesión.
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),

    # ROTATE_REFRESH_TOKENS: Si es True, cada vez que se usa el refresh
    # token para obtener un nuevo access token, también se genera un
    # nuevo refresh token. Esto mejora la seguridad porque cada refresh
    # token es de un solo uso.
    'ROTATE_REFRESH_TOKENS': True,

    # BLACKLIST_AFTER_ROTATION: Si es True (requiere 'rest_framework_simplejwt.token_blacklist'
    # en INSTALLED_APPS), los refresh tokens rotados se agregan a una lista negra,
    # invalidándolos completamente. Previene la reutilización de tokens rotados.
    # Desactivado por simplicidad; activar si se requiere seguridad adicional.
    'BLACKLIST_AFTER_ROTATION': False,

    # AUTH_HEADER_TYPES: Prefijo esperado en el header Authorization.
    # 'Bearer' es el estándar RFC 6750 para tokens OAuth 2.0 / JWT.
    # El cliente debe enviar: Authorization: Bearer eyJ0eXAiOiJKV1Qi...
    'AUTH_HEADER_TYPES': ('Bearer',),

    # TOKEN_OBTAIN_SERIALIZER: Serializador personalizado para la vista
    # de obtención de tokens (POST /api/token/).
    # Apunta a nuestro CustomTokenObtainPairSerializer en la app 'usuarios',
    # que agrega claims personalizados al payload del access token:
    # user_id, username, email y rol (INSTITUCION/GESTOR).
    # Estos claims viajan dentro del token JWT y pueden ser decodificados
    # por el frontend para mostrar información del usuario sin hacer
    # peticiones adicionales al backend.
    'TOKEN_OBTAIN_SERIALIZER': 'usuarios.serializers.CustomTokenObtainPairSerializer',
}


# ============================================================================
# CONFIGURACIÓN DE DRF-SPECTACULAR (Documentación OpenAPI)
# ============================================================================
# drf-spectacular genera automáticamente documentación interactiva de la API
# en formato OpenAPI 3.0, accesible vía Swagger UI (/api/docs/) y ReDoc.
#
# Esta documentación permite a los desarrolladores frontend:
# - Explorar todos los endpoints disponibles
# - Ver los schemas de request/response
# - Probar la API directamente desde el navegador
SPECTACULAR_SETTINGS = {
    'TITLE': 'Farmacia B2B API | CENABAST',
    'DESCRIPTION': (
        '### Sistema de Abastecimiento Clínico Institucional\n'
        'API REST para la intermediación, gestión de pedidos e inventario de insumos clínicos y fármacos.\n\n'
        '---\n'
        '**Identificación del Alumno (EVA-2)**\n'
        '* **Estudiante:** Vicente Pablo Flores Araneda\n'
        '* **Sección:** AP-N4-C1/D\n'
        '* **Año:** 2026\n'
        '* **Modelo:** B2B Institucional (Red asistencial / Hospitales / Clínicas)\n'
        '---\n\n'
        '**Roles del Sistema:**\n'
        '* `GESTOR`: Control de inventario, vademécum y despacho en Bodega Central.\n'
        '* `INSTITUCION`: Programación de pedidos, carro de insumos y seguimiento de compras.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'filter': True,  # Barra de búsqueda arriba
        'defaultModelsExpandDepth': -1,  # Esconde los esquemas gigantes de abajo para que no ensucie la vista
        'syntaxHighlight.theme': 'nord',  # Tema nórdico elegante y sobrio para los JSON
    },
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}