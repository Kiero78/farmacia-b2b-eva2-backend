"""
============================================================================
SERIALIZERS.PY - App 'usuarios'
============================================================================
Este módulo define los serializadores para la app de usuarios.
Los serializadores en Django REST Framework (DRF) cumplen dos funciones:

1. SERIALIZACIÓN: Convertir objetos Python (instancias de modelos Django)
   a tipos de datos nativos de Python (dict, list, str, int, etc.) que
   luego se pueden renderizar fácilmente en JSON, XML u otros formatos.
   Dirección: Model → Dict → JSON (respuesta HTTP).

2. DESERIALIZACIÓN: Convertir datos recibidos (JSON del request) a tipos
   Python validados, que luego se pueden usar para crear/actualizar
   instancias de modelos en la base de datos.
   Dirección: JSON → Dict → Validación → Model (guardado en BD).

Serializadores definidos en este módulo:
-----------------------------------------
- CustomTokenObtainPairSerializer: Personaliza el token JWT para incluir
  claims adicionales (user_id, username, email, rol).
- PerfilSerializer: Serializa el modelo Perfil (rol, nombre_institucion).
- UsuarioSerializer: Serializa el modelo User con su Perfil anidado.
- RegistroUsuarioSerializer: Maneja el registro de nuevos usuarios con
  creación automática del perfil y hashing seguro de contraseña.

Autor: Equipo EVA-2
Fecha: Octubre 2026
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# serializers: Módulo de DRF que provee las clases base para definir
# serializadores. Similar a los formularios de Django (forms.py) pero
# orientados a APIs REST en lugar de HTML.
from rest_framework import serializers

# TokenObtainPairSerializer: Serializador base de SimpleJWT que maneja
# la autenticación por usuario/contraseña y genera el par de tokens
# (access + refresh). Lo heredamos para agregar claims personalizados
# al payload del access token.
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# User: Modelo de usuario nativo de Django. Lo serializamos para exponer
# los datos del usuario en la API (id, username, email, first_name, last_name).
from django.contrib.auth.models import User

# Perfil y Tenant: Modelos de la app usuarios
from usuarios.models import Perfil, Tenant


# ============================================================================
# SERIALIZADOR: TenantSerializer
# ============================================================================
class TenantSerializer(serializers.ModelSerializer):
    """
    Serializador para la entidad Tenant / Farmacia / Clínica.
    """
    class Meta:
        model = Tenant
        fields = ['id', 'nombre', 'codigo', 'rut', 'direccion', 'telefono', 'activo', 'creado_en']


# ============================================================================
# SERIALIZADOR: CustomTokenObtainPairSerializer
# ============================================================================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializador personalizado para la obtención de tokens JWT.
    Enriquece tanto el payload del access token como la respuesta JSON
    con el Rol del usuario y su pertenencia al Tenant.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        perfil = getattr(user, 'perfil', None)
        token['user_id'] = user.id
        token['username'] = user.username
        token['email'] = user.email

        if perfil:
            token['rol'] = perfil.rol
            token['tenant_id'] = perfil.tenant_id if perfil.tenant else None
            token['tenant_codigo'] = perfil.tenant.codigo if perfil.tenant else 'global'
            token['tenant_nombre'] = perfil.tenant.nombre if perfil.tenant else 'Global'
        else:
            token['rol'] = 'USUARIO'
            token['tenant_id'] = None
            token['tenant_codigo'] = 'global'
            token['tenant_nombre'] = 'Global'

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        perfil = getattr(self.user, 'perfil', None)
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['rol'] = perfil.rol if perfil else 'USUARIO'
        data['tenant_id'] = perfil.tenant_id if (perfil and perfil.tenant) else None
        data['tenant_nombre'] = perfil.tenant.nombre if (perfil and perfil.tenant) else 'Global'
        data['tenant_codigo'] = perfil.tenant.codigo if (perfil and perfil.tenant) else 'global'
        return data


# ============================================================================
# SERIALIZADOR: PerfilSerializer
# ============================================================================
class PerfilSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Perfil con soporte Multi-Tenant.
    """
    tenant_detalle = TenantSerializer(source='tenant', read_only=True)

    class Meta:
        model = Perfil
        fields = ['rol', 'nombre_institucion', 'tenant', 'tenant_detalle']


