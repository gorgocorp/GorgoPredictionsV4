---
title: "Guía maestra de UI/UX para Codex"
version: "1.0"
updated: "2026-07-22"
language: "es-MX"
scope:
  - "Aplicaciones web, móviles y SaaS"
  - "CRM, inbox, dashboards y herramientas administrativas"
  - "Productos conversacionales, automatizaciones e inteligencia artificial"
---

# Guía maestra de UI/UX para Codex

## Propósito

Referencia unificada para analizar, diseñar, implementar y validar interfaces digitales.

No existe una lista universal y cerrada de términos UI/UX. Los nombres cambian entre plataformas, librerías, escuelas de diseño y contextos de uso. Este documento reúne una taxonomía práctica y amplia, con definiciones breves, usos recomendados, patrones, técnicas, criterios de calidad y reglas de implementación.

## Cómo debe usarlo Codex

No debe agregar todos los patrones por defecto. Antes de modificar una interfaz:

1. Identificar la tarea y el problema real del usuario.
2. Clasificarlo como visual, estructural, conductual, de estado, contenido, accesibilidad, rendimiento, confianza o datos.
3. Revisar componentes, stores, rutas y patrones existentes.
4. Elegir la solución mínima que resuelva el problema.
5. Definir estados normales, vacíos, de carga, error, permisos, offline y recuperación.
6. Mantener consistencia con el design system.
7. Añadir criterios de aceptación y pruebas reproducibles.
8. No declarar una mejora implementada sin evidencia.

## Modelo general

### UI

Se enfoca principalmente en:

- Componentes.
- Apariencia.
- Estados visuales.
- Layout.
- Tipografía.
- Color.
- Interacción directa.

### UX

Se enfoca principalmente en:

- Comprensión.
- Flujo.
- Eficiencia.
- Continuidad.
- Contexto.
- Errores.
- Confianza.
- Accesibilidad.
- Rendimiento percibido.
- Resultado final de la tarea.

### Producto completo

```text
Apariencia
+ estructura
+ comportamiento
+ estado
+ contenido
+ accesibilidad
+ rendimiento
+ confianza
+ resiliencia
+ validación
= experiencia de usuario completa
```

## Dimensiones que deben revisarse

1. Objetivo y tarea.
2. Diseño visual.
3. Arquitectura de información.
4. Navegación y orientación.
5. Componentes.
6. Comportamiento e interacción.
7. Estado, persistencia y continuidad.
8. Retroalimentación y tiempos de espera.
9. Contenido y lenguaje.
10. Formularios y entrada de datos.
11. Accesibilidad e inclusión.
12. Responsive y adaptación.
13. Rendimiento técnico y percibido.
14. Movimiento y animación.
15. Personalización.
16. Prevención y recuperación de errores.
17. Confianza, privacidad y seguridad.
18. Inteligencia artificial y automatización.
19. Colaboración y handoffs.
20. Investigación, medición y validación.

# Parte I. Taxonomía de UI/UX, producto y experiencia

## Objetivo

Este documento organiza los principales términos de UI/UX por áreas.

Una interfaz no se compone únicamente de:

- Diseño visual.
- Comportamiento e interacción.

También incluye estructura, contenido, navegación, accesibilidad, estados, rendimiento, continuidad, confianza, adaptación y validación con usuarios.

---

# 1. Diseño visual

Define cómo se ve la interfaz y cómo se establece la jerarquía visual.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Visual design | Apariencia general de la interfaz. | Crear claridad, coherencia y una identidad reconocible. |
| Visual hierarchy | Orden visual de importancia entre elementos. | Guiar la atención hacia lo más relevante. |
| Typography | Uso de fuentes, tamaños, pesos y alturas de línea. | Mejorar legibilidad y jerarquía. |
| Color system | Conjunto definido de colores funcionales y de marca. | Mantener consistencia y significado semántico. |
| Spacing system | Escala coherente de márgenes y espacios. | Evitar interfaces desordenadas. |
| Layout | Distribución de elementos dentro de la pantalla. | Organizar contenido y acciones. |
| Grid system | Estructura de columnas y alineaciones. | Mantener orden entre pantallas. |
| Alignment | Relación visual entre elementos. | Facilitar lectura y escaneo. |
| Contrast | Diferencia visual entre elementos. | Mejorar legibilidad, jerarquía y accesibilidad. |
| Visual density | Cantidad de información visible por área. | Adaptar la interfaz a usuarios casuales o avanzados. |
| Elevation | Uso de sombras y profundidad. | Comunicar capas, prioridad y superposición. |
| Shape language | Uso consistente de bordes, radios y formas. | Crear identidad y coherencia. |
| Iconography | Sistema de iconos de la aplicación. | Comunicar acciones y estados de forma compacta. |
| Illustration | Recursos gráficos explicativos o decorativos. | Mejorar onboarding, estados vacíos y comunicación. |
| Branding | Aplicación visual de la identidad del producto. | Diferenciar la aplicación y reforzar confianza. |
| Theming | Variantes visuales como light, dark o alto contraste. | Adaptar la apariencia a preferencias y contexto. |

---

# 2. Comportamiento e interacción

Define cómo responde la interfaz a las acciones del usuario.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Interaction design | Diseño de la relación entre usuario y sistema. | Hacer las acciones entendibles y predecibles. |
| Interaction pattern | Solución recurrente para una acción conocida. | Evitar inventar comportamientos innecesarios. |
| Affordance | Característica que sugiere cómo usar un elemento. | Hacer evidente que algo se puede pulsar, mover o editar. |
| Signifier | Señal visual que indica una posible interacción. | Comunicar clic, arrastre, expansión o selección. |
| Direct manipulation | Manipulación directa de elementos visuales. | Permitir arrastrar, redimensionar o editar sin pasos intermedios. |
| Hover state | Estado visual al pasar el cursor. | Indicar interactividad en escritorio. |
| Focus state | Estado visual del elemento activo mediante teclado. | Mejorar accesibilidad y navegación. |
| Pressed state | Estado mientras se mantiene presionado un control. | Confirmar que la acción fue detectada. |
| Disabled state | Estado no disponible de una acción. | Prevenir operaciones inválidas. |
| Drag-and-drop | Movimiento de elementos mediante arrastre. | Reordenar, transferir o asignar elementos. |
| Inline editing | Edición directa dentro de la vista actual. | Reducir pasos para cambios simples. |
| Keyboard shortcuts | Acciones ejecutadas mediante teclas. | Acelerar flujos frecuentes. |
| Contextual actions | Acciones mostradas según el elemento o contexto. | Reducir ruido visual. |
| Bulk actions | Acciones sobre múltiples elementos seleccionados. | Acelerar administración masiva. |
| Gesture interaction | Acciones mediante gestos táctiles. | Mejorar experiencias móviles. |
| Interaction continuity | Comportamientos consistentes entre pantallas. | Evitar reaprendizaje. |
| Predictability | Resultado esperado después de una acción. | Generar confianza y reducir errores. |

---

# 3. Arquitectura de información

Define cómo se organiza, agrupa y relaciona la información.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Information architecture | Organización general del contenido y las funciones. | Facilitar encontrar y comprender información. |
| Content hierarchy | Orden de importancia del contenido. | Mostrar primero lo esencial. |
| Taxonomy | Sistema de categorías y clasificaciones. | Organizar productos, archivos, clientes o estados. |
| Labeling system | Convenciones para nombres de secciones y acciones. | Evitar términos ambiguos. |
| Grouping | Agrupación de elementos relacionados. | Facilitar escaneo y comprensión. |
| Chunking | División de información en bloques manejables. | Reducir carga cognitiva. |
| Metadata | Datos que describen otros datos. | Facilitar búsqueda, filtros y clasificación. |
| Content model | Definición estructural de entidades y sus relaciones. | Mantener consistencia entre frontend y backend. |
| Sitemap | Mapa de páginas y relaciones de navegación. | Planear la estructura del producto. |
| Hierarchical navigation | Navegación basada en niveles. | Organizar sistemas complejos. |
| Flat navigation | Navegación con pocos niveles. | Reducir profundidad en productos simples. |
| Findability | Facilidad para encontrar contenido o funciones. | Disminuir tiempo de búsqueda. |
| Discoverability | Facilidad para descubrir funciones disponibles. | Evitar acciones ocultas. |
| Information scent | Pistas que indican dónde se encontrará algo. | Mejorar decisiones de navegación. |

---

# 4. Navegación

Define cómo se mueve el usuario dentro del producto.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Navigation model | Estructura general de desplazamiento entre vistas. | Mantener navegación predecible. |
| Global navigation | Navegación disponible en toda la aplicación. | Acceder a módulos principales. |
| Local navigation | Navegación dentro de una sección. | Cambiar entre subsecciones relacionadas. |
| Contextual navigation | Enlaces relacionados con el contenido actual. | Facilitar acciones y rutas relevantes. |
| Breadcrumbs | Ruta jerárquica de la ubicación actual. | Ayudar en estructuras profundas. |
| Deep linking | Acceso directo a una vista o entidad específica. | Compartir y restaurar ubicaciones. |
| Route state | Estado asociado a una ruta. | Mantener tabs, filtros o selección al recargar. |
| Back-navigation preservation | Conservación del contexto al regresar. | Evitar perder scroll, filtros o posición. |
| Navigation memory | Recuerdo de la última ubicación del usuario. | Retomar la actividad anterior. |
| Wayfinding | Señales que ayudan a entender dónde se está. | Reducir desorientación. |
| Progressive navigation | Mostrar rutas adicionales conforme se necesitan. | Evitar menús saturados. |
| Navigation consistency | Misma lógica de navegación en todo el producto. | Reducir aprendizaje. |

---

# 5. Estado, persistencia y continuidad

Define qué información de la interfaz se conserva y cómo se restaura.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| State persistence | Guarda el estado para recuperarlo después. | Conservar tema, filtros, paneles o selección. |
| UI state persistence | Persistencia específica de estados visuales. | Recordar tabs, secciones colapsadas o tamaño de paneles. |
| Preference persistence | Guarda preferencias personales. | Conservar tema, idioma, densidad o layout. |
| Context preservation | Mantiene el punto exacto donde estaba el usuario. | Evitar pérdida de scroll, búsqueda o selección. |
| State restoration | Restaura un estado guardado previamente. | Volver a mostrar la interfaz como estaba. |
| Session persistence | Conserva datos durante una sesión. | Mantener procesos al navegar entre pantallas. |
| Cross-session persistence | Conserva preferencias entre cierres y reaperturas. | Mantener configuración otro día. |
| Cross-device persistence | Sincroniza preferencias entre dispositivos. | Mantener experiencia consistente. |
| State hydration | Carga el estado persistido al iniciar. | Restaurar preferencias antes del render final. |
| State synchronization | Mantiene el mismo estado entre cliente y servidor. | Evitar inconsistencias. |
| Per-entity state | Estado distinto por cada entidad. | Conservar configuración independiente por chat o cliente. |
| Global state | Estado compartido por toda la aplicación. | Tema, sesión, permisos o usuario activo. |
| Local state | Estado limitado a un componente. | Controlar modal, menú o sección. |
| Durable state | Estado que sobrevive reinicios y fallos. | Proteger borradores y operaciones importantes. |
| Scroll restoration | Recupera la posición anterior del scroll. | Volver a listas sin empezar arriba. |
| Filter persistence | Conserva filtros aplicados. | Evitar repetir configuraciones. |
| Selection persistence | Conserva elementos seleccionados. | Mantener operaciones masivas. |
| Expanded-state persistence | Conserva secciones abiertas o cerradas. | Mantener accordions, árboles o paneles. |
| Workspace restoration | Recupera un espacio de trabajo completo. | Restaurar paneles, pestañas y documentos abiertos. |

