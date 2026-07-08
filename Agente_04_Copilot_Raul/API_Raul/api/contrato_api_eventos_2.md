# Contrato de la API — "idioma común"

**Proyecto:** Gestión de eventos y ponentes
**Versión:** 2 (borrador para cerrar en el kickoff)
**Objetivo:** que app, IA y base de datos hablen el mismo idioma. Cerrar esto al principio permite que los 3 equipos (frontend, backend/BD, data science) trabajen en paralelo sin bloquearse.

> **Cómo se lee cada endpoint:** `MÉTODO /ruta` → qué hace.
> `GET` = pedir datos · `POST` = crear · `PUT`/`PATCH` = actualizar · `DELETE` = borrar.
> Todo viaja en formato JSON.
> Este documento es la **fuente de verdad**. Cualquier cambio se avisa al grupo y sube la versión.

---

## 1. Convenciones generales (acordar ANTES de picar código)

Estas reglas evitan el 80% de los líos de integración. Conviene cerrarlas todas.

### 1.1 Formato de datos
- Todo entra y sale en **JSON**, codificado en **UTF-8** (importante: acentos, ñ, euskera — se guarda y se sirve en UTF-8 siempre).
- **Fechas:** `AAAA-MM-DD` (ej. `2026-07-14`).
- **Fecha con hora:** formato ISO `AAAA-MM-DDTHH:MM:SS` (ej. `2026-07-14T10:00:00`).
- **Horas sueltas:** `HH:MM` (24h).
- **Dinero:** número con dos decimales, en euros, sin símbolo (ej. `6700.00`). Nunca texto como `"6.700 €"`.
- **Booleanos:** `true` / `false`, nunca `"sí"`/`"no"`.
- **Nombres de campos:** en minúsculas y con guion bajo (`fecha_inicio`, no `fechaInicio` ni `FechaInicio`). Acordar y respetar.

### 1.2 Identificadores y relaciones
- Cada recurso tiene un `id` numérico único.
- Las relaciones se referencian por ese id (ej. un pedido lleva `evento_id` y `proveedor_id`).
- Los ids los genera la base de datos, no la app ni la IA.

### 1.3 Estados
- Los estados usan palabras fijas y cerradas (lista en cada sección), en minúsculas y sin espacios (ej. `pre-evento`, `pendiente-pago`).
- Nunca texto libre en un campo de estado.

### 1.4 Códigos de respuesta HTTP
Acuerdo mínimo para que el front sepa qué ha pasado sin adivinar:

| Código | Significa | Cuándo |
|---|---|---|
| `200` | OK | Petición correcta (GET, PUT) |
| `201` | Creado | Un POST creó algo nuevo |
| `400` | Petición mal formada | Faltan campos o formato incorrecto |
| `401` | No autenticado | No hay sesión / token válido |
| `403` | Sin permiso | Autenticado pero no puede hacer eso (ej. ponente tocando datos de admin) |
| `404` | No encontrado | El id no existe |
| `409` | Conflicto | Ej. asignar un ponente ya asignado |
| `500` | Error del servidor | Fallo interno |

### 1.5 Formato de error (único para toda la API)
Cuando algo va mal, la respuesta **siempre** tiene esta forma:
```json
{
  "error": true,
  "codigo": "CAMPO_OBLIGATORIO",
  "mensaje": "El campo 'nombre' es obligatorio.",
  "detalles": { "campo": "nombre" }
}
```
- `codigo`: identificador corto y estable, para que el front reaccione (no depende del idioma del mensaje).
- `mensaje`: texto legible para mostrar o depurar.
- `detalles`: opcional, información extra.

### 1.6 Listados: paginación, filtro y orden
Los endpoints que devuelven listas aceptan estos parámetros en la URL:
- `?pagina=1&por_pagina=20` → paginación.
- `?buscar=texto` → búsqueda libre.
- `?estado=confirmado` → filtro por campo.
- `?orden=fecha_inicio&dir=asc` → ordenación.

Y responden envolviendo la lista con metadatos:
```json
{
  "datos": [ /* ...los elementos... */ ],
  "pagina": 1,
  "por_pagina": 20,
  "total": 47
}
```

### 1.7 La IA no escribe directa
Regla de oro de todo el sistema: los agentes **leen** con los mismos `GET` que la app, y lo que **proponen** queda en estado `borrador` / `pendiente de validación`. Ninguna acción con efecto real (enviar email, confirmar pedido, pagar) la ejecuta la IA sola: siempre la aprueba un humano.