# ============================================================================
# SERIALIZADOR: UsuarioSerializer
# ============================================================================
# Serializa el modelo User de Django junto con su Perfil anidado.
# Se usa para las vistas de consulta/actualización del usuario.
#
# Características:
# - Incluye campos del User nativo (id, username, email, first_name, last_name).
# - Incluye el Perfil como serializador anidado (PerfilSerializer).
# - El campo 'perfil' es de solo lectura en este serializador; las
#   actualizaciones del perfil se manejan por separado.
# ============================================================================
class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo User con Perfil anidado.

    Combina los datos del User nativo de Django con los datos del
    Perfil personalizado en una sola respuesta JSON.

    Ejemplo de respuesta:
    {
        "id": 1,
        "username": "hospital_uc",
        "email": "admin@hospitaluc.cl",
        "first_name": "Juan",
        "last_name": "Pérez",
        "perfil": {
            "rol": "INSTITUCION",
            "nombre_institucion": "Hospital Clínico UC"
        }
    }
    """

    # -----------------------------------------------------------------------
    # Campo anidado: perfil
    # -----------------------------------------------------------------------
    # PerfilSerializer(read_only=True): Incluye los datos del Perfil como
    # un objeto JSON anidado dentro de la respuesta del usuario.
    #
    # read_only=True: Este campo solo se incluye en las respuestas (GET).
    # No se espera ni se valida en los requests de entrada (POST/PUT).
    # Las actualizaciones del perfil se manejan a través de un endpoint
    # separado o del RegistroUsuarioSerializer.
    #
    # DRF resuelve la relación automáticamente: accede a user.perfil
    # (gracias al related_name='perfil' en el OneToOneField) y lo
    # serializa usando PerfilSerializer.
    perfil = PerfilSerializer(read_only=True)

    class Meta:
        model = User
        # Campos expuestos del modelo User:
        # - id: PK del usuario (útil para el frontend como identificador).
        # - username: Nombre de usuario único para login.
        # - email: Correo electrónico.
        # - first_name, last_name: Nombre completo del usuario.
        # - perfil: Objeto anidado con rol y nombre_institucion.
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'perfil']


# ============================================================================
# SERIALIZADOR: RegistroUsuarioSerializer
# ============================================================================
# Maneja el proceso de registro de nuevos usuarios en el sistema.
# Este serializador es más complejo porque necesita:
# 1. Recibir datos del User (username, password, email).
# 2. Recibir datos del Perfil (rol, nombre_institucion).
# 3. Crear ambos objetos en la base de datos de forma coordinada.
# 4. Hashear la contraseña de forma segura (NUNCA almacenar texto plano).
#
# Flujo del registro:
# 1. Frontend envía POST /api/registro/ con JSON:
#    {
#        "username": "hospital_uc",
#        "password": "MiPasswordSeguro123",
#        "email": "admin@hospitaluc.cl",
#        "first_name": "Juan",
#        "last_name": "Pérez",
#        "perfil": {
#            "rol": "INSTITUCION",
#            "nombre_institucion": "Hospital Clínico UC"
#        }
#    }
# 2. DRF deserializa y valida los datos con este serializador.
# 3. El método create() crea el User (con password hasheado) y actualiza
#    el Perfil (que ya fue creado por la señal post_save).
# 4. Responde con los datos del usuario creado (sin el password).
# ============================================================================
class RegistroUsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro de nuevos usuarios.

    Recibe username, password, email, nombre y datos del perfil.
    Crea el User con contraseña hasheada y actualiza su Perfil.
    """

    # -----------------------------------------------------------------------
    # Campo: password (write_only)
    # -----------------------------------------------------------------------
    # write_only=True: El campo se acepta en el INPUT (POST request)
    # pero NUNCA se incluye en el OUTPUT (respuesta JSON).
    # Esto es CRÍTICO para seguridad: nunca se debe exponer el password
    # en las respuestas de la API, ni siquiera hasheado.
    #
    # style={'input_type': 'password'}: En el Browsable API de DRF,
    # renderiza el campo como <input type="password"> (oculta los caracteres).
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    # -----------------------------------------------------------------------
    # Campo anidado: perfil (para escritura)
    # -----------------------------------------------------------------------
    # PerfilSerializer(): Sin read_only, permite recibir datos del perfil
    # en el request de registro.
    #
    # required=False: El perfil es opcional en el registro. Si no se envía,
    # se usarán los valores por defecto del modelo Perfil:
    # - rol = 'INSTITUCION'
    # - nombre_institucion = ''
    #
    # Esto permite registros simples: solo username + password + email,
    # y el perfil se puede completar después.
    perfil = PerfilSerializer(required=False)

    class Meta:
        model = User
        # Campos aceptados en el registro:
        # - username: Requerido, único. Nombre de usuario para login.
        # - password: Requerido, write_only. Se hashea antes de guardar.
        # - email: Requerido para comunicaciones.
        # - first_name, last_name: Opcionales. Nombre completo.
        # - perfil: Opcional. Objeto con rol y nombre_institucion.
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'perfil']

    # -----------------------------------------------------------------------
    # Método: create (sobrescrito)
    # -----------------------------------------------------------------------
    # Este método se invoca cuando se llama a serializer.save() después
    # de una validación exitosa (serializer.is_valid()).
    #
    # Sobrescribimos create() porque el proceso de creación de usuario
    # requiere lógica especial:
    # 1. Extraer datos del perfil del validated_data.
    # 2. Crear el User con create_user() (que hashea el password).
    # 3. Actualizar el Perfil creado por la señal post_save.
    #
    # NO usamos User.objects.create() directamente porque ese método
    # almacena el password en TEXTO PLANO. User.objects.create_user()
    # aplica el algoritmo de hashing configurado (por defecto PBKDF2
    # con SHA256, 720,000 iteraciones en Django 5.x).
    # -----------------------------------------------------------------------
    def create(self, validated_data):
        """
        Crea un nuevo User con contraseña hasheada y actualiza su Perfil.

        Args:
            validated_data: Diccionario con los datos ya validados por DRF.
                Ejemplo: {
                    'username': 'hospital_uc',
                    'password': 'MiPasswordSeguro123',
                    'email': 'admin@hospitaluc.cl',
                    'first_name': 'Juan',
                    'last_name': 'Pérez',
                    'perfil': {'rol': 'INSTITUCION', 'nombre_institucion': 'Hospital UC'}
                }

        Returns:
            User: Instancia del User recién creado.
        """
        # Paso 1: Extraer los datos del perfil del validated_data.
        # .pop('perfil', {}) extrae la clave 'perfil' del diccionario y la
        # retorna. Si no existe, retorna {} (diccionario vacío).
        # El pop() REMUEVE la clave del diccionario original, lo cual es
        # necesario porque User.objects.create_user() no acepta 'perfil'
        # como argumento (no es un campo del modelo User).
        perfil_data = validated_data.pop('perfil', {})

        # Paso 2: Extraer el password del validated_data.
        # Similar a perfil, se extrae porque create_user() recibe el
        # password como argumento separado (no como **kwargs).
        password = validated_data.pop('password')

        # Paso 3: Crear el User con create_user().
        # User.objects.create_user() es un método especial del UserManager
        # de Django que:
        # 1. Crea la instancia del User con los datos proporcionados.
        # 2. Llama a user.set_password(password), que:
        #    a. Genera un salt aleatorio (valor random para evitar rainbow tables).
        #    b. Aplica PBKDF2-SHA256 con 720,000 iteraciones.
        #    c. Almacena el hash en formato: algorithm$iterations$salt$hash
        #    d. Ejemplo: pbkdf2_sha256$720000$abc123...$xyz789...
        # 3. Guarda el user en la base de datos (INSERT INTO auth_user).
        #
        # **validated_data desempaqueta el diccionario restante como kwargs:
        # username='hospital_uc', email='admin@hospitaluc.cl', etc.
        user = User.objects.create_user(password=password, **validated_data)

        # Paso 4: Actualizar el Perfil con los datos recibidos.
        # La señal post_save ya creó un Perfil con valores por defecto
        # cuando se ejecutó user.save() dentro de create_user().
        # Ahora actualizamos ese Perfil con los datos del request.
        #
        # Solo actualizamos si se enviaron datos de perfil (perfil_data no vacío).
        if perfil_data:
            # Accedemos al perfil del usuario: user.perfil
            # (gracias al related_name='perfil' del OneToOneField).
            perfil = user.perfil

            # Iteramos sobre los datos del perfil y los asignamos dinámicamente.
            # setattr(obj, attr, value) es equivalente a obj.attr = value.
            # Esto permite actualizar cualquier campo del perfil sin
            # hardcodear los nombres de los campos.
            # Ejemplo: setattr(perfil, 'rol', 'INSTITUCION')
            #          equivale a: perfil.rol = 'INSTITUCION'
            for attr, value in perfil_data.items():
                setattr(perfil, attr, value)

            # Guardar los cambios del perfil en la base de datos (UPDATE).
            perfil.save()

        # Paso 5: Retornar la instancia del User creado.
        # DRF usará el serializador para convertir este User a JSON
        # y enviarlo en la respuesta HTTP 201 Created.
        return user