---

# 6. Retroalimentación y estados del sistema

Define cómo comunica la interfaz lo que está ocurriendo.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Visibility of system status | Comunica el estado actual del sistema. | Mostrar carga, guardado, sincronización o error. |
| Immediate feedback | Respuesta instantánea a una acción. | Confirmar que el sistema detectó el cambio. |
| Inline feedback | Retroalimentación junto al elemento afectado. | Facilitar correcciones. |
| Loading state | Estado mientras se cargan datos. | Evitar pantallas aparentemente congeladas. |
| Success state | Confirmación de una operación correcta. | Cerrar el ciclo de interacción. |
| Error state | Comunicación clara de un fallo. | Explicar qué ocurrió y cómo recuperarse. |
| Empty state | Estado sin contenido disponible. | Explicar el motivo y el siguiente paso. |
| No-results state | Estado de una búsqueda sin coincidencias. | Diferenciar filtros sin resultados de datos inexistentes. |
| Offline state | Estado sin conectividad. | Explicar limitaciones y trabajo pendiente. |
| Progress indication | Representación del avance de una tarea. | Reducir incertidumbre. |
| Status badge | Indicador compacto de estado. | Mostrar activo, pendiente, completado o error. |
| Autosave feedback | Indica guardando, guardado o error. | Generar confianza en edición automática. |
| Sync status | Estado de sincronización entre sistemas. | Detectar datos pendientes o fallidos. |
| Toast | Mensaje temporal no bloqueante. | Confirmaciones breves. |
| Snackbar | Mensaje temporal con una acción. | Ofrecer deshacer o reintentar. |
| Banner | Mensaje persistente de contexto. | Mostrar problemas relevantes de una sección. |

---

# 7. Contenido y lenguaje

Define qué dice la interfaz y cómo lo comunica.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Content design | Diseño estratégico del contenido de interfaz. | Hacer que cada texto ayude a completar una tarea. |
| UX writing | Redacción de botones, mensajes y flujos. | Evitar ambigüedad y reducir errores. |
| Microcopy | Textos pequeños de apoyo. | Explicar campos, estados y acciones. |
| Voice and tone | Personalidad y tono de los textos. | Mantener una comunicación coherente. |
| Label clarity | Claridad de títulos, botones y categorías. | Evitar interpretación incorrecta. |
| Error copy | Texto específico para errores. | Explicar causa y recuperación. |
| Empty-state copy | Texto de pantallas vacías. | Guiar al siguiente paso. |
| Confirmation copy | Texto que confirma una acción. | Reducir incertidumbre. |
| Instructional copy | Texto que explica cómo completar una tarea. | Mejorar onboarding y formularios. |
| Plain language | Lenguaje directo y fácil de entender. | Reducir carga cognitiva. |
| Content consistency | Uso consistente de términos. | Evitar nombres diferentes para la misma acción. |
| CTA clarity | Claridad de las llamadas a la acción. | Indicar exactamente qué ocurrirá. |
| Content hierarchy | Prioridad de títulos, descripciones y ayuda. | Facilitar lectura rápida. |

---

# 8. Formularios y entrada de datos

Define cómo se captura, valida y corrige información.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Form design | Diseño de formularios y secuencia de campos. | Reducir errores y abandono. |
| Input affordance | Señales que indican cómo completar un campo. | Hacer evidente el formato esperado. |
| Inline validation | Validación junto al campo. | Corregir errores sin esperar al envío. |
| Progressive validation | Validación en el momento adecuado. | Evitar interrupciones prematuras. |
| Input masking | Formato automático mientras se escribe. | Facilitar teléfonos, fechas o tarjetas. |
| Smart defaults | Valores iniciales basados en contexto. | Reducir trabajo repetitivo. |
| Autofill | Rellenado automático de datos conocidos. | Acelerar formularios. |
| Dependent fields | Campos que cambian según respuestas previas. | Mostrar únicamente opciones relevantes. |
| Conditional logic | Reglas que muestran u ocultan campos. | Simplificar flujos complejos. |
| Form persistence | Conservación de datos no enviados. | Evitar pérdida de progreso. |
| Draft persistence | Guardado de contenido incompleto. | Continuar después. |
| Autosave | Guardado automático durante la edición. | Reducir pérdida de información. |
| Save and resume | Continuación posterior de un flujo. | Formularios largos. |
| Error prevention | Prevención de datos inválidos. | Reducir fallos antes de enviar. |
| Error recovery | Herramientas para corregir errores. | Evitar reiniciar el formulario. |

---

# 9. Accesibilidad

Define si la interfaz puede ser utilizada por personas con diferentes capacidades y tecnologías.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Accessibility | Diseño utilizable por la mayor cantidad de personas. | Evitar barreras de uso. |
| Keyboard accessibility | Uso completo mediante teclado. | Soportar usuarios sin mouse. |
| Screen-reader support | Compatibilidad con lectores de pantalla. | Comunicar estructura, nombres y estados. |
| Focus management | Control lógico del foco. | Hacer modales, drawers y formularios navegables. |
| Focus restoration | Regreso del foco al origen al cerrar una capa. | Mantener continuidad con teclado. |
| Semantic HTML | Uso correcto de elementos HTML. | Mejorar accesibilidad y mantenimiento. |
| ARIA labeling | Etiquetas accesibles para controles. | Explicar botones e iconos. |
| Color contrast | Diferencia suficiente entre texto y fondo. | Mejorar legibilidad. |
| Non-color indicators | Uso de texto o iconos además del color. | Evitar depender exclusivamente del color. |
| Reduced motion | Reducción de animaciones según preferencia. | Evitar molestias o desorientación. |
| Touch target size | Tamaño mínimo de controles táctiles. | Reducir pulsaciones erróneas. |
| Accessible error handling | Errores identificables y anunciados. | Facilitar corrección. |
| WCAG compliance | Cumplimiento de pautas de accesibilidad. | Establecer criterios verificables. |
| Inclusive design | Diseño que considera diversidad de usuarios y contextos. | Crear soluciones más robustas. |

---

# 10. Responsive y adaptación

Define cómo cambia la interfaz según dispositivo, espacio y contexto.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Responsive design | Adapta el layout al tamaño de pantalla. | Funcionar en escritorio, tablet y móvil. |
| Adaptive design | Usa estructuras específicas para distintos contextos. | Optimizar experiencias por dispositivo. |
| Fluid layout | Usa dimensiones flexibles. | Aprovechar mejor el espacio disponible. |
| Breakpoint | Punto donde cambia la estructura. | Reorganizar contenido según ancho. |
| Container query | Adaptación basada en el tamaño del contenedor. | Crear componentes reutilizables. |
| Mobile-first | Diseñar primero para pantallas pequeñas. | Priorizar contenido esencial. |
| Desktop-first | Diseñar primero para escritorio. | Adecuado para herramientas densas. |
| Responsive typography | Tipografía que cambia según viewport. | Mantener legibilidad. |
| Adaptive navigation | Cambia sidebar, rail o bottom navigation según contexto. | Evitar navegación inadecuada. |
| Responsive density | Ajusta cantidad y espacio de información. | Mantener usabilidad en diferentes tamaños. |
| Orientation handling | Adaptación a vertical y horizontal. | Mejorar uso en móviles y tablets. |
| Device capability adaptation | Adaptación a capacidades del dispositivo. | Usar cámara, touch o teclado cuando estén disponibles. |

---

# 11. Rendimiento y percepción de velocidad

Define qué tan rápida se siente y funciona la interfaz.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| UX performance | Impacto del rendimiento técnico en la experiencia. | Evitar retrasos que interrumpan tareas. |
| Perceived performance | Percepción subjetiva de velocidad. | Hacer que la interfaz se sienta más rápida. |
| Lazy loading | Carga contenido cuando se necesita. | Reducir carga inicial. |
| Prefetching | Carga datos antes de que se soliciten. | Abrir vistas más rápido. |
| Incremental loading | Muestra contenido por partes. | Entregar información útil antes. |
| Skeleton loading | Muestra la estructura esperada durante la carga. | Reducir sensación de espera. |
| Optimistic UI | Actualiza antes de confirmar con el servidor. | Acelerar acciones frecuentes y reversibles. |
| Pessimistic UI | Espera confirmación antes de actualizar. | Proteger operaciones críticas. |
| Virtualization | Renderiza únicamente elementos visibles. | Mantener listas grandes fluidas. |
| Caching | Reutiliza datos cargados previamente. | Reducir peticiones repetidas. |
| Background refresh | Actualiza datos sin bloquear la pantalla. | Mantener información fresca. |
| Stale-while-revalidate | Muestra datos previos mientras actualiza. | Combinar respuesta inmediata y frescura. |
| Debouncing | Retrasa una acción hasta que termina una secuencia. | Optimizar búsquedas y filtros. |
| Throttling | Limita frecuencia de ejecución. | Optimizar scroll y resize. |
| Incremental update | Actualiza solo el elemento modificado. | Evitar recargas completas. |

---

# 12. Movimiento y animación

Define cómo se comunican cambios mediante movimiento.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Motion design | Uso funcional del movimiento. | Explicar transiciones y relaciones. |
| Microinteraction | Animación breve asociada a una acción. | Confirmar selección, guardado o cambio. |
| Transition | Cambio animado entre estados. | Mantener continuidad visual. |
| Enter animation | Animación de entrada. | Comunicar aparición de contenido. |
| Exit animation | Animación de salida. | Comunicar eliminación o cierre. |
| Shared element transition | Conserva un elemento entre vistas. | Mostrar relación entre tarjeta y detalle. |
| Spatial transition | Movimiento que representa dirección o jerarquía. | Explicar navegación. |
| Loading animation | Movimiento durante una espera. | Comunicar actividad. |
| Motion hierarchy | Diferentes intensidades según importancia. | Evitar animaciones excesivas. |
| Reduced-motion support | Alternativa con menos movimiento. | Mejorar accesibilidad. |
| Animation timing | Duración y aceleración de una animación. | Mantener naturalidad y rapidez. |
| Motion consistency | Reglas comunes de animación. | Evitar comportamientos contradictorios. |

---

# 13. Personalización y preferencias

Define cómo adapta el usuario la interfaz a sus necesidades.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Personalization | Adaptación automática según usuario o comportamiento. | Mostrar contenido relevante. |
| Customization | Configuración manual realizada por el usuario. | Elegir tema, columnas o layout. |
| User preferences | Conjunto de configuraciones personales. | Mantener una experiencia consistente. |
| Theme preference | Tema light, dark o automático. | Adaptar apariencia. |
| Density preference | Vista compacta, cómoda o amplia. | Ajustar cantidad de información. |
| Layout preference | Organización personalizada de paneles. | Adaptar espacios de trabajo. |
| Column preference | Visibilidad, orden y tamaño de columnas. | Personalizar tablas. |
| Notification preference | Configuración de alertas. | Evitar ruido innecesario. |
| Locale preference | Idioma y formatos regionales. | Mostrar fechas, moneda y números correctamente. |
| Saved views | Combinación guardada de filtros y columnas. | Repetir flujos de trabajo. |
| Role-based UI | Interfaz adaptada al rol y permisos. | Mostrar funciones relevantes. |
| Adaptive recommendations | Sugerencias basadas en contexto. | Acelerar decisiones frecuentes. |

---

# 14. Prevención, seguridad y recuperación

