# CENABAST B2B — Plataforma de Pedidos de Insumos Médicos y Farmacia

**Evaluación:** Prueba Backend 2 (EVA-2) — Año 2026  
**Proyecto Asignado:** Proyecto 5: Pedidos de Insumos Médicos y Farmacia (Salud / B2B)  
**Estudiante:** Vicente Pablo Flores Araneda  
**Sección:** AP-N4-C1/D  
**Docente:** Evaluación Académica  

---

## 1. Descripción del Proyecto

Sistema empresarial B2B para la gestión, abastecimiento y auditoría de medicamentos e insumos clínicos hospitalarios en la red de salud. Implementa una arquitectura **Multi-Tenant** con control de acceso jerárquico basado en roles (RBAC), control estricto de recetas médicas para fármacos antibióticos y controlados, auditoría farmacéutica con aprobación/denegación de compras, y gestión de stock transaccional atómica bajo **PostgreSQL** mediante transacciones ACID y bloqueos pesimistas (`select_for_update`).

---

## 2. Arquitectura y Modelo de Dominio

### A. Multi-Tenant
El sistema permite segmentar el inventario, los usuarios y las solicitudes por entidad o prestador de salud mediante el modelo `Tenant`:
- `Tenant`: Código (`codigo`), Razón Social (`nombre`), `rut`, dirección, teléfono y estado activo.
- Cada insumo, usuario y solicitud queda contextualizado dentro de su respectivo `Tenant`.

### B. Jerarquía de Roles (`ROL_CHOICES`)
1. **`SUPERADMIN`**:
   - Acceso global e irrestricto a todos los tenants de la red.
   - Acceso completo a Django Admin y Swagger API.
2. **`ADMIN_PAGINA`** (Farmacéutico Auditor / Gestor de Bodega):
   - Administra el catálogo de su tenant.
   - Revisa y audita las prescripciones médicas de las órdenes en estado `EN_REVISION`.
   - Aprueba la venta (descontando stock atómicamente) o deniega la compra (cancelando la orden sin afectar stock).
   - Controla el inventario y despachos (`ENTREGADO`, `CANCELADO`).
3. **`USUARIO`** (Institución Médica / Comprador Clínico):
   - Explora el vademécum de insumos y fármacos.
   - Gestiona su programación de compras (Carro de Compras).
   - Registra solicitudes y adjunta antecedentes de receta médica cuando el fármaco lo exige.

---

## 3. Flujo Clínico de Recetas Médicas y Control de Stock

```mermaid
flowchart TD
    A[Usuario agrega insumos al Carro] --> B{¿Requiere Receta Médica?}
    B -- No (Venta Libre) --> C[Confirmar Solicitud]
    C --> D[Descuento atómico de stock select_for_update]
    D --> E[Estado: PAGADO / Aprobado]
    
    B -- Sí (Antibióticos / Controlados) --> F[Ingreso de Folio y Médico Prescriptor]
    F --> G[Confirmar Solicitud]
    G --> H[Estado: EN REVISION de Receta]
    H --> I[Stock NO se descuenta inmediatamente]
    I --> J[Admin de Página / Farmacéutico examina Receta]
    
    J --> K{Decisión del Farmacéutico}
    K -- APROBAR VENTA --> L[Validación y descuento atómico de stock]
    L --> M[Receta: APROBADA | Solicitud: PAGADO]
    
    K -- DENEGAR COMPRA --> N[Cancelación de Orden sin descuento de stock]
    N --> O[Receta: RECHAZADA | Solicitud: CANCELADO]
```

### Tipos de Venta de Fármacos (`TIPO_VENTA_CHOICES`)
- `LIBRE`: Venta y despacho inmediato (ej: Paracetamol, Ibuprofeno, Guantes Quirúrgicos).
- `RECETA_SIMPLE`: Requiere prescripción médica válida (ej: Amoxicilina + Ácido Clavulánico, Ciprofloxacino).
- `RECETA_RETENIDA`: Psicotrópicos y estupefacientes sujetos a control y retención de receta (ej: Clonazepam, Morfina).

