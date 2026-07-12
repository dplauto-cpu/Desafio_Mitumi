# Documentación del Agente: agente_gestor_correos

## Resumen

Agente encargado de leer, clasificar y organizar automáticamente los
correos electrónicos de MITUMI.

### Capacidades

-   Lee la bandeja de entrada.
-   Clasifica correos (clientes, ponentes, proveedores y otros).
-   Extrae información relevante y adjuntos.
-   Relaciona la información con el evento correspondiente.
-   Genera acciones propuestas para revisión humana.

### Limitaciones

-   No responde automáticamente.
-   No modifica la base de datos.
-   No elimina correos.

## Flujo

1.  Leer correo.
2.  Extraer texto y adjuntos.
3.  Clasificar con IA.
4.  Identificar evento.
5.  Detectar documentación.
6.  Proponer acciones.

## Herramientas

-   IMAP
-   OpenAI GPT
-   Base de datos MITUMI
-   Gestor documental

## Caso de uso
Un ponente envía el siguiente email, y lo claisifica en ponente:
Hola, finalmente llegaré una hora más tarde al evento. ¿Podéis modificar mi recogida del aeropuerto?
Gracias.