Define cómo se evitan errores y cómo se recupera el usuario.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Error prevention | Impide acciones o datos inválidos. | Reducir fallos antes de que ocurran. |
| Error recovery | Permite corregir un fallo. | Evitar pérdida de trabajo. |
| Undo | Revierte una acción reciente. | Evitar confirmaciones repetitivas. |
| Redo | Reaplica una acción revertida. | Mejorar control en editores. |
| Reversible action | Acción diseñada para poder deshacerse. | Aumentar velocidad y confianza. |
| Confirmation dialog | Solicita confirmación antes de una operación crítica. | Proteger acciones irreversibles. |
| Safe defaults | Valores iniciales de bajo riesgo. | Reducir errores accidentales. |
| Guardrails | Límites que previenen acciones peligrosas. | Proteger sin bloquear innecesariamente. |
| Graceful degradation | Mantiene funciones básicas ante fallos parciales. | Evitar caída total de la experiencia. |
| Fault tolerance | Continúa funcionando aunque una parte falle. | Proteger flujos importantes. |
| Retry pattern | Permite repetir una operación fallida. | Recuperar sincronizaciones o cargas. |
| Idempotency | Repetir una acción sin duplicar efectos. | Evitar publicaciones o registros duplicados. |
| Recovery state | Estado utilizado para reconstruir una operación. | Continuar procesos interrumpidos. |
| Checkpointing | Puntos guardados durante un proceso. | Recuperar flujos largos. |

---

# 15. Confianza, privacidad y transparencia

Define si el usuario entiende y confía en lo que hace el producto.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Trust design | Diseño orientado a generar confianza. | Reducir incertidumbre en acciones importantes. |
| Transparency | Explicación clara de procesos y consecuencias. | Evitar resultados inesperados. |
| Explainability | Explicación del motivo de una decisión del sistema. | Comprender automatizaciones o IA. |
| Data visibility | Claridad sobre qué datos se usan. | Mejorar control y privacidad. |
| Consent design | Solicitud clara de autorización. | Evitar consentimiento ambiguo. |
| Privacy by design | Privacidad considerada desde la arquitectura. | Proteger datos desde el inicio. |
| Permission clarity | Explicación de permisos requeridos. | Reducir rechazo y desconfianza. |
| Auditability | Registro verificable de acciones. | Investigar cambios y responsabilidades. |
| Provenance | Identificación del origen de un dato o acción. | Distinguir usuario, IA, sistema o integración. |
| Human-in-the-loop | Intervención humana en decisiones relevantes. | Controlar automatizaciones críticas. |
| Confidence indicator | Comunicación del nivel de certeza. | Evitar presentar inferencias como hechos. |
| Destructive-action clarity | Explicación del impacto de una acción. | Reducir eliminaciones accidentales. |

---

# 16. Internacionalización y localización

Define cómo se adapta la interfaz a idiomas y regiones.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Internationalization | Preparación técnica para múltiples idiomas y regiones. | Evitar rediseñar la aplicación después. |
| Localization | Adaptación de textos y formatos a una región. | Mejorar comprensión local. |
| Locale | Configuración regional del usuario. | Controlar idioma, fechas, números y moneda. |
| RTL support | Soporte para lectura de derecha a izquierda. | Adaptar la interfaz a ciertos idiomas. |
| Date localization | Formato regional de fechas. | Evitar confusiones. |
| Number localization | Formato regional de números. | Mostrar separadores correctos. |
| Currency localization | Formato y símbolo monetario regional. | Presentar precios correctamente. |
| Translation expansion | Espacio adicional para textos traducidos. | Evitar cortes de contenido. |
| Cultural adaptation | Ajuste de símbolos, ejemplos y convenciones. | Evitar interpretaciones incorrectas. |
| Time-zone handling | Manejo explícito de zonas horarias. | Mostrar eventos y registros correctamente. |

---

# 17. Diseño de sistemas y consistencia

Define las reglas reutilizables que mantienen coherencia en toda la aplicación.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Design system | Conjunto de componentes, reglas y documentación. | Mantener coherencia y acelerar desarrollo. |
| Component library | Colección reutilizable de componentes. | Evitar duplicación. |
| Design tokens | Variables de color, espacio, tipografía y movimiento. | Sincronizar diseño y código. |
| Pattern library | Catálogo de soluciones recurrentes. | Reutilizar comportamientos probados. |
| UI guidelines | Reglas de uso de componentes. | Evitar implementaciones inconsistentes. |
| Interaction guidelines | Reglas de comportamiento. | Mantener patrones predecibles. |
| Content guidelines | Reglas de redacción. | Mantener voz y terminología. |
| Accessibility guidelines | Criterios de accesibilidad. | Garantizar un estándar mínimo. |
| Component states | Estados definidos de cada componente. | Cubrir loading, disabled, error y success. |
| Variant system | Variantes controladas de un componente. | Evitar estilos arbitrarios. |
| Theming architecture | Estructura técnica para temas. | Aplicar cambios globales coherentes. |
| Governance | Proceso para mantener y evolucionar el sistema. | Evitar degradación con el tiempo. |

---

# 18. Investigación y validación UX

Define cómo se comprueba que la interfaz realmente funciona.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| UX research | Investigación sobre usuarios, tareas y contexto. | Diseñar con evidencia. |
| User interview | Entrevista directa con usuarios. | Conocer necesidades y problemas. |
| Usability testing | Observación de usuarios usando el producto. | Detectar obstáculos reales. |
| Heuristic evaluation | Auditoría basada en principios de usabilidad. | Encontrar problemas rápidamente. |
| Cognitive walkthrough | Evaluación paso a paso de una tarea. | Revisar facilidad de aprendizaje. |
| Task analysis | Descomposición de una tarea. | Simplificar flujos. |
| User journey | Recorrido completo del usuario. | Detectar fricciones entre etapas. |
| Journey mapping | Representación visual del recorrido. | Analizar puntos de dolor y oportunidades. |
| Persona | Perfil representativo de un tipo de usuario. | Mantener decisiones enfocadas. |
| Jobs to be Done | Necesidad funcional que el usuario intenta resolver. | Diseñar alrededor del resultado esperado. |
| A/B testing | Comparación de dos variantes. | Medir cuál funciona mejor. |
| Analytics | Medición del comportamiento real. | Detectar abandono, errores y uso. |
| Funnel analysis | Análisis de pasos hacia una conversión. | Encontrar puntos de abandono. |
| Session replay | Reproducción de interacciones de usuario. | Detectar problemas difíciles de reproducir. |
| Accessibility audit | Evaluación técnica de accesibilidad. | Encontrar incumplimientos. |

---

# 19. Métricas de experiencia

Define cómo se mide la calidad de uso.

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Task success rate | Porcentaje de tareas completadas correctamente. | Medir efectividad. |
| Time on task | Tiempo necesario para completar una tarea. | Medir eficiencia. |
| Error rate | Cantidad de errores por tarea. | Detectar complejidad o ambigüedad. |
| Completion rate | Porcentaje de flujos terminados. | Evaluar formularios y procesos. |
| Abandonment rate | Porcentaje de usuarios que abandonan. | Localizar fricción. |
| Learnability | Facilidad de aprendizaje inicial. | Evaluar onboarding. |
| Memorability | Facilidad de reutilización después de un tiempo. | Evaluar consistencia. |
| Satisfaction | Percepción general del usuario. | Medir calidad subjetiva. |
| SUS | Escala estandarizada de usabilidad. | Comparar percepción de facilidad. |
| NPS | Intención de recomendar el producto. | Medir lealtad general. |
| CES | Esfuerzo percibido para completar una tarea. | Detectar flujos pesados. |
| Conversion rate | Porcentaje que completa una acción objetivo. | Medir efectividad comercial. |
| Retention | Usuarios que continúan usando el producto. | Evaluar valor sostenido. |

---

# 20. Modelo práctico de categorías UI/UX

Para documentar una pantalla o solicitar una implementación a Codex, revisar estas áreas:

```text
1. Visual.
2. Estructura e información.
3. Navegación.
4. Comportamiento e interacción.
5. Estado, persistencia y continuidad.
6. Retroalimentación del sistema.
7. Contenido y lenguaje.
8. Formularios y entrada de datos.
9. Accesibilidad.
10. Responsive y adaptación.
11. Rendimiento percibido y técnico.
12. Movimiento y animación.
13. Personalización.
14. Prevención y recuperación de errores.
15. Confianza, privacidad y transparencia.
16. Internacionalización.
17. Design system y consistencia.
18. Investigación y validación.
19. Métricas de experiencia.
```

---

# 21. Plantilla para pedir una auditoría completa a Codex

```text
Audita esta pantalla desde todas las dimensiones de UI/UX, no solamente desde
el diseño visual.

Evalúa:

1. Diseño visual:
   jerarquía, tipografía, color, espaciado, densidad, alineación y contraste.

2. Arquitectura de información:
   agrupación, nomenclatura, jerarquía, categorías y facilidad para encontrar
   información.

3. Navegación:
   rutas, orientación, regreso, deep linking y preservación de contexto.

4. Comportamiento e interacción:
   estados de controles, selección, acciones masivas, teclado, drawers,
   modales, hover, focus y drag-and-drop.

5. Persistencia y continuidad:
   filtros, búsqueda, scroll, selección, tabs, secciones colapsadas, tema,
   tamaños de paneles y estado por entidad.

6. Retroalimentación:
   loading, success, error, empty, no-results, sincronización, progreso,
   autosave y recuperación.

7. Contenido:
   títulos, labels, CTA, microcopy, errores e instrucciones.

8. Formularios:
   validación, defaults, autofill, datos parciales, borradores y recuperación.

9. Accesibilidad:
   teclado, foco, semántica HTML, ARIA, contraste, lectores de pantalla y
   reducción de movimiento.

10. Responsive:
    comportamiento en escritorio, tablet y móvil.

11. Rendimiento:
    virtualización, lazy loading, caché, actualización incremental y
    rendimiento percibido.

12. Prevención y recuperación:
    undo, retry, confirmaciones, idempotencia, tolerancia a fallos y acciones
    reversibles.

13. Confianza:
    permisos, origen de acciones, IA vs. humano, transparencia, auditoría y
    consecuencias.

Entrega:

- Hallazgos comprobables.
- Severidad.
- Evidencia.
- Impacto en usuario.
- Corrección mínima recomendada.
- Criterios de aceptación.
- Pruebas reproducibles.
- Diferencia entre problemas visuales, funcionales, de comportamiento,
  accesibilidad, rendimiento y arquitectura.
```

---

# 22. Términos prioritarios para aplicaciones SaaS administrativas

Para aplicaciones como CRM, inbox, publicadores, paneles de operaciones o herramientas con IA, priorizar:

```text
Visual hierarchy
Information architecture
Interaction design
Context preservation
State persistence
Per-entity state
Scroll restoration
Filter persistence
Selection persistence
Workspace restoration
Visibility of system status
Optimistic UI
Incremental update
Autosave
Draft persistence
Undo
Retry
Idempotency
Graceful degradation
Focus management
Keyboard accessibility
Virtualization
Responsive density
Auditability
Provenance
Human-in-the-loop
Design tokens
Usability testing
Task success rate
```

---

# 23. Resumen conceptual

## UI

Se enfoca principalmente en:

- Componentes.
- Apariencia.
- Estados visuales.
- Layout.
- Tipografía.
- Color.
- Interacción directa.

## UX

Se enfoca principalmente en:

- Comprensión.
- Flujo.
- Eficiencia.
- Continuidad.
- Contexto.
- Errores.
- Confianza.
- Accesibilidad.
- Rendimiento percibido.
- Resultado final de la tarea.

## Producto completo

Una implementación madura debe considerar simultáneamente:

```text
Apariencia
+ estructura
+ comportamiento
+ estado
+ contenido
+ accesibilidad
+ rendimiento
+ confianza
+ validación
= experiencia de usuario completa
```