---

## 4. Stack Tecnológico

- **Lenguaje:** Python 3.11+
- **Framework Web & ORM:** Django 5.x
- **API REST:** Django REST Framework (DRF) 3.15+
- **Base de Datos:** PostgreSQL 14+ (Driver nativo `psycopg2-binary`)
- **Autenticación:** JWT con `djangorestframework-simplejwt`
- **Documentación de API:** OpenAPI 3.0 & Swagger UI mediante `drf-spectacular`
- **Frontend / UI:** Django Templates + Bootstrap 5 + Bootstrap Icons + Fetch API (SPA híbrida con JWT)

---

## 5. Endpoints de la API REST

### Autenticación y Cuentas
- `POST /api/token/`: Obtención de JWT `access` y `refresh` (incluye rol y tenant en payload).
- `POST /api/token/refresh/`: Renovación de access token expirado.
- `POST /api/registro/`: Registro de nuevos usuarios institucionales.

### Catálogo y Carrito
- `GET /api/categorias/`: Listado de categorías de insumos.
- `GET /api/insumos/`: Listado de insumos con filtros de categoría, búsqueda y tipo de venta.
- `GET /api/carro/` ó `GET /api/carro-insumos/`: Consulta del carro institucional activo.
- `POST /api/carro/items/` ó `POST /api/carro-insumos/`: Agregar/actualizar items en el carro.
- `DELETE /api/carro/`: Vaciar carro de compras.

### Solicitudes y Auditoría Farmacéutica
- `POST /api/solicitudes/confirmar/`: Convierte el carro en Solicitud formal.
- `GET /api/solicitudes/` ó `GET /api/mis-solicitudes/`: Trazabilidad de órdenes.
- `POST /api/solicitudes/{id}/revisar-receta/`: Auditoría médica (`decision`: `APROBAR` o `DENEGAR`).
- `POST /api/solicitudes/{id}/subir-receta/`: Registro/actualización de antecedentes de receta médica.
- `PATCH /api/solicitudes/{id}/estado/`: Transición de estado (`ENTREGADO`, `CANCELADO`).

### Documentación Interactiva
- `GET /api/docs/`: Interfaz gráfica interactiva de Swagger UI (pública).
- `GET /api/schema/`: Esquema OpenAPI 3.0 descargable.

---

## 6. Credenciales de Prueba Preconfiguradas

| Rol | Usuario | Contraseña | Privilegios / Alcance |
| :--- | :--- | :--- | :--- |
| **SUPERADMIN** | `superadmin` | `SuperAdmin2026!` | Acceso global multi-tenant, Django Admin y Swagger |
| **ADMIN_PAGINA** | `admin_farmacia` | `AdminFarmacia2026!` | Farmacéutico auditor, aprobación/denegación de recetas y stock |
| **USUARIO** | `hospital_uc` | `Cliente1234!` | Compras B2B, carro institucional y carga de recetas |
| **GESTOR** | `gestor_bodega` | `Admin1234!` | Alias operativo para gestión y despacho |

---

## 7. Instalación y Puesta en Marcha

### 1. Clonar el repositorio y configurar variables de entorno
```bash
git clone <URL_DEL_REPOSITORIO>
cd farmacia_b2b
cp .env.example .env
```
Configurar en `.env` las credenciales de conexión a PostgreSQL (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).

### 2. Crear y activar entorno virtual
```bash
python -m venv venv
# En Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Aplicar migraciones en PostgreSQL
```bash
python manage.py migrate
```

### 5. Poblar la base de datos con datos de demostración
```bash
python manage.py seed_db
```

### 6. Ejecutar la suite de pruebas automatizadas
```bash
python manage.py test
```
*Todas las pruebas unitarias y de integración se ejecutan contra PostgreSQL verificando el 100% de los flujos de negocio.*

### 7. Iniciar el servidor de desarrollo
```bash
python manage.py runserver
```
- **Portal Web Institucional:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Documentación Swagger UI:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **Panel Administrativo:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
