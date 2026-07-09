# Tarea de análisis

Analiza el mensaje del ponente y clasifícalo.

Debes devolver exclusivamente un JSON válido.

Reglas de salida obligatorias:

- No uses Markdown.
- No uses bloques ```json.
- No añadas explicaciones fuera del JSON.
- No añadas texto antes ni después.
- La respuesta completa debe poder parsearse con json.loads() en Python.

Estructura exacta de salida:

{
  "intencion": "consulta_alojamiento | consulta_viaje | consulta_taxi | consulta_horario | consulta_lugar | consulta_documentacion | contactar_mitumi | incidencia | saludo | otro",
  "urgencia": "baja | normal | alta",
  "respuesta_ponente": "texto breve para Telegram, solo si puedes responder con datos confirmados",
  "requiere_escalado": false,
  "motivo_escalado": null,
  "confianza": 0.85
}

Criterios:

- Si el mensaje es "✈️ Vuelo" o pregunta por vuelo, avión, billete o viaje: intencion = "consulta_viaje".
- Si el mensaje es "🚕 Taxi" o pregunta cómo ir, cómo llegar, traslado, taxi o llegada al hotel: intencion = "consulta_taxi".
- Si el mensaje es "🏨 Hotel" o pregunta por hotel, habitación, dormir o alojamiento: intencion = "consulta_alojamiento".
- Si el mensaje es "🕒 Horario" o pregunta por hora, horario, inicio, charla o ponencia: intencion = "consulta_horario".
- Si el mensaje es "📍 Lugar" o pregunta dónde es, ubicación, dirección, sala o lugar del evento: intencion = "consulta_lugar".
- Si el mensaje es "📄 Documentación" o pregunta por CV, foto, presentación, PPT o documentación: intencion = "consulta_documentacion".
- Si el mensaje es "📞 Contactar MITUMI": intencion = "contactar_mitumi", requiere_escalado = true.
- Si el mensaje es "🚨 Urgencia", o dice que está perdido, no encuentra billete, tiene una urgencia, cancelación o problema inmediato: intencion = "incidencia", urgencia = "alta", requiere_escalado = true.
- Si es un saludo: intencion = "saludo".
- Si no sabes clasificarlo: intencion = "otro", requiere_escalado = true.
- No inventes datos. El agente Python construirá la respuesta final usando datos confirmados.