---

## 2. Autenticación y roles

Para la demo no hace falta seguridad de banco, pero sí acordar la regla.

| Puerta | Qué hace |
|---|---|
| `POST /auth/login` | Entrar. Devuelve un token de sesión y el rol |
| `POST /auth/logout` | Cerrar sesión |
| `GET /auth/yo` | Devuelve los datos del usuario que ha iniciado sesión |

**Ejemplo de respuesta del login:**
```json
{
  "token": "abc123...",
  "usuario": { "id": 8, "nombre": "Admin Demo", "rol": "admin" }
}
```
Roles posibles: `admin` (gestiona todo) · `ponente` (solo ve y edita lo suyo).

> El token se manda en cada petición en la cabecera `Authorization: Bearer <token>`.
> Reglas de permiso: un `ponente` solo accede a su propia ficha y su evento; un `admin` accede a todo.

---

## 3. Eventos

| Puerta | Qué hace | Respuesta |
|---|---|---|
| `GET /eventos` | Lista de eventos (paginada) | Lista envuelta (ver 1.6) |
| `GET /eventos/{id}` | Detalle de un evento | Objeto evento |
| `POST /eventos` | Crear un evento | `201` + evento creado |
| `PUT /eventos/{id}` | Editar un evento | `200` + evento actualizado |
| `DELETE /eventos/{id}` | Cancelar/borrar un evento | `200` + confirmación |

**Objeto evento:**
```json
{
  "id": 1,
  "nombre": "Congreso Anual Industria",
  "cliente": "Cámara de Comercio",
  "tipo": "congreso",
  "num_personas": 320,
  "fecha_inicio": "2026-07-14",
  "fecha_fin": "2026-07-15",
  "estado": "pre-evento",
  "lugar_id": 5,
  "creado_en": "2026-06-30T09:00:00"
}
```
- Estados del evento: `borrador`, `pre-evento`, `en-curso`, `finalizado`, `cancelado`.
- Al crear, `nombre` y `cliente` son obligatorios; el resto puede ir vacío y completarse luego.

---

## 4. Lugar

| Puerta | Qué hace | Respuesta |
|---|---|---|
| `GET /lugares` | Buscar lugares (acepta `?buscar=`) | Lista envuelta |
| `GET /lugares/{id}` | Detalle de un lugar con sus servicios | Objeto lugar |
| `POST /eventos/{id}/lugar` | Asignar un lugar a un evento | `201` + asignación |
| `POST /lugares/{id}/contactar` | Pedir el lugar por email para una fecha (genera solicitud) | `201` + solicitud |

**Objeto lugar:**
```json
{
  "id": 5,
  "nombre": "Palacio Kursaal",
  "zona": "Donostia",
  "capacidad": 600,
  "valoracion": 4.6,
  "servicios_disponibles": ["catering", "parking", "wifi", "luces", "sonido"]
}
```

**Objeto lugar asignado (dentro de un evento):**
```json
{
  "evento_id": 1,
  "lugar_id": 5,
  "fecha_inicio": "2026-07-14",
  "fecha_fin": "2026-07-15",
  "presupuesto": 6700.00,
  "estado": "confirmado",
  "servicios_incluidos": ["catering", "parking", "wifi"]
}
```
Estados de la asignación de lugar: `propuesto`, `contactado`, `confirmado`, `descartado`.

---

## 5. Audiovisuales / Servicios (proveedores y pedidos)

| Puerta | Qué hace | Respuesta |
|---|---|---|
| `GET /proveedores` | Buscar proveedores (acepta `?buscar=` y `?tipo=`) | Lista envuelta |
| `GET /eventos/{id}/proveedores` | Proveedores asociados a un evento | Lista |
| `POST /eventos/{id}/proveedores/{prov_id}/contratar` | Contratar un proveedor para el evento | `201` |
| `POST /eventos/{id}/pedidos` | Generar un pedido a un proveedor contratado | `201` + pedido |
| `GET /eventos/{id}/pedidos` | Ver los pedidos del evento | Lista |
| `PUT /pedidos/{id}/confirmar` | Confirmar pedido y fijar coste definitivo | `200` + pedido |

