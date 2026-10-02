from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from usuarios.models import Tenant, Perfil
from usuarios.permissions import IsSuperAdmin, IsAdminPagina, IsUsuario


class TenantYRolesTests(TestCase):
    """
    Pruebas unitarias y de integración para la arquitectura Multi-Tenant
    y el control de acceso basado en roles (RBAC).
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Crear Tenants
        self.tenant_a = Tenant.objects.create(
            nombre='Hospital Regional de Valparaíso',
            codigo='HOSP-VALP-01',
            rut='60.123.456-7',
            activo=True
        )
        self.tenant_b = Tenant.objects.create(
            nombre='Clínica Metropolitana',
            codigo='CLIN-MET-02',
            rut='76.543.210-K',
            activo=True
        )

        # 2. Crear Usuarios con sus respectivos roles y perfiles
        self.super_user = User.objects.create_user(
            username='super_test',
            password='TestPassword123!',
            email='super@test.cl'
        )
        p_super = self.super_user.perfil
        p_super.rol = 'SUPERADMIN'
        p_super.tenant = self.tenant_a
        p_super.nombre_institucion = 'Ministerio de Salud'
        p_super.save()

        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='TestPassword123!',
            email='admin@test.cl'
        )
        p_admin = self.admin_user.perfil
        p_admin.rol = 'ADMIN_PAGINA'
        p_admin.tenant = self.tenant_a
        p_admin.nombre_institucion = 'Farmacia Hospital Valparaíso'
        p_admin.save()

        self.cliente_user = User.objects.create_user(
            username='cliente_test',
            password='TestPassword123!',
            email='cliente@test.cl'
        )
        p_cliente = self.cliente_user.perfil
        p_cliente.rol = 'USUARIO'
        p_cliente.tenant = self.tenant_a
        p_cliente.nombre_institucion = 'Pabellón Central'
        p_cliente.save()

    def test_tenant_creation_and_str(self):
        """Verifica que el modelo Tenant se cree correctamente y su representación en string sea adecuada."""
        self.assertEqual(str(self.tenant_a), 'Hospital Regional de Valparaíso (HOSP-VALP-01)')
        self.assertTrue(self.tenant_a.activo)

    def test_perfil_role_properties(self):
        """Verifica que las propiedades helper del modelo Perfil funcionen acorde al rol asignado."""
        # Superadmin posee privilegios de superadmin y administración de página
        self.assertTrue(self.super_user.perfil.es_superadmin)
        self.assertTrue(self.super_user.perfil.es_admin_pagina)
        self.assertFalse(self.super_user.perfil.es_usuario)

        # Admin de Página solo administra, no es superadmin global
        self.assertFalse(self.admin_user.perfil.es_superadmin)
        self.assertTrue(self.admin_user.perfil.es_admin_pagina)
        self.assertFalse(self.admin_user.perfil.es_usuario)

        # Usuario común no posee privilegios administrativos
        self.assertFalse(self.cliente_user.perfil.es_superadmin)
        self.assertFalse(self.cliente_user.perfil.es_admin_pagina)
        self.assertTrue(self.cliente_user.perfil.es_usuario)

    def test_jwt_token_claims_include_tenant_and_role(self):
        """Verifica que el endpoint /api/token/ entregue el rol y tenant en la respuesta JSON."""
        response = self.client.post('/api/token/', {
            'username': 'admin_test',
            'password': 'TestPassword123!'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data.get('rol'), 'ADMIN_PAGINA')
        self.assertEqual(data.get('tenant_id'), self.tenant_a.id)
        self.assertEqual(data.get('tenant_codigo'), 'HOSP-VALP-01')
        self.assertEqual(data.get('tenant_nombre'), 'Hospital Regional de Valparaíso')
