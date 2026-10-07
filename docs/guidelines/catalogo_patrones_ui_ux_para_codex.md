# Catálogo de patrones UI/UX para implementación con Codex

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

# 11. Identificación del patrón mostrado en la pantalla

La pantalla analizada utiliza una combinación de los siguientes patrones:

- Transfer list.
- Dual-pane selector.
- Grouped list.
- Virtualized list.
- Multi-select con checkboxes.
- Bulk transfer controls.
- Search.
- Faceted filters.
- Empty state.
- Sync indicator.
- Status badges.
- Counter badges.

Nombre técnico recomendado para el componente:

```text
DestinationGroupTransferPanel
```

Alternativas:

```text
GroupTransferSelector
DualPaneGroupSelector
PublishTargetSelector
DestinationGroupsSelector
```

---

# 12. Recomendaciones específicas para la pantalla de grupos destino

## 12.1 Mantener la estructura de dos columnas

La estructura de dos paneles es adecuada porque permite comparar:

- Grupos disponibles.
- Grupos seleccionados.
- Cantidad total.
- Estado de membresía.
- Categoría.
- Resultado de filtros.

No sustituirla por un modal simple ni por un select convencional.

---

## 12.2 Mejorar los controles centrales

Los botones actuales con símbolos:

```text
→
»
←
«
```

pueden resultar ambiguos.

Sustituirlos por botones con icono, texto accesible y tooltip:

```text
Agregar seleccionados
Agregar todos los filtrados
Quitar seleccionados
Quitar todos
```

Requisitos:

- `aria-label`.
- Tooltip visible.
- Estado disabled cuando la acción no aplique.
- Atajo de teclado opcional.
- Confirmación visual inmediata.

---

## 12.3 Agregar selección mediante doble clic

Permitir:

```text
Doble clic en grupo disponible -> agregar.
Doble clic en grupo elegido -> quitar.
```

Mantener checkbox para selección múltiple.

No depender exclusivamente del doble clic porque no es evidente ni accesible en móvil.

---

## 12.4 Agregar drag-and-drop

Permitir arrastrar grupos de un panel al otro.

Requisitos:

- Drag preview.
- Zona de destino resaltada.
- Soporte para selección múltiple.
- Alternativa completa mediante teclado y botones.
- No usar drag-and-drop como único mecanismo.

---

## 12.5 Agregar barra de acciones masivas

Cuando existan elementos seleccionados, mostrar una barra contextual:

```text
3 grupos seleccionados
[Agregar]
[Verificar]
[Limpiar selección]
```

En el panel derecho:

```text
3 grupos seleccionados
[Quitar]
[Verificar]
[Limpiar selección]
```

La barra debe desaparecer cuando no exista selección.

---

## 12.6 Agregar drawer de detalles

Al hacer clic en un grupo, abrir un drawer lateral derecho con:

- Imagen o portada del grupo.
- Nombre.
- ID.
- Categoría.
- Cantidad de miembros.
- Estado de membresía.
- Permisos disponibles.
- Última verificación.
- Último error.
- Historial de sincronización.
- Preview de publicación.
- Botón verificar.
- Botón agregar o quitar.
- Enlace externo al grupo, si existe.

El drawer debe abrirse sin perder:

- Scroll.
- Filtros.
- Selección.
- Posición de la lista.

---

## 12.7 Usar lista virtualizada

La pantalla contiene cientos de grupos.

Implementar virtualización para evitar renderizar todos los elementos al mismo tiempo.

Opciones técnicas:

- `@tanstack/react-virtual`
- `react-window`
- `react-virtuoso`

La lista debe soportar:

- Altura variable si aplica.
- Sticky section headers.
- Selección persistente.
- Scroll restoration.
- Búsqueda.
- Filtros.
- Agrupación.

---

## 12.8 Mantener buscadores y encabezados fijos

Los siguientes elementos deben permanecer visibles durante el scroll:

- Título del panel.
- Contador.
- Buscador.
- Filtros.
- Barra de selección.
- Acciones masivas.

Usar:

```css
position: sticky;
top: 0;
z-index: adecuado;
```

Evitar que el fondo sea transparente durante el scroll.

---

## 12.9 Mostrar filtros activos como chips

Ejemplo:

```text
Mercado Libre Monterrey ×
Motos-Crédito ×
Miembro ×
Verificados ×
```

Agregar acción:

```text
Limpiar filtros
```

Los chips deben aparecer debajo del buscador o dentro de una barra de filtros.

---

## 12.10 Mejorar los contadores

Mostrar contadores claros:

```text
625 disponibles
12 seleccionados
908 totales
576 sin clasificar
```

Evitar formatos ambiguos como:

```text
2/908
0 de 0
```

cuando no se explique qué significa cada número.

---

## 12.11 Estados individuales por grupo

Cada grupo debe mostrar un estado explícito:

```text
Miembro
No miembro
Verificando
Verificado
Sin permisos
No disponible
Error
Pendiente de sincronización
```

Cada estado debe tener:

- Texto.
- Icono.
- Color semántico.
- Tooltip con detalle.
- Acción de recuperación si aplica.

No depender exclusivamente del color.

---

## 12.12 Acción “Deshacer”

Al quitar un grupo:

```text
Grupo eliminado de destinos.
[Deshacer]
```

No pedir confirmación para acciones fácilmente reversibles.

Usar confirmación solamente para:

- Quitar todos.
- Publicar en gran cantidad de grupos.
- Eliminar configuración persistente.
- Acciones con efectos externos no reversibles.

---

## 12.13 Persistencia de contexto

Mantener al cambiar de vista o abrir detalles:

- Filtros.
- Texto de búsqueda.
- Scroll.
- Selección.
- Grupos elegidos.
- Categoría expandida.
- Ordenamiento.
- Densidad visual.

Persistir en:

- Estado local.
- URL query params.
- Store global.
- `sessionStorage` si aplica.

---

## 12.14 Estado vacío mejorado

En lugar de mostrar solamente:

```text
Aún no has elegido grupos destino
```

usar:

```text
Aún no has elegido grupos destino.

Selecciona uno o varios grupos del panel izquierdo y agrégalos para definir dónde se publicará el contenido.
```

Acciones posibles:

```text
Agregar seleccionados
Agregar todos los filtrados
```

---

## 12.15 Estado de sincronización

Sustituir mensajes ambiguos como:

```text
Sincronizando...
625 de 625
```

por estados claros:

```text
Sincronización completa
625 grupos actualizados
Hace 2 minutos
```

Durante el proceso:

```text
Sincronizando grupos
420 de 625
67 %
```

En error:

```text
No se pudieron sincronizar 8 grupos
[Ver detalles]
[Reintentar]
```

---

# 13. Estructura de componente recomendada

```tsx
<DestinationGroupsPage>
  <PageHeader />

  <DestinationGroupTransferPanel>
    <AvailableGroupsPanel>
      <PanelHeader />
      <SearchBar />
      <FiltersToolbar />
      <ActiveFilterChips />
      <BulkSelectionBar />
      <VirtualizedGroupedList />
    </AvailableGroupsPanel>

    <TransferActions />

    <SelectedGroupsPanel>
      <PanelHeader />
      <SearchBar />
      <BulkSelectionBar />
      <VirtualizedList />
      <EmptyState />
    </SelectedGroupsPanel>
  </DestinationGroupTransferPanel>

  <GroupDetailsDrawer />
  <SyncStatusBanner />
  <UndoSnackbar />
</DestinationGroupsPage>
```

---

# 14. Modelo de estado recomendado

```ts
type GroupStatus =
  | "member"
  | "not_member"
  | "verifying"
  | "verified"
  | "missing_permissions"
  | "unavailable"
  | "sync_pending"
  | "error";

type DestinationGroup = {
  id: string;
  name: string;
  category: string | null;
  platform: "facebook";
  memberCount?: number;
  status: GroupStatus;
  isSelected: boolean;
  isDestination: boolean;
  lastVerifiedAt?: string;
  lastSyncedAt?: string;
  errorCode?: string;
  errorMessage?: string;
};

type GroupFilters = {
  accountId?: string;
  category?: string;
  membershipStatus?: GroupStatus[];
  verificationStatus?: GroupStatus[];
  query: string;
};

type DestinationGroupsState = {
  availableGroups: DestinationGroup[];
  destinationGroups: DestinationGroup[];
  selectedAvailableIds: Set<string>;
  selectedDestinationIds: Set<string>;
  filters: GroupFilters;
  activeGroupId?: string;
  drawerOpen: boolean;
  syncing: boolean;
  syncProgress?: {
    completed: number;
    total: number;
  };
};
```

