9 Tablas (usuarios, clientes, eventos, presupuestos, salas, espacios, ponencias, ponentes, estados)

usuarios:
- id                    uuid
- nombre_usuario        text
- rol                   text

clientes:
- id                    uuid
- cliente               text
- email                 text
- telefono              text
- empresa               text
- sector                text
- ciudad                text

eventos:
- id                    uuid
- nombre_evento         text
- ciudad                text
- lugar_confirmado      text
- fecha_inicio          timestamptz
- fecha_fin             timestamptz
- numero_personas       integer
- tipo_evento           text
- nota                  text
- id_presupuesto        uuid
- id_cliente            uuid
- id_estado             uuid
- id_sala               uuid
- id_ponencia           uuid

presupuestos:
- id                    uuid
- estado_presupuesto    boolean
- total                 double precision
- fecha                 timestamptz
- nota_ubicacion        text
- precio_ubicacion      double precision
- catering              boolean
- nota_catering         text
- precio_catering       double precision
- audiovisuales         boolean
- nota_audiovisuales    text
- precio_audiovisuales  double precision
- otros                 boolean
- nota_otros            text
- precio_otros          double precision

salas:
- id                    uuid
- nombre_sala           text
- tipo_sala             text
- capacidad_max_sala    integer
- nota_sala             text
- id_espacio            uuid

espacios:
- id                    uuid
- nombre_espacio        text
- ciudad                text
- direccion             text
- aforo                 integer
- nota                  text
- telefono_contacto     text
- nombre_contacto       text
- email_contacto        text

ponencias:
- id                            uuid
- nombre_hotel                  text
- nota_transporte               text
- horario_ida_transporte        timestamptz
- horario_vuelta_transporte     timestamptz
- localizacion_hotel            text
- horario_ponencia              timestamptz
- checkin_horario               timestamptz
- ponente_estado                text
- presentacion_link             text
- billete_ida_link              text
- billete_vuelta_link           text
- tipo_ponencia                 text
- id_ponente                    uuid

ponentes:
- id                    uuid
- nombre_ponente        text
- docu_identificacion   text
- email                 text
- sector                text
- telefono              text
- foto_link             text
- cv_link               text
- empresa               text
- cargo                 text

estados:
- id                    uuid
- descripcion           text

**Propuestas:**