**Objeto pedido:**
```json
{
  "id": 12,
  "evento_id": 1,
  "proveedor_id": 7,
  "proveedor_nombre": "Video y Streaming SL",
  "necesidades": ["pantalla LED 4x3", "streaming en directo"],
  "estado": "generado",
  "coste_estimado": 4600.00,
  "coste_definitivo": null
}
```
Estados del pedido: `generado`, `pendiente`, `confirmado`, `cancelado`.
> Al confirmar (`PUT .../confirmar`) es obligatorio mandar `coste_definitivo`.

---

## 6. Presupuesto

| Puerta | Qué hace | Respuesta |
|---|---|---|
| `GET /eventos/{id}/presupuesto` | Presupuesto del evento con partidas y desviaciones | Objeto presupuesto |
| `PUT /eventos/{id}/presupuesto` | Actualizar partidas presupuestadas | `200` |

**Objeto presupuesto:**
```json
{
  "evento_id": 1,
  "total_presupuestado": 27000.00,
  "total_ejecutado": 21100.00,
  "dias_restantes": 8,
  "partidas": [
    { "nombre": "Espacio",      "presupuestado": 6700.00, "ejecutado": 6160.00 },
    { "nombre": "Catering",     "presupuestado": 5500.00, "ejecutado": 5500.00 },
    { "nombre": "Técnica / AV", "presupuestado": 4600.00, "ejecutado": 5430.00 },
    { "nombre": "Viajes",       "presupuestado": 4300.00, "ejecutado": 4010.00 }
  ]
}
```
> La **desviación** de cada partida (`ejecutado − presupuestado`) y su color (verde/rojo) los calcula la app a partir de estos números. La API solo da los datos crudos.

---

## 7. Ponentes

| Puerta | Qué hace | Respuesta |
|---|---|---|
| `GET /eventos/{id}/ponentes` | Ponentes de un evento (dashboard, paginado) | Lista envuelta |
| `GET /ponentes/{id}` | Ficha detalle de un ponente | Objeto ponente |
| `POST /ponentes` | Crear un ponente nuevo | `201` |
| `POST /eventos/{id}/ponentes` | Asignar un ponente existente a un evento | `201` |
| `PUT /ponentes/{id}` | Editar ficha | `200` |
| `GET /ponentes/{id}/documentos` | Documentos del ponente y su estado | Lista |
| `POST /ponentes/{id}/documentos` | Subir un documento | `201` |
| `GET /ponentes/{id}/viajes` | Logística de viaje del ponente | Objeto viajes |
| `GET /ponentes/{id}/facturacion` | Datos y estado de facturación | Objeto facturación |

**Objeto ponente (resumido, para el dashboard):**
```json
{
  "id": 3,
  "nombre": "Ane Etxeberria",
  "empresa": "Tecnalia",
  "rol": "keynote",
  "estado": "confirmado",
  "documentacion": "completa",
  "ponencia": { "sala": "A", "hora": "10:00" },
  "viajes": "cerrado",
  "facturacion": "pendiente-pago"
}
```

**Objeto documento:**
```json
{
  "id": 40,
  "ponente_id": 3,
  "tipo": "cv",
  "estado": "recibido",
  "archivo_url": "/archivos/cv_ane.pdf"
}
```

Listas de estados (cerradas):
- Ponente: `invitado`, `pendiente`, `confirmado`, `cancelado`.
- Documentación (resumen): `completa`, `incompleta`, `sin-iniciar`.
- Documento individual: `pendiente`, `recibido`, `en-revision`, `rechazado`.
- Viajes: `sin-iniciar`, `en-gestion`, `cerrado`.
- Facturación: `sin-datos`, `pendiente-pago`, `pagada`.
- Tipos de documento: `cv`, `foto`, `presentacion`, `autorizacion-imagen`, `ficha-tecnica`.

---

## 8. Endpoints que usa la IA (agentes)

Los agentes **leen** con los `GET` de las secciones anteriores. Lo que **proponen** entra por estos, y queda pendiente de validación humana.