# Parte II. Catálogo de componentes y patrones de interfaz

## Objetivo

Este documento sirve como referencia técnica para diseñar e implementar interfaces modernas, limpias, intuitivas y consistentes.

No existe una lista cerrada de componentes UI. Los nombres pueden variar entre frameworks y librerías como:

- React
- Material UI
- Ant Design
- Radix UI
- shadcn/ui
- Fluent UI
- Chakra UI
- Mantine
- Headless UI

La implementación debe priorizar:

1. Claridad visual.
2. Jerarquía de información.
3. Accesibilidad.
4. Retroalimentación inmediata.
5. Persistencia de contexto.
6. Acciones reversibles.
7. Reducción de pasos innecesarios.
8. Diseño responsive.
9. Estados de carga, error y vacío.
10. Soporte para teclado.

---

# 1. Diferencias básicas

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Slider | Control para seleccionar un valor o rango arrastrando un indicador sobre una barra. | Volumen, precio, porcentaje, intensidad o distancia. |
| Slide | Pantalla o elemento individual dentro de una secuencia. | Presentaciones, tutoriales o carruseles. |
| Carousel | Conjunto horizontal de slides navegables. | Imágenes, productos o contenido destacado. No usar para información crítica. |
| Drawer | Panel que aparece desde un lateral sin abandonar la pantalla principal. | Detalles, edición, filtros, archivos o configuración contextual. |
| Bottom sheet | Panel que aparece desde la parte inferior. | Acciones y detalles en móvil. |
| Transfer list | Dos listas que permiten mover elementos entre disponibles y seleccionados. | Grupos destino, permisos, usuarios, categorías o asignaciones. |
| Split view | Pantalla dividida en dos o más paneles simultáneos. | Lista a la izquierda y detalle a la derecha. |
| Master-detail | Un elemento principal controla el contenido de un panel de detalle. | Correos, conversaciones, archivos o clientes. |

---

# 2. Navegación

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Navbar | Navegación principal horizontal. | Aplicaciones con pocas secciones principales. |
| Sidebar | Navegación vertical persistente. | Aplicaciones administrativas con muchos módulos. |
| Navigation rail | Sidebar compacta basada principalmente en iconos. | Interfaces donde se necesita conservar espacio horizontal. |
| Collapsible sidebar | Sidebar que puede minimizarse. | Dashboards densos. |
| Navigation drawer | Menú lateral temporal. | Móviles o pantallas pequeñas. |
| Tabs | Cambian entre vistas relacionadas dentro del mismo contexto. | General, permisos, actividad o documentos. |
| Segmented control | Selector compacto entre pocas vistas mutuamente excluyentes. | Lista/cuadrícula, mensual/anual o activo/inactivo. |
| Breadcrumbs | Muestran la ruta jerárquica actual. | Configuración profunda, carpetas o catálogos. |
| Stepper | Muestra las etapas de un proceso. | Onboarding, formularios, pagos o publicación. |
| Pagination | Divide resultados en páginas. | Tablas y búsquedas donde importa la posición. |
| Infinite scroll | Carga contenido conforme el usuario sigue desplazándose. | Feeds y exploración continua. |
| Load more | Carga bloques adicionales mediante un botón. | Alternativa controlada al scroll infinito. |
| Anchor navigation | Navega a secciones de la misma página. | Formularios o documentos largos. |
| Scrollspy | Resalta automáticamente la sección visible. | Configuración extensa y documentación. |
| Contextual back button | Regresa a la vista anterior lógica. | Detalles abiertos desde una lista. |
| Command palette | Buscador global de acciones y navegación por teclado. | Aplicaciones avanzadas con muchas funciones. |
| Recent items | Acceso rápido a elementos abiertos recientemente. | Proyectos, archivos, clientes o conversaciones. |

---

# 3. Paneles, capas y contenido contextual

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Modal | Bloquea temporalmente la interfaz hasta resolver una acción. | Confirmaciones o tareas breves que requieren atención. |
| Dialog | Ventana enfocada para comunicar o solicitar una decisión. | Eliminar, guardar, autorizar o confirmar. |
| Drawer lateral | Abre información sin perder el contexto principal. | Preview, detalles, edición o historial. |
| Popover | Panel pequeño anclado a un elemento. | Filtros, acciones o información breve. |
| Tooltip | Explicación breve al pasar el cursor o enfocar. | Iconos o controles no evidentes. |
| Context menu | Menú que aparece mediante clic derecho o acción secundaria. | Acciones sobre archivos, filas o nodos. |
| Dropdown menu | Lista desplegable de acciones o valores. | Selecciones compactas. |
| Overflow menu | Menú de acciones secundarias, normalmente representado por tres puntos. | Evitar saturar una fila o tarjeta. |
| Hover card | Preview enriquecido al mantener el cursor sobre un elemento. | Usuarios, archivos, enlaces o grupos. |
| Peek view | Vista rápida sin abrir completamente el elemento. | Imágenes, documentos o conversaciones. |
| Lightbox | Visualizador centrado para imágenes o multimedia. | Galerías y previews de alta resolución. |
| Fullscreen overlay | Capa que ocupa toda la pantalla. | Editores, galerías o flujos complejos. |
| Inspector panel | Panel con propiedades del elemento seleccionado. | Diseñadores, constructores y administradores. |
| Resizable panel | Panel cuyo ancho o alto puede modificarse. | Listas con detalles o editores técnicos. |

---

# 4. Selección, filtros y formularios

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Checkbox | Selección independiente de uno o varios elementos. | Selección múltiple y opciones booleanas. |
| Radio button | Permite elegir exactamente una opción. | Métodos, planes o tipos excluyentes. |
| Toggle switch | Activa o desactiva un estado inmediato. | Notificaciones, visibilidad o sincronización. |
| Select | Lista cerrada de opciones. | Pocas opciones conocidas. |
| Combobox | Select con búsqueda y escritura. | Catálogos extensos. |
| Autocomplete | Sugiere resultados mientras se escribe. | Usuarios, ciudades, modelos o etiquetas. |
| Multiselect | Permite elegir varios valores dentro de un solo control. | Categorías, destinatarios o permisos. |
| Chips | Representan filtros, etiquetas o selecciones compactas. | Mostrar selecciones activas. |
| Tag input | Permite introducir varias etiquetas. | Palabras clave, destinatarios o clasificación. |
| Range slider | Selecciona un mínimo y un máximo. | Precio, fecha, distancia o puntuación. |
| Numeric stepper | Aumenta o reduce una cantidad mediante botones. | Unidades, intentos, prioridad o cantidad. |
| Date picker | Selección visual de una fecha. | Programaciones, vencimientos y filtros. |
| Date range picker | Selección de fecha inicial y final. | Reportes y búsquedas temporales. |
| Time picker | Selección de hora. | Programaciones y recordatorios. |
| Color picker | Selección visual de color. | Personalización y diseño. |
| File picker | Selección de archivos del dispositivo. | Adjuntos e importaciones. |
| Dropzone | Área para arrastrar y soltar archivos. | Cargas múltiples y flujos documentales. |
| Inline editing | Edición directa sobre el contenido mostrado. | Nombres, estados o cantidades simples. |
| Form wizard | Divide un formulario largo en etapas. | Configuración inicial o procesos complejos. |
| Smart defaults | Completa valores previsibles automáticamente. | Reducir esfuerzo y errores. |
| Dependent fields | Cambia opciones según una selección previa. | Estado/municipio, plan/requisitos o categoría/subcategoría. |
| Faceted filters | Filtros combinables por categoría, estado o atributo. | Grandes catálogos y búsquedas. |
| Filter drawer | Agrupa filtros avanzados en un panel lateral. | Pantallas con poco espacio. |
| Saved filters | Guarda combinaciones frecuentes de filtros. | Operaciones repetitivas. |

---

# 5. Listas, datos y organización

| Componente | Descripción | Uso recomendado |
|---|---|---|
| List view | Presenta elementos en filas. | Conversaciones, archivos, grupos o clientes. |
| Card grid | Muestra elementos como tarjetas. | Contenido visual o con varios atributos. |
| Data table | Organiza datos en filas y columnas. | Comparación, administración y reportes. |
| Virtualized list | Renderiza solamente los elementos visibles. | Listas de cientos o miles de registros. |
| Tree view | Representa jerarquías expandibles. | Carpetas, permisos o categorías. |
| Accordion | Expande y contrae secciones verticales. | FAQ y configuración agrupada. |
| Kanban board | Organiza elementos por etapas. | Pipelines, tareas o estados. |
| Timeline | Ordena eventos cronológicamente. | Historiales, actividad y auditoría. |
| Activity feed | Lista cambios o eventos recientes. | Colaboración y seguimiento. |
| Calendar view | Distribuye eventos por fecha. | Programaciones, campañas y citas. |
| Transfer list | Mueve registros entre dos colecciones. | Grupos destino, permisos y asignaciones. |
| Dual-pane selector | Variante de transfer list con filtros, búsqueda y preview. | Selecciones masivas con contexto. |
| Grouped list | Separa elementos mediante encabezados de categoría. | Colecciones como “Mis grupos” y “Motos”. |
| Expandable row | Muestra detalles dentro de una fila. | Tablas donde no se requiere un drawer completo. |
| Sticky header | Mantiene encabezados visibles durante el scroll. | Listas y tablas extensas. |
| Sticky actions | Mantiene acciones principales siempre accesibles. | Selecciones largas y formularios. |
| Sortable list | Permite reordenar elementos. | Prioridades, playlists o pasos. |
| Drag-and-drop list | Mueve elementos mediante arrastre. | Organización visual y reasignaciones. |
| Masonry grid | Cuadrícula con tarjetas de diferentes alturas. | Galerías visuales. |
| Comparison view | Coloca elementos lado a lado. | Productos, versiones o configuraciones. |

---

# 6. Acciones y comandos

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Primary button | Ejecuta la acción principal de la vista. | Publicar, guardar, crear o enviar. |
| Secondary button | Acción alternativa de menor prioridad. | Cancelar, verificar o previsualizar. |
| Tertiary button | Acción discreta sin fondo dominante. | Acciones auxiliares. |
| Icon button | Botón representado por un icono. | Acciones conocidas y repetitivas. |
| Split button | Acción principal acompañada por un menú de variantes. | Publicar ahora, programar o guardar borrador. |
| Floating action button | Acción flotante dominante. | Crear un elemento en móvil. |
| Action toolbar | Agrupa acciones relacionadas. | Editores y administración. |
| Bulk action bar | Aparece cuando existen varios elementos seleccionados. | Eliminar, mover, etiquetar o verificar en lote. |
| Command bar | Barra de acciones globales. | Aplicaciones de productividad. |
| Keyboard shortcuts | Ejecutan acciones mediante teclas. | Usuarios frecuentes y flujos repetitivos. |
| Shortcut hints | Muestran la combinación de teclas disponible. | Mejorar descubrimiento de comandos. |
| Swipe actions | Revelan acciones al deslizar una fila. | Aplicaciones móviles. |
| Drag handle | Indica dónde sujetar para arrastrar. | Reordenamiento claro y controlado. |
| Undo action | Permite revertir una operación reciente. | Eliminar, mover, archivar o cambiar estado. |
| Optimistic action | Actualiza la interfaz antes de confirmar con el servidor. | Acciones rápidas y reversibles. |

---

