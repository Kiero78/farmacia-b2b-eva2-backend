"""
============================================================================
APPS.PY - Configuración de la app 'usuarios'
============================================================================
Este archivo configura la aplicación 'usuarios' dentro del proyecto Django.
La clase UsuariosConfig hereda de AppConfig y define metadatos de la app.

El método ready() es CLAVE: se ejecuta una sola vez cuando Django carga
la app, y aquí se importan las señales (signals) definidas en models.py.
Sin este import, la señal post_save que crea el Perfil automáticamente
NO se registraría y no funcionaría.
============================================================================
"""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """
    Configuración de la app 'usuarios'.

    Atributos:
    - default_auto_field: Tipo de PK por defecto para los modelos de esta app.
    - name: Nombre de la app (debe coincidir con el directorio).
    - verbose_name: Nombre legible que aparece en el admin de Django.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'
    verbose_name = 'Gestión de Usuarios'

    def ready(self):
        """
        Método ready(): Se ejecuta cuando Django termina de cargar esta app.

        Aquí importamos el módulo de modelos para que las señales definidas
        con el decorador @receiver se registren correctamente.

        Sin este import explícito, Django NO conectaría la señal post_save
        con la función crear_perfil_usuario, y los perfiles no se crearían
        automáticamente al crear nuevos usuarios.

        Nota: Se importa dentro del método (no al inicio del archivo) para
        evitar imports circulares que podrían ocurrir durante la carga
        del framework.
        """
        import usuarios.models  # noqa: F401 - Registra las señales post_save