| Puerta | Qué hace | Respuesta |
|---|---|---|
| `POST /borradores` | Un agente guarda un borrador de comunicación (no se envía) | `201` |
| `GET /borradores?evento={id}` | El admin ve los borradores pendientes | Lista |
| `PUT /borradores/{id}/aprobar` | Un humano aprueba (y entonces se envía) | `200` |
| `PUT /borradores/{id}/rechazar` | Un humano descarta el borrador | `200` |
| `POST /bloqueos` | Un agente marca un problema (falta doc, sin confirmar…) | `201` |
| `GET /eventos/{id}/bloqueos` | Ver los bloqueos activos del evento | Lista |
| `POST /briefing/analizar` | Sube un resumen (PDF/DOC) → devuelve campos del evento rellenos | Objeto briefing |

**Objeto borrador (comunicación propuesta por la IA):**
```json
{
  "id": 21,
  "evento_id": 1,
  "ponente_id": 3,
  "tipo": "recordatorio-documentacion",
  "asunto": "Falta tu presentación para el congreso",
  "cuerpo": "Hola Ane, te recordamos que...",
  "estado": "pendiente-validacion",
  "generado_por": "agente-comunicacion"
}
```

**Objeto bloqueo (problema detectado por la IA):**
```json
{
  "id": 5,
  "evento_id": 1,
  "ponente_id": 4,
  "motivo": "falta-autorizacion-imagen",
  "gravedad": "alta",
  "detectado_por": "agente-documental"
}
```

**Respuesta del briefing autocompletado:**
```json
{
  "campos": {
    "nombre": "Congreso Anual Industria",
    "cliente": "Cámara de Comercio",
    "tipo": "congreso",
    "num_personas": 320,
    "fecha_inicio": "2026-07-14",
    "fecha_fin": "2026-07-15"
  },
  "confianza": "alta",
  "avisos": ["No se encontró la fecha de fin con seguridad."]
}
```
> Regla clave: la IA **propone**, el humano **decide**. El objeto viene con `confianza` y `avisos` justo para que la persona revise antes de aceptar. Nada se envía, se paga ni se confirma sin validación.

---

## 9. Modelo de datos (guía para BD y para "crear datos")

Las entidades principales y cómo se relacionan. Sirve para que el equipo de base de datos y el de datos de prueba trabajen alineados con esta misma estructura.

- **Evento** — nombre, cliente, tipo, fechas, estado. Se relaciona con un **Lugar**.
- **Lugar** — nombre, zona, capacidad, servicios disponibles.
- **Ponente** — datos personales, empresa, rol. Existe por sí mismo.
- **Ponente_Evento** — la relación entre un ponente y un evento (un ponente puede ir a varios eventos, y un evento tiene varios ponentes). Aquí viven el estado, la ponencia (sala/hora), etc.
- **Documento** — pertenece a un ponente. Tipo y estado.
- **Viaje / Logística** — pertenece a un Ponente_Evento.
- **Facturación** — pertenece a un Ponente_Evento.
- **Proveedor** — empresa de servicios (AV, catering…). Existe por sí mismo.
- **Pedido** — relaciona un evento con un proveedor. Coste estimado y definitivo.
- **Borrador** y **Bloqueo** — generados por la IA, ligados a evento (y a veces a ponente).

> Relación clave a no olvidar: **ponente y evento se unen a través de `Ponente_Evento`**, no directamente. Es lo que permite que un mismo ponente tenga historial en varios eventos.

---

## 10. Checklist para cerrar en el kickoff

- [ ] De acuerdo con las convenciones generales (sección 1): formato, UTF-8, nombres de campos, códigos HTTP, formato de error, paginación.
- [ ] De acuerdo con las rutas y los nombres de campos de cada sección.
- [ ] Listas de estados revisadas y cerradas.
- [ ] Regla de autenticación y permisos (admin/ponente) acordada.
- [ ] Modelo de datos (sección 9) validado por el equipo de BD.
- [ ] Documento subido al repositorio como versión 2.
- [ ] Cada equipo sabe qué endpoints **consume** y cuáles **construye**.
- [ ] Acordado cómo se avisan los cambios futuros del contrato.

---

## Notas de uso

- Esto es un **punto de partida**, no un dogma. Los nombres de campos y rutas son una propuesta razonable; ajustadlos a lo que ya teníais en vuestros documentos, sobre todo en la parte de ponentes.
- No hace falta construir todos los endpoints para la demo. Priorizad los que sostienen la historia: crear evento → ver ponentes → la IA ayuda → presupuesto.
- Mantener este documento actualizado es más importante que tenerlo perfecto: si algo cambia en el código, que cambie aquí el mismo día.