# 7. Estados y retroalimentación

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Toast | Notificación temporal no bloqueante. | Guardado, copiado o actualizado. |
| Snackbar | Notificación temporal con una acción breve. | “Grupo eliminado. Deshacer”. |
| Banner | Mensaje persistente dentro de una sección. | Problemas de sincronización o avisos importantes. |
| Alert | Mensaje destacado de éxito, error o advertencia. | Estados que requieren reconocimiento. |
| Inline validation | Muestra errores junto al campo correspondiente. | Formularios. |
| Progress bar | Indica avance medible. | Subidas, importaciones o procesos largos. |
| Spinner | Indica espera breve sin porcentaje conocido. | Cargas pequeñas. |
| Skeleton | Representa la estructura mientras se carga contenido. | Listas, tarjetas y perfiles. |
| Shimmer | Animación aplicada al skeleton. | Comunicar que la carga sigue activa. |
| Empty state | Explica por qué no hay contenido y qué acción realizar. | Listas vacías o módulos sin configurar. |
| No-results state | Indica que los filtros no encontraron coincidencias. | Búsquedas y filtros. |
| Error state | Explica un fallo y ofrece recuperación. | Reintentar, reconectar o corregir. |
| Offline state | Indica pérdida de conexión. | Aplicaciones con sincronización. |
| Sync indicator | Muestra estado de sincronización. | Publicadores, editores y aplicaciones offline. |
| Status badge | Representa un estado compacto. | Activo, pendiente, error o sincronizado. |
| Counter badge | Muestra una cantidad junto a una sección. | Notificaciones, elegidos o pendientes. |
| Presence indicator | Muestra disponibilidad o actividad. | Colaboración y soporte. |
| Autosave indicator | Comunica guardado automático. | Editores y formularios extensos. |

---

# 8. Descubrimiento y ayuda

| Componente | Descripción | Uso recomendado |
|---|---|---|
| Onboarding | Introducción inicial al producto. | Primer uso. |
| Guided tour | Recorre funciones mediante pasos. | Funciones complejas o nuevas. |
| Coach mark | Señala una función concreta. | Cambios recientes en la interfaz. |
| Spotlight | Oscurece la pantalla y destaca un control. | Enseñar una acción importante. |
| Contextual help | Ayuda relacionada con la sección actual. | Configuraciones técnicas. |
| Help tooltip | Explicación breve junto a una etiqueta. | Conceptos ambiguos. |
| Inline example | Ejemplo dentro o debajo de un campo. | Formatos de teléfono, URL o reglas. |
| Preview mode | Muestra el resultado antes de aplicarlo. | Publicaciones, documentos y plantillas. |

---

# 9. Movimiento e interacción

| Patrón | Descripción | Uso recomendado |
|---|---|---|
| Microinteraction | Animación breve que confirma una acción. | Selección, guardado, expansión o cambio de estado. |
| Expand/collapse | Abre o cierra contenido progresivamente. | Detalles secundarios. |
| Slide transition | Mueve una vista lateralmente. | Flujos secuenciales o navegación móvil. |
| Fade transition | Muestra u oculta contenido suavemente. | Cambios de estado discretos. |
| Shared element transition | Conserva visualmente un elemento entre vistas. | Tarjeta que se transforma en detalle. |
| Drag preview | Muestra qué elemento se está moviendo. | Drag-and-drop. |
| Snap scrolling | Ajusta el desplazamiento a posiciones definidas. | Carruseles y paneles horizontales. |
| Pull to refresh | Actualiza al arrastrar hacia abajo. | Aplicaciones móviles. |
| Long press | Abre acciones adicionales manteniendo presionado. | Móvil, para acciones secundarias. |
| Hover state | Cambia visualmente al pasar el cursor. | Mostrar interactividad en escritorio. |
| Focus state | Resalta el elemento activo mediante teclado. | Accesibilidad obligatoria. |

---

# 10. Patrones modernos de estructura

| Patrón | Descripción |
|---|---|
| Progressive disclosure | Mostrar primero lo esencial y revelar opciones avanzadas cuando sean necesarias. |
| Contextual actions | Mostrar acciones solamente cuando aplican al elemento seleccionado. |
| Density modes | Permitir vista compacta, cómoda o amplia. |
| Responsive layout | Adaptar la estructura, no solamente los tamaños, según el espacio disponible. |
| Adaptive navigation | Convertir sidebar en drawer o barra inferior según el dispositivo. |
| Zero-state guidance | Usar estados vacíos para explicar el siguiente paso. |
| Direct manipulation | Permitir mover, editar o redimensionar objetos directamente. |
| Preview before commit | Permitir revisar el resultado antes de una operación importante. |
| Reversible actions | Favorecer “deshacer” en lugar de confirmaciones constantes. |
| Smart bulk actions | Aplicar acciones masivas sin repetir operaciones fila por fila. |
| Persistent context | Mantener filtros, scroll y selección al abrir o cerrar detalles. |
| Focus mode | Ocultar elementos secundarios durante una tarea compleja. |

---


# Parte III. Conceptos y técnicas avanzadas

## 1. Disciplinas relacionadas

| Término | Descripción breve | Para qué sirve |
|---|---|---|
| Product design | Integra necesidades de usuario, negocio y viabilidad técnica. | Diseñar una solución completa, no solo una pantalla. |
| Interaction design, IxD | Define acciones, respuestas, reglas y secuencias de interacción. | Crear comportamientos predecibles. |
| Human-computer interaction, HCI | Estudia la relación entre personas y sistemas computacionales. | Fundamentar decisiones en capacidades humanas. |
| Human factors | Analiza límites físicos, cognitivos y situacionales. | Reducir errores, carga mental y fatiga. |
| Ergonomics | Adapta sistemas y entornos a las personas. | Mejorar seguridad, comodidad y desempeño. |
| Service design | Diseña la experiencia entre canales, personas, procesos y sistemas. | Resolver problemas de extremo a extremo. |
| Customer experience, CX | Percepción total de la relación con una organización. | Coordinar producto, soporte, ventas y operación. |
| Developer experience, DX | Experiencia de quienes integran o mantienen tecnología. | Mejorar APIs, documentación y herramientas. |
| Employee experience, EX | Experiencia de los usuarios internos. | Optimizar operación y adopción. |
| Conversation design | Diseña interacciones mediante texto o voz. | Crear asistentes y chats coherentes. |
| Voice user interface, VUI | Interfaz operada por voz. | Manos libres y accesibilidad. |
| Human-AI experience, HAX | Diseña experiencias con sistemas probabilísticos o agentes. | Asegurar control, corrección y confianza. |
| UX engineering | Traduce diseño a componentes accesibles y mantenibles. | Mantener paridad entre diseño y código. |
| DesignOps | Organiza procesos, herramientas y gobierno del diseño. | Escalar equipos y sistemas. |
| ResearchOps | Organiza participantes, repositorios y prácticas de investigación. | Hacer investigación repetible y ética. |
| ContentOps | Gestiona creación, revisión, traducción y mantenimiento de contenido. | Evitar textos inconsistentes u obsoletos. |

## 2. Cualidades de experiencia

| Término | Descripción breve | Técnica aplicable |
|---|---|---|
| Effectiveness | Exactitud y completitud al lograr una tarea. | Medir tasa de éxito. |
| Efficiency | Tiempo y esfuerzo necesarios. | Reducir pasos y repetición. |
| Satisfaction | Percepción subjetiva del uso. | Medir después de tareas reales. |
| Utility | La función necesaria existe. | Validar el problema antes de optimizar. |
| Usefulness | La solución aporta valor en contexto. | Comparar contra la alternativa actual. |
| Learnability | Facilidad de aprendizaje inicial. | Usar convenciones conocidas. |
| Memorability | Facilidad para volver a usar el sistema. | Mantener posiciones y reglas consistentes. |
| Findability | Facilidad para localizar algo conocido. | Mejorar arquitectura, búsqueda y labels. |
| Discoverability | Facilidad para descubrir funciones desconocidas. | Usar señales, ayuda contextual y onboarding progresivo. |
| Predictability | Posibilidad de anticipar un resultado. | Labels explícitos y comportamiento consistente. |
| Controllability | Posibilidad de dirigir, detener o revertir. | Cancelar, deshacer, editar y aprobar. |
| Error tolerance | Capacidad de resistir y recuperar fallos. | Estados parciales, retry e idempotencia. |
| Continuity | Conservación del contexto durante el trabajo. | Persistir scroll, filtros, selección y borradores. |
| Credibility | Percepción de veracidad y fiabilidad. | Mostrar origen, fecha y estado. |
| Trust calibration | Confianza proporcional a la capacidad real. | Mostrar límites, incertidumbre y evidencia. |
| Perceived performance | Velocidad que percibe el usuario. | Feedback inmediato y carga progresiva. |
| Inclusiveness | Capacidad de servir a usuarios diversos. | Incluir diversidad en investigación y pruebas. |
| Maintainability | Facilidad para evolucionar sin degradación. | Componentes, tokens, contratos y pruebas. |

## 3. Principios cognitivos y heurísticas

Estas reglas orientan decisiones, pero no sustituyen pruebas con usuarios.

| Principio | Idea central | Aplicación |
|---|---|---|
| Recognition over recall | Reconocer es más fácil que recordar. | Mostrar opciones, historial y sugerencias. |
| Cognitive load | Atención y memoria son limitadas. | Reducir decisiones simultáneas. |
| Chunking | La información se comprende mejor en grupos. | Dividir contenido y formularios. |
| Mental model | El usuario interpreta según experiencias previas. | Usar lenguaje y patrones familiares. |
| Jakob's law | Se espera que un producto funcione como otros conocidos. | No reinventar controles sin beneficio demostrado. |
| Hick-Hyman law | Más opciones pueden aumentar el tiempo de decisión. | Priorizar, agrupar y revelar progresivamente. |
| Fitts's law | Objetivos grandes y cercanos son más fáciles de activar. | Aumentar áreas activas y proximidad. |
| Tesler's law | La complejidad no desaparece, se distribuye. | Hacer que el sistema absorba complejidad segura. |
| Aesthetic-usability effect | Una apariencia cuidada puede parecer más usable. | No usar belleza para ocultar problemas. |
| Peak-end rule | La experiencia se recuerda por picos y final. | Cuidar errores críticos y confirmación final. |
| Serial position effect | Inicio y final suelen recordarse mejor. | Colocar prioridades en posiciones fuertes. |
| Von Restorff effect | Un elemento distinto destaca. | Reservar énfasis para la acción principal. |
| Goal-gradient effect | La motivación aumenta cerca de la meta. | Mostrar progreso real y pasos restantes. |
| Progressive disclosure | Mostrar complejidad cuando se necesita. | Separar básico y avanzado. |
| User control and freedom | El usuario necesita salir de estados no deseados. | Añadir cancelar, atrás, cerrar y deshacer. |
| Visibility of system status | El sistema debe comunicar qué ocurre. | Mostrar carga, guardado, cola y error. |
| Consistency and standards | Patrones iguales reducen aprendizaje. | Unificar acciones y estados. |
| Error prevention | Prevenir es mejor que corregir. | Restringir valores y usar defaults seguros. |
| Match with the real world | El sistema debe hablar el lenguaje del usuario. | Evitar nombres internos. |
| Flexibility and efficiency | Novatos y expertos necesitan distintas velocidades. | Añadir atajos sin ocultar el flujo básico. |

## 4. Principios Gestalt

| Principio | Qué comunica | Aplicación |
|---|---|---|
| Proximity | Elementos cercanos están relacionados. | Agrupar mediante espacio. |
| Similarity | Elementos similares pertenecen al mismo grupo. | Mantener estilo por función. |
| Common region | Elementos dentro de una región forman un conjunto. | Cards y secciones. |
| Connectedness | Elementos conectados tienen relación fuerte. | Timelines y grafos. |
| Continuity | La mirada sigue líneas y direcciones. | Alinear pasos y contenido. |
| Closure | La mente completa formas incompletas. | Simplificar iconos sin perder significado. |
| Figure-ground | Se distingue contenido principal del fondo. | Contraste claro entre capas. |
| Common fate | Elementos que se mueven juntos se relacionan. | Coordinar animaciones de grupos. |

