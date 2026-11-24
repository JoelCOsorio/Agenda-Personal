# Especificación de Requerimientos de Software (ERS)
## Proyecto: Agenda Personal y Académica

---

### 1. Introducción y Propósito
El objetivo de este proyecto es desarrollar una aplicación integral de gestión de tiempo y actividades orientada tanto al ámbito personal como al académico. El sistema permite planificar itinerarios, gestionar entregas y mantener un directorio de contactos clave, organizados bajo una estructura modular e intuitiva.

---

### 2. Actores del Sistema
* **Usuario (Estudiante / Docente / Usuario General):** Persona que interactúa con la aplicación para registrar sus materias, agendar eventos, dar seguimiento a tareas pendientes y consultar contactos.

---

### 3. Requisitos Funcionales (RF)

#### Módulo 0: Núcleo Académico (Materias / Asignaturas)
*Este módulo actúa como eje articulador entre eventos, tareas y contactos académicos.*

* **RF-01 (Gestión de Materias):** El sistema debe permitir registrar, consultar, modificar y eliminar materias/asignaturas.
* **RF-02 (Atributos de Materia):** Cada materia debe incluir: nombre, código/sigla, profesor asignado, aula/enlace virtual y un color identificador para la interfaz y el calendario.
* **RF-03 (Filtro por Materia):** El usuario podrá filtrar su agenda y lista de tareas para visualizar únicamente los elementos asociados a una materia específica.

---

#### Módulo 1: Agenda y Eventos
* **RF-04 (CRUD de Eventos):** El usuario podrá crear, visualizar, editar y eliminar eventos en su agenda.
* **RF-05 (Detalle del Evento):** Cada evento debe registrar:
  * Título y descripción.
  * Fecha y hora de inicio y fin.
  * Tipo de evento (*Clase, Examen, Reunión, Personal, etc.*).
  * Ubicación (física o enlace virtual).
  * Materia asociada (opcional).
  * Color o etiqueta distintiva.
* **RF-06 (Eventos Recurrentes):** El sistema debe soportar reglas de repetición periódica (diaria, semanal en días específicos o mensual), fundamental para horarios de clase regulares.
* **RF-07 (Vistas Temporales):** El sistema debe ofrecer las siguientes perspectivas de visualización:
  * **Vista Diaria:** Lista cronológica detallada de actividades del día.
  * **Vista Semanal:** Parrilla horaria de lunes a domingo.
  * **Vista Mensual:** Cuícula de calendario tradicional con indicadores visuales de eventos.
  * **Vista Anual:** Mapa global de meses con mapa de calor o conteo de actividades.
* **RF-08 (Recordatorios y Notificaciones):**
  * El usuario podrá configurar alertas para un evento: al momento del inicio, con antelación fija (10 min, 30 min, 1 hora, 1 día antes) o con un tiempo personalizado.
  * El sistema debe emitir la notificación correspondiente cuando se cumpla la condición temporal.
* **RF-09 (Historial y Eventos Pasados):** El usuario podrá consultar eventos previos para revisar su historial de actividades.

---

#### Módulo 2: Gestión de Tareas
* **RF-10 (CRUD de Tareas):** El usuario podrá registrar, consultar, modificar y dar de baja tareas o pendientes.
* **RF-11 (Atributos de Tarea):** Cada tarea contará con:
  * Título y descripción detallada.
  * Fecha y hora límite de entrega (*deadline*).
  * Estado: *Pendiente*, *En progreso*, *Completada*.
  * Nivel de prioridad: *Alta*, *Media*, *Baja*.
  * Materia o categoría vinculada (opcional).
* **RF-12 (Subtareas / Lista de Verificación):** El usuario podrá añadir subtareas o ítems de control (*checklist*) dentro de una tarea principal.
* **RF-13 (Filtros y Ordenamiento):** El sistema debe permitir ordenar y filtrar tareas por: estado de finalización, proximidad de fecha de entrega, materia y prioridad.

---

#### Módulo 3: Directorio de Contactos
* **RF-14 (CRUD de Contactos):** El sistema debe permitir crear, consultar, modificar y eliminar contactos.
* **RF-15 (Información del Contacto):** Cada ficha de contacto incluirá:
  * Nombre completo.
  * Correo electrónico institucional y/o personal.
  * Número de teléfono.
  * Rol o categoría (*Profesor, Asesor/Tutor, Compañero de equipo, Personal*).
  * Materias en las que participa o se relaciona.
  * Notas u observaciones adicionales (ej. horario de asesorías).
* **RF-16 (Búsqueda Rápida):** Búsqueda en tiempo real por nombre, rol o materia vinculada.

---

### 4. Requisitos No Funcionales (RNF)

* **RNF-01 (Persistencia Offline / Local):** La aplicación debe almacenar todos los datos de forma local mediante una base de datos relacional ligera (ej. SQLite), garantizando funcionamiento pleno sin conexión a internet.
* **RNF-02 (Interfaz Adaptable y Responsiva):** La interfaz gráfica de usuario (GUI) debe adaptarse fluidamente a ventanas de escritorio (Linux, Windows, macOS) y pantallas móviles o tabletas.
* **RNF-03 (Rendimiento):** La carga del calendario y el listado de tareas/eventos debe responder en menos de 1 segundo para volúmenes estándar de datos (hasta 5,000 registros).
* **RNF-04 (Diseño Accesible y Cómodo):** El sistema debe incorporar paletas de color con buen contraste e incluir soporte para modo claro (*Light*) y modo oscuro (*Dark*).
* **RNF-05 (Integridad y Respaldo):** Capacidad para exportar e importar los datos en formato estándar (JSON o SQLite backup) para respaldos del usuario.

---

### 5. Historias de Usuario Principales (Ejemplos)

* **HU-01 (Horario de Clases Recurrente):**
  * *Como* estudiante,
  * *Quiero* programar mis clases para que se repitan automáticamente cada semana durante el semestre,
  * *Para* no tener que ingresar manualmente el horario de cada día.
  * *Criterios de Aceptación:* El usuario selecciona días de la semana (ej. lunes y miércoles), hora inicio/fin y fecha de término del semestre. El calendario muestra las instancias automáticamente.

* **HU-02 (Alerta de Entrega de Proyecto):**
  * *Como* usuario,
  * *Quiero* recibir una notificación 24 horas antes del vencimiento de una tarea de alta prioridad,
  * *Para* finalizar los preparativos con suficiente margen de tiempo.
  * *Criterios de Aceptación:* Al cumplirse el plazo de 24 horas previas, el sistema despliega una notificación visible/audible indicando el título de la tarea y la materia.

* **HU-03 (Consulta del Docente de una Asignatura):**
  * *Como* alumno,
  * *Quiero* acceder a los datos de contacto de mi profesor directamente desde la vista de la materia,
  * *Para* enviarle un correo sobre dudas de una tarea sin salir de la aplicación.
  * *Criterios de Aceptación:* Desde el detalle de la materia o evento de clase, un clic en el nombre del profesor abre sus datos de contacto o la acción de redacción de correo.
