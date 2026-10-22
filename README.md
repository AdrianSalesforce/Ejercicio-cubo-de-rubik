# Pocket Cube 2×2×2 — solucionador individual

Prototipo didáctico en Python para resolver un cubo de Rubik 2×2×2 mediante búsqueda informada **IDA\*** (Iterative Deepening A*) y dos tablas de patrones. No usa paquetes externos.

## tutorial.pdf


He anadido un tutorial.pdf donde se explica en mayor detalle el funcionamiento del mismo, pero que es para yo poder enterarme bien de como funciona correctamente

## Pocket Cube IDA_.ppt y Guion Presentacion Pocket Cube Adrian Herrera Fernandez.pdf

Pequeña presentación para la clase del 22/10/26

Guión de apoyo para la exposición de clase

## Requisitos

- Python 3.10 o superior.
- No hace falta instalar dependencias.

## Ejecutarlo en Windows

1. Descomprime la carpeta.
2. Abre una terminal dentro de la carpeta.
3. Ejecuta `python main.py` (o abre `run_windows.bat`).
4. El programa construye las tablas pequeñas al arrancar y muestra un menú.

En Linux/macOS también sirve `python3 main.py`.

## Opciones

1. **Scramble de práctica**: genera una secuencia aleatoria, imprime el scramble y después busca una solución. Aplica ambas secuencias, en ese orden, al cubo físico.
2. **Secuencia conocida**: introduce los movimientos que ya has aplicado a un cubo inicialmente resuelto.
3. **Colores de las esquinas**: lee manualmente las tres pegatinas de cada posición. Se introducen en el orden del nombre de la posición: para `URF`, pegatinas de las caras `U`, `R`, `F`. Por defecto, el mapa es U=blanco (W), D=amarillo (Y), F=verde (G), B=azul (B), R=rojo (R), L=naranja (O). Si el cubo tiene otro esquema, ajusta `DEFAULT_COLOR_MAP` en `main.py`.
4. **Notación**: recuerda los movimientos admitidos.

## Notación

- `U R F D L B`: giro horario de esa cara visto desde fuera.
- `R'`: giro antihorario de la cara R.
- `U2`: media vuelta de la cara U.
- Los movimientos se separan por espacios.

## Algoritmo

La búsqueda es IDA*: aumenta progresivamente un límite `f = g + h`, donde `g` es el número de movimientos usados y `h` una heurística admisible. `h` es el máximo de dos distancias exactas precomputadas por BFS: una proyección solo de permutaciones de esquinas (8! combinaciones) y otra solo de orientaciones (3^7 combinaciones legales). Tomar el máximo mantiene la cota inferior admisible.

El solucionador evita repetir inmediatamente la misma cara y canoniza el orden de movimientos de caras opuestas, ya que esas caras no comparten esquinas y sus giros conmutan. La clave de transposición incluye estado y cara anterior para no eliminar rutas que tengan distintas restricciones de continuación.

## Pruebas

```bash
python -m unittest -v
```

Las pruebas comprueban transformaciones de movimiento, ida/vuelta de representación, ranking de permutaciones, rechazo de una orientación imposible y resolución de scrambles de distintos tamaños.

## Archivos

- `main.py`: modelo, movimientos, validación, tablas de patrones, IDA* e interfaz de terminal.
- `tests.py`: pruebas automatizadas con `unittest`.
- `tutorial.pdf`: explicación paso a paso y guía para defenderlo oralmente.
- `requirements.txt`: no hay dependencias externas.