## 5. Feedforward, feedback y reglas de interacción

| Término | Descripción breve | Aplicación |
|---|---|---|
| Affordance | Propiedad que sugiere cómo usar algo. | Hacer botones y campos reconocibles. |
| Signifier | Señal visible de una acción. | Label, icono, handle o subrayado. |
| Mapping | Relación entre control y efecto. | Alinear posición y consecuencia. |
| Feedback | Respuesta posterior a una acción. | Confirmar inmediatamente. |
| Feedforward | Información previa sobre lo que ocurrirá. | Preview, labels y consecuencias. |
| Constraint | Límite que evita acciones inválidas. | Restringir sin crear callejones sin salida. |
| Direct manipulation | Manipulación directa del objeto. | Arrastrar, redimensionar o editar inline. |
| Interruptibility | Posibilidad de detener una operación. | IA, cargas y procesos largos. |
| Resumability | Posibilidad de continuar posteriormente. | Formularios y workflows. |
| Input-modality independence | Funciona con teclado, touch, mouse o voz. | No depender de un solo método. |
| Optimistic UI | Refleja éxito antes de confirmación. | Acciones reversibles e idempotentes. |
| Pessimistic UI | Espera confirmación del servidor. | Operaciones críticas. |
| Partial success | Parte de una operación se completa. | Mostrar resultado por elemento. |
| Progressive result | Resultados aparecen conforme están disponibles. | Búsqueda, reportes e IA. |

## 6. Estados avanzados que deben modelarse

| Estado | Significado | Regla |
|---|---|---|
| Initial | Aún no se inicia la carga o tarea. | No confundir con empty. |
| Loading | Se obtiene o procesa información. | Bloquear solo la zona afectada. |
| Refreshing | Existen datos y se actualizan. | Mantener contenido previo. |
| Stale | El dato puede estar desactualizado. | Mostrar fecha o refrescar en segundo plano. |
| Empty | No existen datos. | Explicar el siguiente paso. |
| No results | La consulta no encontró coincidencias. | Conservar filtros y ofrecer recuperación. |
| Partial | Existen datos incompletos. | Diferenciar lo disponible de lo faltante. |
| Success | La operación terminó correctamente. | Confirmar resultado. |
| Warning | Existe riesgo o condición anómala. | Explicar consecuencia. |
| Error | La operación falló. | Mostrar causa y recuperación. |
| Permission denied | Falta autorización. | Explicar cómo solicitar acceso. |
| Rate limited | Se alcanzó un límite temporal. | Mostrar cuándo reintentar. |
| Offline | No existe conexión. | Mostrar datos locales y cola pendiente. |
| Sync pending | Cambios locales aún no llegan al servidor. | No presentarlos como confirmados. |
| Conflict | Existen cambios incompatibles. | Comparar y permitir resolver. |
| Cancelled | La operación fue detenida. | Mantener resultados válidos. |
| Queued | La operación espera ejecución. | Mostrar posición o expectativa. |
| Processing | La operación se ejecuta en backend. | Permitir salir y recibir notificación. |
| Archived | El elemento se conserva fuera de la vista activa. | Permitir restaurar. |
| Deleted | El elemento se eliminó. | Definir ventana de undo o recuperación. |

## 7. Persistencia y continuidad avanzada

| Término | Descripción breve | Uso |
|---|---|---|
| Server state | Datos cuya fuente de verdad es remota. | Entidades y resultados de API. |
| Client state | Estado controlado por la aplicación. | Preferencias y UI temporal. |
| Derived state | Estado calculado desde otros datos. | Contadores y habilitación. |
| State machine | Estados y transiciones explícitas. | Flujos complejos. |
| Finite-state machine | Solo permite estados definidos. | Evitar combinaciones imposibles. |
| URL-driven state | Estado representado en la URL. | Filtros y vistas compartibles. |
| Cache invalidation | Reglas para descartar datos obsoletos. | Mantener coherencia. |
| Optimistic concurrency | Detecta conflictos sin bloqueo permanente. | Edición multiusuario. |
| Preference migration | Actualiza preferencias guardadas entre versiones. | Evitar romper layouts. |
| Session recovery | Restaura trabajo después de un cierre inesperado. | Editores y formularios. |
| Pending-action queue | Guarda acciones aún no confirmadas. | Offline y sincronización. |
| Checkpointing | Guarda puntos seguros intermedios. | Procesos largos y agentes. |

## 8. Search UX

| Término | Descripción breve | Uso |
|---|---|---|
| Typeahead | Muestra resultados durante la escritura. | Búsqueda rápida. |
| Fuzzy search | Tolera errores y variaciones. | Nombres y términos humanos. |
| Synonym handling | Relaciona términos equivalentes. | Dominios con vocabulario variado. |
| Scoped search | Limita la búsqueda a una sección. | Aplicaciones grandes. |
| Faceted search | Combina consulta con filtros. | Catálogos extensos. |
| Saved search | Guarda una consulta. | Trabajo repetitivo. |
| Recent searches | Conserva búsquedas previas. | Retomar tareas. |
| Query persistence | Conserva la consulta al navegar. | Abrir un detalle y regresar. |
| Search relevance | Ordena por utilidad estimada. | Medir éxito, no solo clic. |
| Zero-results recovery | Ayuda a modificar una consulta fallida. | Sugerir limpiar, corregir o ampliar. |

## 9. UX para IA y agentes

| Término o patrón | Descripción breve | Aplicación |
|---|---|---|
| Capability disclosure | Explica qué puede hacer la IA. | Primer uso y contexto. |
| Limitation disclosure | Explica qué no puede garantizar. | Calibrar expectativas. |
| Expectation setting | Define calidad, tiempo y alcance esperados. | Antes de iniciar. |
| Prompt scaffolding | Estructura la solicitud mediante campos o ejemplos. | Reducir ambigüedad. |
| Intent preview | Muestra cómo interpretó la solicitud. | Antes de una acción compleja. |
| Plan preview | Muestra los pasos previstos. | Agentes con múltiples acciones. |
| Tool transparency | Muestra herramientas y fuentes usadas. | Operaciones externas. |
| Grounding | Vincula respuestas con evidencia. | Datos, documentos y búsqueda. |
| Citation UX | Permite revisar la fuente. | Respuestas factuales. |
| Freshness indicator | Muestra fecha de los datos. | Información cambiante. |
| Confidence calibration | Comunica certeza proporcional. | Evitar falsa precisión. |
| Uncertainty handling | Gestiona falta de datos o ambigüedad. | Preguntar, abstenerse o presentar opciones. |
| Editable output | Permite corregir una propuesta. | Textos y datos extraídos. |
| Correction affordance | Ruta explícita para marcar un error. | Clasificación y extracción. |
| Memory transparency | Muestra qué recuerda el sistema. | Preferencias y contexto. |
| Memory control | Permite editar o borrar memoria. | Privacidad y confianza. |
| Context boundary | Explica qué datos o conversación se usan. | Evitar inferencias sorpresivas. |
| Mixed initiative | Usuario e IA alternan control. | Asistencia flexible. |
| Autonomy level | Grado de acción sin aprobación. | Definirlo según riesgo. |
| Approval gate | Requiere aprobación antes de ejecutar. | Enviar, publicar, borrar o pagar. |
| Human-in-the-loop | Una persona participa en la decisión. | Alto riesgo o baja confianza. |
| Human-on-the-loop | Una persona supervisa y puede intervenir. | Automatización continua. |
| Escalation | Transfiere a humano o sistema especializado. | Límites de capacidad. |
| Handoff package | Contexto entregado durante escalación. | Evitar repetición. |
| Agent progress | Estado visible del trabajo. | Planeando, ejecutando o esperando. |
| Agent activity log | Registro de pasos y herramientas. | Auditoría y depuración. |
| Action receipt | Comprobante de una acción ejecutada. | Qué cambió, dónde y cuándo. |
| Interrupt o stop | Detiene generación o ejecución. | Procesos largos. |
| Pause and resume | Pausa y continúa una tarea. | Agentes y jobs. |
| Partial-result UX | Conserva resultados válidos aunque falten otros. | Evitar fallo total. |
| Failure-aware UX | Diseña suponiendo que la IA puede fallar. | Corrección, fallback y recourse. |
| Deterministic action boundary | Usa lógica verificable para acciones críticas. | Precio, permisos, pagos y persistencia. |
| Preview before action | Revisa efectos antes de ejecutar. | Cambios externos. |
| Sandbox preview | Simula cambios en aislamiento. | Código y automatización. |
| Reversible agent action | Acción del agente que puede deshacerse. | Cambios operativos. |
| Trust repair | Recuperación después de un error. | Reconocer, corregir y explicar. |
| Output versioning | Conserva versiones de propuestas. | Comparación y rollback. |
| Safety guardrail UX | Protección visible y proporcional. | Explicar bloqueo y alternativa. |
| Recourse | Ruta para impugnar o corregir una decisión. | Decisiones de impacto. |

## 10. Colaboración y tiempo real

| Término | Descripción breve | Aplicación |
|---|---|---|
| Presence | Indica quién está activo. | Documentos, chats y tickets. |
| Live cursor | Cursor de otra persona. | Edición simultánea. |
| Selection presence | Muestra qué elemento edita otra persona. | Evitar conflictos. |
| Comments | Discusión asociada a contenido. | Revisión. |
| Mentions | Notificación dirigida. | Solicitar atención. |
| Assignment | Responsable explícito. | Tareas, CRM y soporte. |
| Ownership | Propiedad de una entidad. | Responsabilidad. |
| Activity feed | Historial legible de actividad. | Colaboración. |
| Audit log | Registro formal de acciones. | Cumplimiento y diagnóstico. |
| Version history | Versiones recuperables. | Rollback. |
| Pessimistic locking | Bloquea mientras alguien edita. | Datos que no toleran mezcla. |
| Optimistic concurrency | Permite editar y detecta conflicto. | Contenido y formularios. |
| Notification batching | Agrupa avisos. | Reducir fatiga. |
| Read receipt | Indica lectura. | Mensajería con reglas de privacidad. |
| Typing indicator | Indica escritura activa. | Chat en tiempo real. |

## 11. UX de servicio y omnicanal

| Término | Descripción breve | Aplicación |
|---|---|---|
| Customer journey | Recorrido completo de una persona. | Detectar fricciones entre etapas. |
| Journey map | Representación de acciones, canales y percepción. | Alinear equipos. |
| Touchpoint | Punto de interacción con el servicio. | Web, WhatsApp, tienda o soporte. |
| Channel | Medio de interacción. | Diseñar continuidad. |
| Omnichannel | Experiencia coordinada entre canales. | Transferir contexto. |
| Cross-channel continuity | Conserva estado al cambiar de canal. | Evitar repetición. |
| Moment of truth | Interacción de alto impacto. | Pago, error, entrega o soporte. |
| Service blueprint | Mapa de frontstage y backstage. | Conectar UX con operación. |
| Frontstage | Lo visible para el usuario. | Interfaz y atención. |
| Backstage | Procesos invisibles de soporte. | Reglas, integraciones y equipos. |
| Service recovery | Respuesta ante una falla. | Reconocer, resolver y comunicar. |
| SLA communication | Expectativa de tiempo. | Mostrar cuándo se atenderá. |
| Queue transparency | Estado dentro de una cola. | Soporte, turnos y jobs. |
| Operational UX | Experiencia de operadores internos. | Reducir errores y tiempos. |
| Exception handling | Flujo para casos no estándar. | Evitar hacks manuales. |

