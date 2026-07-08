# API — Gestión de eventos y ponentes (Flask)

API del proyecto, hecha con Flask. Implementa los endpoints del contrato "idioma común".

**Importante:** ahora mismo funciona sobre **datos de prueba en memoria** (archivo `datos.py`), así que arranca sin necesitar PostgreSQL. Es ideal para que:
- el equipo de **frontend** conecte las pantallas desde el primer día, y
- el equipo de **base de datos** monte PostgreSQL en paralelo sin bloquear a nadie.

Cuando la BD real esté lista, solo hay que reescribir `datos.py` para que lea/escriba en PostgreSQL. **Los endpoints (`app.py`) no cambian.**

---

## Cómo arrancar

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Arrancar la API:
```bash
python app.py
```

3. Comprobar que está viva. Abre en el navegador o con curl:
```
http://localhost:5000/
http://localhost:5000/eventos
```

---

## Estructura de archivos

| Archivo | Qué es |
|---|---|
| `app.py` | Todos los endpoints. Esta es la API. |
| `datos.py` | La "base de datos" en memoria (datos de prueba). **Lo que se sustituye por PostgreSQL.** |
| `requirements.txt` | Dependencias. |
| `README.md` | Este archivo. |

---

## Cómo pasar de datos de prueba a PostgreSQL

Toda la lógica de acceso a datos está aislada en `datos.py`, en 6 funciones:
`listar`, `obtener`, `crear`, `actualizar`, `borrar`, `filtrar`.

El equipo de BD solo tiene que reescribir esas 6 funciones para que hablen con
PostgreSQL (con `psycopg2` o un ORM como SQLAlchemy), manteniendo los mismos
nombres y lo que devuelven. `app.py` seguirá funcionando sin tocar una línea.

Es la ventaja de haber separado las capas: la API no sabe (ni le importa) si
los datos vienen de memoria o de una base de datos real.

---

## Endpoints principales

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/auth/login` | Iniciar sesión (usa `admin@demo.eus` / `1234`) |
| GET | `/eventos` | Listar eventos |
| POST | `/eventos` | Crear evento |
| GET | `/eventos/{id}` | Detalle de evento |
| GET | `/eventos/{id}/ponentes` | Ponentes del evento (dashboard) |
| GET | `/eventos/{id}/presupuesto` | Presupuesto con partidas |
| GET | `/lugares` | Buscar lugares |
| POST | `/eventos/{id}/lugar` | Asignar lugar |
| POST | `/eventos/{id}/pedidos` | Generar pedido a proveedor |
| PUT | `/pedidos/{id}/confirmar` | Confirmar pedido + coste definitivo |
| GET | `/ponentes/{id}` | Ficha de ponente |
| POST | `/borradores` | La IA propone una comunicación |
| PUT | `/borradores/{id}/aprobar` | Un humano aprueba y se envía |
| POST | `/bloqueos` | La IA marca un problema |
| POST | `/briefing/analizar` | Analizar un resumen y devolver campos |

La lista completa está en `app.py` (organizada por secciones) y en el documento
del contrato de API.

---

## Probar sin frontend

Puedes probar cualquier endpoint con `curl` o con la extensión Thunder Client / Postman:

```bash
# Listar eventos
curl http://localhost:5000/eventos

# Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.eus","password":"1234"}'

# Crear un evento
curl -X POST http://localhost:5000/eventos \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Mi evento","cliente":"Cliente X"}'
```

---

## Notas para el equipo

- Los datos están en memoria: **si reinicias la API, se pierden los cambios** y vuelve a los datos de prueba iniciales. Es lo esperado hasta tener PostgreSQL.
- Ya está activado **CORS**, así que el frontend puede llamar a la API desde el navegador sin el error clásico.
- La autenticación es sencilla (suficiente para la demo): tokens en memoria, sin cifrado. **No usar tal cual en producción.**
- El endpoint `/briefing/analizar` devuelve datos de ejemplo: el equipo de data science sustituye su interior por la llamada real al agente.
- Todo responde en JSON con UTF-8 (acentos y euskera correctos).
