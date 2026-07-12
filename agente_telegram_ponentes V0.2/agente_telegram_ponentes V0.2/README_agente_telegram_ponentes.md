# Documentación del Agente: agente_telegram_ponentes

> **Versión:** 0.2 MVP\
> **Última actualización:** 10/07/2026\
> **Autor:** Alejandro -- Proyecto MITUMI\
> **Estado:** 🟡 Beta

## 1. Resumen ejecutivo

  -----------------------------------------------------------------------
  Campo                               Valor
  ----------------------------------- -----------------------------------
  Nombre                              agente_telegram_ponentes

  Propósito                           Gestionar la comunicación entre los
                                      ponentes y la organización mediante
                                      Telegram.

  Fase                                Soporte previo y durante el evento.

  Modelo                              OpenAI GPT (clasificación de
                                      intención y generación de
                                      respuestas).

  Tipo                                Conversacional especializado

  Entorno                             Python

  Nivel de criticidad                 Alto
  -----------------------------------------------------------------------

## 2. Propósito

### Capacidades

-   Atiende consultas de los ponentes mediante Telegram.
-   Clasifica automáticamente la intención (hotel, transporte, agenda,
    documentación, ponencia, urgencia u otros).
-   Recupera información del evento y genera una respuesta adecuada.
-   Detecta incidencias urgentes y propone su escalado.
-   Mantiene el contexto conversacional del ponente.

### Limitaciones

-   No modifica la base de datos.
-   No realiza reservas.
-   No envía comunicaciones externas salvo las permitidas por el
    orquestador.
-   No toma decisiones organizativas.

## 3. Inicio rápido

### Requisitos

-   Python 3.11+
-   Token de Telegram
-   Variables de entorno configuradas
-   Acceso a la API/servicios de MITUMI

### Ejecución

``` bash
python main.py
```

## 4. Lógica

1.  Recibe el mensaje del ponente.
2.  Obtiene el contexto del usuario.
3.  Envía el contexto al LLM.
4.  Clasifica la intención.
5.  Recupera la información necesaria.
6.  Devuelve la respuesta.
7.  Si detecta una urgencia genera una acción de escalado (en el MVP
    puede enviar un correo electrónico).

## 5. Modos de fallo

  -----------------------------------------------------------------------
  Patrón                              Recuperación
  ----------------------------------- -----------------------------------
  Token inválido                      Registrar error y reintentar cuando
                                      se corrija la configuración.

  API no disponible                   Informar al usuario y registrar
                                      incidencia.

  Información insuficiente            Solicitar datos adicionales al
                                      ponente.

  Clasificación ambigua               Pedir aclaración antes de
                                      responder.
  -----------------------------------------------------------------------

## 6. Observabilidad

-   Logs INFO y DEBUG.
-   Registro de mensajes recibidos.
-   Registro de decisiones del agente.
-   Registro de errores de herramientas.

## 7. Comportamiento

Determinista: - Validaciones. - Acceso a configuración. - Recuperación
de datos.

No determinista: - Interpretación del lenguaje natural. - Redacción de
respuestas.

## 8. Contrato

Entrada: - Mensaje del usuario. - Identificador del ponente. - Contexto
del evento.

Salida:

``` json
{
  "respuesta":"...",
  "intencion":"...",
  "urgencia":"baja|media|alta",
  "requiere_escalado":false,
  "acciones":[]
}
```

## 9. Herramientas

  Herramienta            Uso
  ---------------------- ----------------------------------
  Telegram Bot API       Comunicación con el ponente
  LLM                    Comprensión del lenguaje natural
  Base de datos MITUMI   Consulta de información
  Servicio Email (MVP)   Envío de incidencias urgentes

## 10. Seguridad

-   Tokens mediante `.env`.
-   Sin credenciales hardcodeadas.
-   No almacena información sensible fuera de la plataforma.

## 11. Métricas

-   Tiempo medio de respuesta.
-   Consultas resueltas.
-   Incidencias urgentes detectadas.
-   Escalados realizados.

## 12. Casos de prueba

Caso 1: - Entrada: "¿A qué hora empieza mi ponencia?" - Resultado
esperado: devuelve la hora correcta.

Caso 2: - Entrada: "He perdido el vuelo." - Resultado esperado:
clasifica como urgencia, genera escalado y en el MVP envía un correo a
la organización.

## 13. Historial

  -----------------------------------------------------------------------
  Versión                 Fecha                   Cambios
  ----------------------- ----------------------- -----------------------
  0.2                     10/07/2026              Primera versión
                                                  funcional del agente
                                                  Telegram para MITUMI.

  -----------------------------------------------------------------------