## 12. Dashboards y visualización de datos

| Término | Descripción breve | Aplicación |
|---|---|---|
| Chart selection | Elección según la pregunta. | Barras para comparación, líneas para tendencia. |
| Preattentive attribute | Propiedad detectada rápidamente. | Posición, longitud, forma o color. |
| Baseline | Referencia de comparación. | Objetivos y valores históricos. |
| Annotation | Explicación dentro de una gráfica. | Destacar eventos. |
| Threshold | Límite significativo. | Alertas y SLA. |
| Small multiples | Gráficas con estructura y escala común. | Comparar segmentos. |
| Drill-down | De resumen a detalle. | Dashboards operativos. |
| Drill-through | Abre registros que explican una métrica. | Auditoría. |
| Cross-filtering | Una selección filtra otras vistas. | Análisis interactivo. |
| Brushing and linking | Selección coordinada entre visualizaciones. | Exploración avanzada. |
| Uncertainty visualization | Representa rangos o confianza. | Predicciones. |
| Accessible chart | Gráfica con tabla o resumen alternativo. | Accesibilidad. |
| Color-safe palette | Paleta distinguible por más personas. | No depender de rojo y verde. |
| Actionable metric | Métrica ligada a una decisión. | Evitar dashboards decorativos. |
| Metric definition | Contrato de cálculo y alcance. | Evitar números contradictorios. |


# Parte IV. Aplicación, auditoría y validación

## 1. Técnicas de implementación

| Técnica | Qué resuelve | Regla de aplicación |
|---|---|---|
| Semantic-first implementation | Accesibilidad y comportamiento nativo. | Elegir HTML correcto antes de ARIA. |
| Component composition | Componentes monolíticos y duplicación. | Componer primitivas con contratos claros. |
| State-machine modeling | Estados imposibles o ambiguos. | Definir estado, evento, transición y efecto. |
| URL state | Navegación no reproducible. | Guardar filtros y tabs compartibles en la URL. |
| Server-state separation | Mezcla de datos remotos y UI local. | Tratar caché, loading y sincronización por separado. |
| Optimistic update | Latencia percibida. | Implementar rollback y reconciliación. |
| Debounced search | Solicitudes excesivas. | Cancelar respuestas obsoletas. |
| Throttled interaction | Eventos demasiado frecuentes. | Limitar scroll, resize y drag. |
| Virtualized rendering | Listas lentas. | Renderizar solo el rango visible. |
| Error boundary | Un fallo rompe toda la pantalla. | Recuperar por región. |
| Progressive boundary | Carga global innecesaria. | Cargar secciones de forma independiente. |
| Feature flag | Riesgo de despliegue. | Lanzar gradualmente y retirar flags obsoletos. |
| Design-token implementation | Valores inconsistentes. | Consumir tokens semánticos. |
| Responsive component API | Lógica responsive duplicada. | Adaptar por contenedor y capacidad. |
| Focus management utility | Foco perdido en overlays. | Contener solo en modales y restaurar al cerrar. |
| Live-region utility | Cambios dinámicos invisibles para lector. | Anunciar solo eventos relevantes. |
| Idempotency key | Envíos o publicaciones duplicados. | Usar en operaciones externas. |
| Undo buffer | Acciones reversibles sin recuperación. | Retener estado durante una ventana definida. |
| Draft storage | Pérdida de contenido. | Versionar, expirar y proteger borradores. |
| Telemetry instrumentation | Falta de evidencia. | Registrar eventos con nombres y propiedades estables. |
| Visual regression | Cambios visuales accidentales. | Usar capturas deterministas. |
| Accessibility automation | Regresiones básicas. | Complementar con teclado y lector de pantalla. |
| Contract testing | Desalineación frontend-backend. | Probar success, partial, error y permisos. |
| Loading-state contract | Estados inconsistentes. | Definir initial, loading, refresh, stale y error. |
| Permission-aware rendering | Acciones que el backend rechazará. | Alinear interfaz con autorización real. |
| Locale-safe formatting | Fechas y moneda incorrectas. | Usar APIs de internacionalización. |
| Incremental update | Recarga completa por cambio local. | Actualizar solo la entidad afectada. |
| Request deduplication | Peticiones repetidas. | Compartir solicitudes idénticas. |
| Cache invalidation | Datos obsoletos. | Invalidar por evento y fuente de verdad. |
| Background synchronization | Bloqueo por operaciones secundarias. | Sincronizar sin impedir tareas independientes. |

## 2. Técnicas por etapa del ciclo de producto

| Etapa | Técnicas recomendadas | Entregable esperado |
|---|---|---|
| Discovery | Entrevistas, observación, analytics y JTBD. | Problemas, contexto y riesgos. |
| Definición | Task analysis, opportunity mapping e hipótesis. | Problema priorizado y criterio de éxito. |
| Arquitectura | Content inventory, card sorting y tree testing. | Taxonomía, sitemap y navegación. |
| Flujos | User flow, task flow y service blueprint. | Estados, decisiones y handoffs. |
| Diseño temprano | Sketch, wireframe y content-first. | Estructura sin detalle visual innecesario. |
| Prototipado | Lo-fi, hi-fi y prototype interactivo. | Hipótesis evaluable. |
| Validación | Usability test, accessibility review y walkthrough. | Hallazgos con evidencia y severidad. |
| Diseño visual | Tokens, jerarquía, responsive y estados. | Especificación y componentes. |
| Implementación | Component-driven, semantic HTML y state machine. | Código reutilizable. |
| QA | Pruebas funcionales, visuales, a11y, rendimiento y error. | Evidencia reproducible. |
| Lanzamiento | Feature flag, pilot y telemetry. | Despliegue controlado. |
| Medición | Funnel, task success, Core Web Vitals y soporte. | Impacto real. |
| Iteración | Triangulación y experimentos. | Correcciones verificadas. |
| Gobierno | Design system, deuda y deprecación. | Consistencia a largo plazo. |

## 3. Métodos de investigación que deben distinguirse

| Clasificación | Pregunta principal | Ejemplos |
|---|---|---|
| Generative | Qué problema existe y por qué. | Entrevistas, campo y diario. |
| Evaluative | Qué tan bien funciona una solución. | Usability testing y benchmark. |
| Attitudinal | Qué dicen o creen las personas. | Entrevistas y encuestas. |
| Behavioral | Qué hacen realmente. | Pruebas, observación y analytics. |
| Qualitative | Por qué ocurre. | Sesiones moderadas. |
| Quantitative | Cuánto y con qué frecuencia. | Métricas, encuestas y experimentos. |
| Moderated | Investigador guía la sesión. | Tareas complejas. |
| Unmoderated | Participante completa sin moderador. | Escala y tareas simples. |
| Longitudinal | Cómo cambia durante un periodo. | Hábitos y retención. |
| Cross-sectional | Cómo difiere entre grupos en un momento. | Segmentos y variantes. |

## 4. Técnicas de análisis

| Técnica | Uso |
|---|---|
| Affinity mapping | Agrupar observaciones y encontrar temas. |
| Thematic analysis | Identificar patrones cualitativos. |
| Severity rating | Priorizar por impacto, frecuencia y persistencia. |
| Root-cause analysis | Distinguir síntoma de causa. |
| Task analysis | Descomponer una tarea y sus decisiones. |
| Hierarchical task analysis | Modelar objetivos, subtareas y planes. |
| Mental-model diagram | Comparar expectativas con estructura. |
| Opportunity mapping | Relacionar necesidad, problema y solución. |
| Assumption mapping | Priorizar supuestos por riesgo e incertidumbre. |
| Hypothesis statement | Definir cambio, audiencia, resultado y medición. |
| Evidence matrix | Relacionar hallazgo, evidencia, confianza y decisión. |
| Triangulation | Combinar métodos para reducir falsos positivos. |

## 5. Métricas de experiencia

| Métrica | Qué mide | Uso |
|---|---|---|
| Task success rate | Tareas completadas correctamente. | Efectividad. |
| Time on task | Tiempo necesario. | Eficiencia. |
| Error rate | Errores por tarea o sesión. | Claridad y prevención. |
| Completion rate | Flujos finalizados. | Formularios y onboarding. |
| Abandonment rate | Flujos abandonados. | Fricción. |
| First-click success | Primer destino correcto. | Navegación. |
| Findability rate | Éxito para localizar contenido. | Arquitectura de información. |
| Search success rate | Búsquedas que logran el objetivo. | Search UX. |
| Zero-results rate | Consultas sin coincidencias. | Cobertura y vocabulario. |
| Recovery rate | Errores de los que el usuario se recupera. | Resiliencia. |
| Time to recovery | Tiempo para corregir un fallo. | Error UX. |
| SUS | Percepción general de usabilidad. | Benchmark. |
| UMUX-Lite | Percepción breve de utilidad y facilidad. | Encuestas compactas. |
| SEQ | Dificultad percibida de una tarea. | Después de cada tarea. |
| CES | Esfuerzo percibido. | Soporte y procesos. |
| CSAT | Satisfacción inmediata. | Interacción específica. |
| NPS | Intención declarada de recomendar. | Relación general, no diagnóstico de UI. |
| Activation rate | Usuarios que alcanzan valor inicial. | Onboarding. |
| Adoption rate | Uso de una función. | Lanzamientos. |
| Retention | Usuarios que continúan. | Valor sostenido. |
| Conversion rate | Cumplimiento de objetivo comercial. | Evaluar junto con calidad y ética. |
| Rage clicks | Clics repetidos por frustración. | Interacción rota. |
| Dead clicks | Clics sin resultado. | Affordance falsa. |
| Backtracking | Regresos repetidos. | Navegación o comprensión. |
| Support-contact rate | Necesidad de soporte. | Fricción no resuelta. |
| Accessibility violations | Incumplimientos detectados. | Calidad mínima. |
| LCP | Carga del contenido principal. | Rendimiento. |
| INP | Respuesta a interacciones. | Responsiveness. |
| CLS | Estabilidad visual. | Evitar saltos. |
| Trust calibration | Alineación entre confianza y precisión. | IA. |
| Human override rate | Intervenciones sobre automatización. | Autonomía mal calibrada. |
| Handoff success | Transferencias sin pérdida de contexto. | Soporte e IA. |

## 6. Baseline técnico recomendado

### Accesibilidad

- WCAG 2.2 nivel AA como baseline para web.
- HTML semántico antes de ARIA.
- WAI-ARIA Authoring Practices para widgets complejos.
- Navegación completa con teclado.
- Focus visible, orden lógico y restauración de foco.
- No depender exclusivamente de color, hover, iconos o drag-and-drop.
- WCAG 2.2 establece un objetivo mínimo de 24 por 24 píxeles CSS con excepciones.
- En Material Design se recomienda un touch target de al menos 48 por 48 dp.
- Respetar `prefers-reduced-motion`.
- Probar reflow, zoom, alto contraste y lector de pantalla.

### Rendimiento

Objetivos recomendados de Core Web Vitals:

```text
LCP <= 2.5 s
INP <= 200 ms
CLS <= 0.1
```

Además:

- Medir con datos reales de usuarios.
- Evitar recargas completas por cambios locales.
- Virtualizar listas grandes.
- Reservar espacio para evitar layout shift.
- Cargar de forma incremental.
- Mantener feedback inmediato aunque el backend tarde.

## 7. Decisiones rápidas de patrones

