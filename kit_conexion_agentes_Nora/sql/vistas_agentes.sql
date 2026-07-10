-- vistas_agentes.sql — Contrato de lectura estable para los agentes de data.
--
-- QUÉ ES: vistas de solo lectura con nombres de columna FIJOS. Los agentes leen las
-- vistas; si backend renombra columnas o reorganiza tablas en una migración de Prisma,
-- solo hay que arreglar la vista y ningún agente se rompe.
--
-- QUIÉN LO EJECUTA: el equipo de BBDD (Leire/Eduardo), con la cuenta owner, cuando lo
-- decida. NO lo ejecuta ningún agente. Es idempotente (CREATE OR REPLACE).
--
-- CÓMO:  psql "$OWNER_DATABASE_URL" -c "SET default_transaction_read_only = off" -f vistas_agentes.sql
--        (la base tiene read-only por defecto; el SET solo afecta a esa sesión)
--
-- Nota Prisma: las vistas no las gestiona Prisma — sobreviven a `migrate deploy`, pero si
-- una migración cambia columnas que la vista usa, la migración fallará hasta actualizar la
-- vista. Eso es deliberado: el error salta en la migración (donde se ve) y no en los agentes.

SET default_transaction_read_only = off;

-- ── Eventos con su estado y cliente resueltos a texto ────────────────────────────────
CREATE OR REPLACE VIEW vista_agente_eventos AS
SELECT
  e.id,
  e.nombre_evento,
  e.ciudad,
  e.lugar_confirmado,
  e.fecha_inicio,
  e.fecha_fin,
  e.numero_personas,
  e.tipo_evento,
  e.nota,
  es.descripcion      AS estado,
  c.cliente           AS cliente_nombre,
  c.empresa           AS cliente_empresa,
  e.id_cliente,
  e.id_estado,
  e.id_presupuesto,
  e.id_sala,
  e.id_ponencia
FROM eventos e
LEFT JOIN estados  es ON es.id = e.id_estado
LEFT JOIN clientes c  ON c.id  = e.id_cliente;

-- ── Ponencias con su ponente y su evento (la logística que usan los agentes de ponentes) ──
CREATE OR REPLACE VIEW vista_agente_ponencias AS
SELECT
  po.id,
  e.id                AS id_evento,
  e.nombre_evento,
  p.id                AS id_ponente,
  p.nombre_ponente,
  p.email             AS email_ponente,
  p.telefono          AS telefono_ponente,
  p.empresa           AS empresa_ponente,
  po.nombre_hotel,
  po.localizacion_hotel,
  po.nota_transporte,
  po.horario_ida_transporte,
  po.horario_vuelta_transporte,
  po.horario_ponencia,
  po.checkin_horario,
  po.ponente_estado,
  po.presentacion_link,
  po.billete_ida_link,
  po.billete_vuelta_link,
  po.tipo_ponencia
FROM ponencias po
LEFT JOIN ponentes p ON p.id = po.id_ponente
LEFT JOIN eventos  e ON e.id_ponencia = po.id;   -- ⚠ relación actual (1 ponente/evento);
                                                 -- si backend corrige el muchos-a-muchos,
                                                 -- SOLO cambia este JOIN, no los agentes.

-- ── Salas con su espacio ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vista_agente_salas AS
SELECT
  s.id,
  s.nombre_sala,
  s.tipo_sala,
  s.capacidad_max_sala,
  s.nota_sala,
  esp.id              AS id_espacio,
  esp.nombre_espacio,
  esp.ciudad          AS ciudad_espacio,
  esp.direccion,
  esp.aforo           AS aforo_espacio
FROM salas s
LEFT JOIN espacios esp ON esp.id = s.id_espacio;

-- ── Presupuestos con su evento ───────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vista_agente_presupuestos AS
SELECT
  pr.id,
  e.id                AS id_evento,
  e.nombre_evento,
  pr.estado_presupuesto,
  pr.total,
  pr.fecha,
  pr.precio_ubicacion,  pr.nota_ubicacion,
  pr.precio_catering,   pr.nota_catering,
  pr.precio_audiovisuales, pr.nota_audiovisuales,
  pr.precio_otros,      pr.nota_otros,
  pr.observaciones
FROM presupuestos pr
LEFT JOIN eventos e ON e.id_presupuesto = pr.id;

-- ── Permisos: los agentes leen las vistas con su rol de solo lectura ─────────────────
GRANT SELECT ON vista_agente_eventos,
                vista_agente_ponencias,
                vista_agente_salas,
                vista_agente_presupuestos
TO agente_readonly;
