# Sistema de Control de Velocidad de un Motor DC para Refrigeración de Racks de Servidores

Trabajo Final Integrador — Teoría de Control  
Tecnologías de Automatización — UTN FRBA

## Integrantes

- **Matías Rainhart**
- **Facundo Slaibe**

**Docente:** Dr. Omar Civale  
**Comisión:** K4521

---

## Descripción del proyecto

Este proyecto corresponde al Trabajo Final Integrador de la materia **Tecnologías de Automatización**, dentro del bloque temático de **Teoría de Control**.

El trabajo aborda el diseño y análisis de un **sistema de control de velocidad para un motor de corriente continua (DC)** utilizado en un ventilador de refrigeración de un rack de servidores.

El objetivo es modelar matemáticamente el comportamiento del motor, diseñar un controlador de velocidad y analizar las características de estabilidad y error del sistema mediante herramientas propias de la Teoría de Control.

El sistema planteado se encuentra dentro del contexto de la **infraestructura de Tecnologías de la Información (TI)** y la refrigeración automatizada de servidores.

---

## Objetivos

### Objetivo general

Diseñar y fundamentar un sistema de control de lazo cerrado que permita regular automáticamente la velocidad de un motor DC perteneciente a un ventilador de refrigeración, utilizando como referencia una consigna de velocidad relacionada con la temperatura del equipo.

### Objetivos específicos

- Identificar y describir la estructura completa del sistema de control.
- Identificar transductores, actuadores, señales y perturbaciones.
- Obtener el modelo matemático del motor DC a partir de sus ecuaciones diferenciales.
- Obtener la función de transferencia de la planta.
- Representar el sistema mediante un diagrama de bloques de lazo cerrado.
- Diseñar un controlador **Proporcional-Integral (PI)**.
- Analizar la estabilidad mediante el **criterio de Routh-Hurwitz**.
- Analizar el error en estado estacionario.
- Simular el comportamiento del sistema mediante un programa desarrollado en Python.

---

## Contexto del sistema

El sistema se encuentra aplicado a la refrigeración de un **rack de servidores**.

Los servidores generan calor durante su funcionamiento, por lo que resulta necesario mantener una temperatura adecuada para evitar problemas de funcionamiento y degradación del rendimiento.

Para esto se utilizan ventiladores cuya velocidad puede regularse mediante **PWM (Pulse Width Modulation)**.