| Necesidad | Patrón recomendado | Evitar |
|---|---|---|
| Mostrar detalle sin abandonar una lista | Drawer o master-detail. | Modal grande para navegación frecuente. |
| Pedir una decisión crítica breve | Modal dialog. | Drawer que puede ignorarse. |
| Mostrar acciones ancladas | Popover o dropdown. | Drawer. |
| Explicar un icono | Tooltip en hover y focus. | Contenido esencial solo en tooltip. |
| Cambiar entre vistas hermanas | Tabs o segmented control. | Stepper. |
| Mostrar progreso lineal | Stepper o progress indicator. | Tabs. |
| Elegir un valor continuo | Slider. | Carousel. |
| Mostrar contenido secuencial | Carousel con slides. | Slider de valor. |
| Mover elementos entre conjuntos | Transfer list o dual-pane selector. | Multiselect sin resultado visible. |
| Administrar muchos registros | Data table o virtualized list. | Cards grandes. |
| Explorar contenido visual | Card grid o masonry. | Tabla. |
| Acción reversible | Ejecutar y ofrecer Undo. | Confirmación repetitiva. |
| Proceso largo asíncrono | Background job, progreso y notificación. | Bloqueo total. |
| Carga de estructura conocida | Skeleton. | Spinner global. |
| Carga breve de una acción | Spinner dentro del control. | Skeleton de toda la página. |
| Sin contenido inicial | Empty state. | No-results. |
| Búsqueda sin coincidencias | No-results con recuperación. | Empty state genérico. |
| Filtros complejos en móvil | Filter drawer o bottom sheet. | Barra saturada. |
| Muchos comandos | Command palette más navegación visible. | Funciones completamente ocultas. |
| IA que ejecutará cambios | Plan preview, approval gate y receipt. | Ejecución silenciosa. |

## 8. Antipatrones frecuentes

| Antipatrón | Problema | Corrección |
|---|---|---|
| Icon-only ambiguity | El icono no es evidente. | Añadir label, tooltip y nombre accesible. |
| Placeholder as label | El nombre desaparece al escribir. | Usar label persistente. |
| Disabled without explanation | No se sabe cómo habilitar. | Mostrar requisito o acción. |
| Modal overuse | Interrumpe y pierde contexto. | Usar drawer, popover o inline. |
| Drawer overuse | Panel excesivo para contenido breve. | Usar tooltip o popover. |
| Toast for critical error | Desaparece antes de resolverse. | Error inline o banner. |
| Spinner for long process | No comunica avance. | Progress y estado. |
| Skeleton for unknown structure | Crea expectativa falsa. | Progress indicator. |
| Infinite scroll for task lists | Dificulta ubicación y regreso. | Paginación o load more. |
| Carousel for critical content | Oculta información. | Mostrar contenido estable. |
| Color-only status | No es accesible. | Añadir texto, forma o icono. |
| Hover-only action | No funciona con touch o teclado. | Ruta visible alternativa. |
| Drag-only interaction | No es accesible. | Botones y teclado. |
| Confirmation fatigue | Se ignoran diálogos. | Undo para acciones reversibles. |
| Generic error | No permite corregir. | Causa, alcance y recuperación. |
| Full-page loading | Bloquea trabajo no relacionado. | Carga por regiones. |
| State reset on navigation | Pierde contexto. | Restaurar estado. |
| Theme flash | Muestra tema incorrecto al iniciar. | Hidratar antes del primer paint. |
| Silent autosave failure | Puede perder datos. | Estado visible y retry. |
| Optimistic UI without rollback | Estado falso permanente. | Reconciliar y revertir. |
| Duplicate design patterns | Reglas distintas para lo mismo. | Consolidar en design system. |
| Overvalidation | Bloquea resultados recuperables. | Separar errores críticos de metadata auxiliar. |
| Guardrail without recovery | Crea un callejón sin salida. | Explicar y ofrecer alternativa. |
| Premature personalization | La UI cambia de forma impredecible. | Control, explicación y reset. |
| Dark pattern | Manipula decisiones. | Opciones equivalentes y consentimiento claro. |
| AI confidence theater | Certeza visual sin evidencia. | Fuentes, límites y recourse. |
| Hidden agent action | La IA cambia datos sin claridad. | Preview, aprobación y receipt. |
| No partial success | Un fallo menor borra resultados válidos. | Estado por componente. |
| Over-animation | Distracción y fatiga. | Movimiento funcional. |
| Responsive shrink-only | Solo reduce tamaños. | Reorganizar estructura. |

## 9. Formato de hallazgo de auditoría

```text
ID:
Categoría:
Severidad:
Pantalla o flujo:
Problema observado:
Evidencia:
Impacto en la tarea:
Primer punto real de divergencia:
Causa probable:
Corrección mínima:
Patrón o término aplicable:
Criterios de aceptación:
Prueba reproducible:
Riesgo de regresión:
Estado comprobable:
```

### Severidad

| Nivel | Definición |
|---|---|
| S0 Bloqueante | Impide una tarea crítica o causa pérdida, exposición o acción incorrecta. |
| S1 Alta | Provoca fallos frecuentes, abandono o recuperación costosa. |
| S2 Media | Aumenta esfuerzo, confusión o tiempo, pero existe ruta alternativa. |
| S3 Baja | Inconsistencia o mejora menor. |

## 10. Prompt maestro para Codex

```text
Actúa como arquitecto de frontend, diseñador de producto, auditor de UX,
especialista en accesibilidad y responsable de calidad de interfaz.

OBJETIVO

Audita e implementa la mejora solicitada sin limitarte al aspecto visual.
Evalúa estructura, comportamiento, estado, contenido, accesibilidad,
rendimiento, confianza y pruebas.

REGLAS

1. Analiza primero el código, componentes, stores, rutas y design system.
2. No dupliques componentes, estilos, stores, contratos ni validadores.
3. No inventes problemas ni declares una mejora implementada sin evidencia.
4. Distingue:
   - problema visual;
   - arquitectura de información;
   - interacción;
   - persistencia o estado;
   - datos o backend;
   - accesibilidad;
   - rendimiento;
   - contenido;
   - permisos, confianza o IA.
5. Mantén el contexto:
   - scroll;
   - búsqueda;
   - filtros;
   - orden;
   - selección;
   - tab activa;
   - secciones expandidas o colapsadas;
   - tamaños de paneles;
   - borradores;
   - estado específico por entidad.
6. Define y prueba:
   - default;
   - hover;
   - focus visible;
   - active;
   - selected;
   - disabled;
   - loading;
   - refreshing;
   - stale;
   - empty;
   - no results;
   - partial success;
   - error;
   - permission denied;
   - offline;
   - recovery.
7. Usa HTML semántico y patrones de teclado apropiados.
8. Cumple WCAG 2.2 AA como baseline.
9. No dependas solo de color, hover, drag-and-drop o iconos.
10. Las acciones críticas deben mostrar consecuencia, preview, aprobación o
    recuperación según el riesgo.
11. Las acciones reversibles deben preferir Undo.
12. Las operaciones deben ser idempotentes cuando un retry pueda duplicarlas.
13. Una falla secundaria no debe borrar un resultado principal válido.
14. Para IA o agentes:
    - muestra capacidades y límites;
    - conserva evidencia y fuentes;
    - comunica incertidumbre;
    - permite detener, corregir y escalar;
    - requiere aprobación para efectos externos;
    - registra acciones ejecutadas;
    - diferencia IA, usuario, sistema e integración.

ENTREGA

1. Estado inicial comprobado.
2. Hallazgos con evidencia.
3. Primer punto real de divergencia.
4. Solución mínima seleccionada.
5. Archivos modificados.
6. Contratos y estados afectados.
7. Criterios de aceptación.
8. Pruebas automatizadas.
9. Pruebas manuales reproducibles.
10. Riesgos y elementos no comprobables.

No marques READY, COMPLETE o IMPLEMENTED sin pruebas suficientes.
```

## 11. Checklist de aceptación

### Visual

- [ ] Jerarquía clara.
- [ ] Tipografía, espacios, colores y radios usan tokens.
- [ ] Estados visuales consistentes.
- [ ] El color no es la única señal.
- [ ] Light y dark mantienen legibilidad.

### Navegación y estructura

- [ ] El usuario sabe dónde está.
- [ ] Existe una ruta clara para regresar.
- [ ] Back y deep links restauran un estado coherente.
- [ ] La nomenclatura coincide con el lenguaje del usuario.
- [ ] Filtros, búsqueda y selección se conservan cuando corresponde.

### Interacción

- [ ] La acción principal es evidente.
- [ ] Toda acción produce feedback.
- [ ] Hover no es la única ruta.
- [ ] Drag-and-drop tiene alternativa.
- [ ] Existen Undo, cancelar o recovery según el riesgo.
- [ ] No existen dead clicks.

### Estado y persistencia

- [ ] Se distingue UI state de server state.
- [ ] El estado por entidad no contamina otras entidades.
- [ ] Scroll, búsqueda y filtros se restauran.
- [ ] El tema se hidrata sin flash.
- [ ] Los borradores no se pierden.
- [ ] No se almacenan secretos en `localStorage`.

### Feedback

- [ ] Loading, empty, no-results y error son distintos.
- [ ] Los procesos largos muestran progreso o estado.
- [ ] Los errores indican causa y recuperación.
- [ ] Autosave comunica guardando, guardado y error.
- [ ] Los cambios dinámicos importantes se anuncian accesiblemente.

### Accesibilidad

- [ ] La pantalla funciona con teclado.
- [ ] Focus visible y orden lógico.
- [ ] Modales contienen y restauran foco.
- [ ] Controles tienen nombre accesible.
- [ ] HTML semántico antes de ARIA.
- [ ] Contraste y target size cumplen baseline.
- [ ] Zoom, reflow y reduced motion funcionan.

### Responsive y rendimiento

- [ ] El layout se reorganiza, no solo se encoge.
- [ ] No hay contenido crítico oculto.
- [ ] Listas grandes usan paginación o virtualización.
- [ ] No se recarga toda la pantalla por un cambio local.
- [ ] Se miden LCP, INP y CLS.
- [ ] No existen saltos visuales evitables.

### Confianza e IA

- [ ] Origen y fecha de datos son visibles cuando importan.
- [ ] Usuario, IA, sistema e integración están diferenciados.
- [ ] La IA declara límites y permite corrección.
- [ ] Acciones externas requieren aprobación proporcional.
- [ ] Existe historial o receipt de cambios.
- [ ] Los fallos parciales conservan resultados válidos.
- [ ] El handoff transfiere contexto.

# Referencias base consultadas

| Referencia | Área |
|---|---|
| Web Content Accessibility Guidelines 2.2, W3C WAI | Accesibilidad |
| ARIA Authoring Practices Guide, W3C WAI | Widgets, semántica y teclado |
| ISO 9241-11:2018 | Usabilidad |
| ISO 9241-210 | Diseño centrado en las personas |
| Nielsen Norman Group, 10 Usability Heuristics | Heurísticas |
| Nielsen Norman Group, UX Research Methods | Investigación |
| Material Design 3 | Fundamentos, componentes, estados y touch targets |
| Apple Human Interface Guidelines | Plataformas e interacción |
| Microsoft Fluent 2 Design System | Componentes, motion, contenido y Wait UX |
| IBM Carbon Design System | Design system, contenido y movimiento |
| GOV.UK Design System | Componentes y patrones respaldados por investigación |
| web.dev Core Web Vitals | Rendimiento |
| Microsoft HAX Toolkit | Experiencias con IA |
| Google People + AI Guidebook | IA centrada en las personas |

## Nota de alcance

Esta guía es una referencia amplia, no una norma única ni una lista cerrada.

Cuando existan alternativas:

1. Priorizar la necesidad y la evidencia del usuario.
2. Cumplir requisitos legales y de accesibilidad.
3. Seguir convenciones de la plataforma.
4. Mantener consistencia con el producto.
5. Elegir la solución mínima, comprensible, reversible y verificable.
