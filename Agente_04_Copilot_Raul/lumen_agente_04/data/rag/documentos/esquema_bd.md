# Esquema de base de datos — Ágora (plataforma Mitumi)

Documento de referencia (grounding) para Lumen. Es la **única fuente de verdad sobre nombres de tablas y campos**. Lumen debe citar siempre tabla y campo cuando responde con un dato concreto, y nunca debe inventar un campo o tabla que no esté aquí.

Si una consulta requiere un dato que no aparece en este esquema, Lumen debe declararlo como `bloqueo_detectado`, no inferirlo ni aproximarlo.

## Tablas dentro del alcance de consulta de Lumen

### `clientes`
`id_cliente`, `cliente`, `email`, `telefono`, `empresa`

### `eventos`
`id_evento`, `nombre_evento`, `ciudad`, `fecha_inicio`, `fecha_fin`, `numero_personas`, `servicio_requerido`, `presupuesto_maximo`, `tipo_evento`, `nota`, `id_estado` (FK → `estados`), `id_cliente` (FK → `clientes`), `id_sala` (FK → `salas`), `id_presupuesto` (FK → `presupuestos`)

### `presupuestos`
`id_presupuesto`, `estado_presupuesto`, `total`, `fecha`, `ubicacion`, `catering`, `audiovisuales`, `otros`, `Observaciones`, `id_evento` (FK → `eventos`)

### `ponentes`
`id_ponente`, `nombre_ponente`, `docu_identificacion`, `email`, `sector`, `telefono`, `foto_link`

### `evento_ponente`
`id_evento_ponente`, `horario_ida_transporte`, `horario_vuelta_transporte`, `localizacion_hotel`, `horario_ponencia`, `checkin_horario`, `ponente_estado`, `presentacion_link`, `billete_ida_link`, `billete_vuelta_link`, `id_ponente` (FK → `ponentes`), `id_evento` (FK → `eventos`)

### `estados`
`id_estado`, `descripcion`

### `salas`
`id_sala`, `nombre_sala`, `tipo`, `capacidad_max_sala`, `id_espacio` (FK → `espacios`)

### `espacios`
`id_espacio`, `nombre_espacio`, `ciudad`, `direccion`, `capacidad_total`, `aforo`, `nota`, `telefono_contacto`, `nombre_contacto`, `email_contacto`

## Relaciones principales

```text
clientes 1──N eventos
eventos  N──1 estados
eventos  1──1 presupuestos   (eventos.id_presupuesto ↔ presupuestos.id_evento)
eventos  N──1 salas
salas    N──1 espacios
ponentes 1──N evento_ponente N──1 eventos
```

## Tabla FUERA de alcance — exclusión obligatoria

### `usuarios`
`id_usuario`, `nombre_usuario`, `contrasenia`, `rol (admin)`

Esta tabla **no forma parte del dominio de negocio del evento** (espacios, presupuesto, ponentes, clientes) — es la tabla de autenticación de la plataforma y contiene credenciales (`contrasenia`).

Regla dura, no negociable:

```text
Lumen NUNCA consulta la tabla `usuarios`.
Lumen NUNCA expone, menciona o infiere el contenido del campo `contrasenia` bajo ninguna circunstancia.
Si el usuario pregunta por credenciales, contraseñas, roles de acceso o datos de la tabla `usuarios`,
Lumen responde que está fuera de su alcance y lo marca como `bloqueo_detectado` con nivel_riesgo "alto".
```

Esta regla está implementada en dos capas: `prompts/prompt_sistema.md` (nivel LLM) y
`src/consultas.py` + `src/validaciones.py` (nivel código, defensa en profundidad).

## Datos personales — manejo sensible

`ponentes.docu_identificacion`, `ponentes.email`, `ponentes.telefono`, `clientes.email`, `clientes.telefono` son datos personales. Lumen puede consultarlos dentro de la plataforma para el equipo de Mitumi (uso interno legítimo), pero:

- no debe generar listados masivos exportables de estos campos salvo que el usuario lo pida explícitamente y de forma acotada;
- si la petición implica reenviar estos datos fuera de la plataforma (email externo, exportar a un tercero), debe marcarse `requiere_validacion_humana: true` y `nivel_riesgo: "medio"` como mínimo.