---

# 15. Reglas de UX para la implementación

1. Toda acción debe producir retroalimentación visible.
2. Toda acción destructiva debe ser reversible o confirmada.
3. No usar iconos sin tooltip cuando su significado no sea evidente.
4. No depender exclusivamente del color para comunicar estados.
5. Mantener la selección y el scroll al abrir detalles.
6. No recargar toda la lista por una modificación individual.
7. No bloquear toda la pantalla durante una verificación individual.
8. Mostrar estados por fila.
9. Mostrar estados globales de sincronización por separado.
10. Usar skeleton durante la primera carga.
11. Usar spinner solamente para acciones pequeñas.
12. Usar virtualización para listas grandes.
13. Permitir navegación completa con teclado.
14. Mantener objetivos táctiles de al menos 44 x 44 px en móvil.
15. Mantener contraste suficiente en texto, botones y estados.
16. Evitar confirmaciones repetitivas.
17. Priorizar acciones masivas cuando existan muchos elementos.
18. Mantener la acción principal visible.
19. Mostrar errores junto al elemento que falló.
20. No eliminar selecciones al cambiar filtros.

---

# 16. Accesibilidad mínima

Implementar:

```text
Tab
Shift + Tab
Enter
Space
Escape
Arrow Up
Arrow Down
Home
End
Ctrl/Cmd + A
```

Requisitos:

- Focus visible.
- Orden de tabulación lógico.
- `aria-label` en botones de icono.
- `aria-selected` en filas.
- `aria-expanded` en grupos colapsables.
- `aria-live` para mensajes de sincronización.
- `role="status"` para progreso.
- `role="alert"` para errores críticos.
- Contraste WCAG AA.
- No bloquear zoom.
- No ocultar información exclusivamente en hover.

---

# 17. Criterios de aceptación

## Transferencia

- El usuario puede agregar uno o varios grupos.
- El usuario puede quitar uno o varios grupos.
- El usuario puede agregar todos los grupos filtrados.
- El usuario puede quitar todos los grupos elegidos.
- Los botones se deshabilitan cuando no aplican.
- La selección no se pierde al cambiar filtros.

## Búsqueda y filtros

- La búsqueda responde sin bloquear la interfaz.
- Los filtros activos son visibles.
- Existe acción para limpiar filtros.
- Los filtros pueden persistirse.
- El estado sin resultados es diferente al estado vacío.

## Drawer

- El drawer muestra detalles del grupo.
- Abrir y cerrar el drawer no altera el scroll.
- Escape cierra el drawer.
- El foco regresa al elemento que lo abrió.

## Rendimiento

- La interfaz permanece fluida con más de 900 grupos.
- No se renderizan todos los grupos simultáneamente.
- La selección no produce recargas globales.
- La sincronización muestra progreso.

## Accesibilidad

- Todas las acciones funcionan con teclado.
- Los botones de icono tienen texto accesible.
- Los estados no dependen solamente del color.
- Los mensajes importantes son anunciados por lectores de pantalla.

---

# 18. Prioridad de implementación

## Prioridad 1

- Corregir etiquetas y botones ambiguos.
- Agregar estados de carga, error y vacío.
- Implementar lista virtualizada.
- Mantener buscador y filtros fijos.
- Agregar barra de acciones masivas.
- Persistir selección y filtros.
- Agregar tooltips y accesibilidad.

## Prioridad 2

- Drawer de detalles.
- Drag-and-drop.
- Doble clic.
- Preview de publicación.
- Filtros guardados.
- Atajos de teclado.

## Prioridad 3

- Densidad configurable.
- Animaciones avanzadas.
- Shared element transitions.
- Historial detallado.
- Personalización de layout.

---

# 19. Resultado esperado

La pantalla debe sentirse como una herramienta profesional de selección masiva:

- Rápida.
- Predecible.
- Escalable.
- Accesible.
- Limpia.
- Sin acciones ambiguas.
- Sin pérdida de contexto.
- Con información suficiente antes de publicar.
