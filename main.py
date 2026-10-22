#!/usr/bin/env python3
"""Solucionador didáctico del cubo 2x2x2 mediante IDA* y tablas de patrones.

No necesita paquetes externos. La entrada manual se hace esquina por esquina:
para una posición URF se escriben, en orden, los colores de las pegatinas U, R y F.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random
import time
from typing import Iterable, Optional

# Las tres caras de cada esquina siguen una orientación cíclica coherente.
CORNER_FACES = (
    ("U", "R", "F"),  # URF
    ("U", "F", "L"),  # UFL
    ("U", "L", "B"),  # ULB
    ("U", "B", "R"),  # UBR
    ("D", "F", "R"),  # DFR
    ("D", "L", "F"),  # DLF
    ("D", "B", "L"),  # DBL
    ("D", "R", "B"),  # DRB
)
CORNER_NAMES = ("URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB")
FACE_VECTOR = {
    "U": (0, 1, 0), "D": (0, -1, 0),
    "R": (1, 0, 0), "L": (-1, 0, 0),
    "F": (0, 0, 1), "B": (0, 0, -1),
}
VECTOR_FACE = {v: k for k, v in FACE_VECTOR.items()}
CORNER_COORDS = tuple(tuple(sum(FACE_VECTOR[f][i] for f in faces) for i in range(3)) for faces in CORNER_FACES)
COORD_CORNER = {v: i for i, v in enumerate(CORNER_COORDS)}

# Esquema de colores estándar. Si tu cubo tiene otro esquema, cambia estas letras.
DEFAULT_COLOR_MAP = {"U": "W", "D": "Y", "F": "G", "B": "B", "R": "R", "L": "O"}
COLOR_NAMES = {"W": "blanco", "Y": "amarillo", "G": "verde", "B": "azul", "R": "rojo", "O": "naranja"}
FACE_ORDER = ("U", "R", "F", "D", "L", "B")

# Un estado cubie es (perm, ori): en cada posición, qué esquina está y cómo está girada.
SOLVED_PERM = tuple(range(8))
SOLVED_ORI = (0,) * 8
SOLVED_STICKERS = tuple(face for corner in CORNER_FACES for face in corner)
PIECE_BY_COLOR_SET = {frozenset(faces): i for i, faces in enumerate(CORNER_FACES)}


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _rotate_minus_90(v, axis):
    """Giro de -90 grados alrededor del eje exterior de la cara (horario visto desde fuera)."""
    cross = _cross(axis, v)
    projection = _dot(axis, v)
    return tuple(-cross[i] + axis[i] * projection for i in range(3))


def _build_sticker_permutation(face: str) -> tuple[int, ...]:
    axis = FACE_VECTOR[face]
    result = [None] * 24  # source sticker index -> destination sticker index
    for pos, faces in enumerate(CORNER_FACES):
        coord = CORNER_COORDS[pos]
        for slot, sticker_face in enumerate(faces):
            source = pos * 3 + slot
            normal = FACE_VECTOR[sticker_face]
            if _dot(coord, axis) == 1:
                new_coord = _rotate_minus_90(coord, axis)
                new_normal = _rotate_minus_90(normal, axis)
            else:
                new_coord, new_normal = coord, normal
            dest_pos = COORD_CORNER[new_coord]
            dest_face = VECTOR_FACE[new_normal]
            dest_slot = CORNER_FACES[dest_pos].index(dest_face)
            result[source] = dest_pos * 3 + dest_slot
    if sorted(result) != list(range(24)):
        raise RuntimeError(f"Permutación de pegatinas no válida para {face}")
    return tuple(result)


def apply_sticker_move(state: tuple[str, ...], sticker_perm: tuple[int, ...]) -> tuple[str, ...]:
    new_state = [None] * 24
    for src, dst in enumerate(sticker_perm):
        new_state[dst] = state[src]
    return tuple(new_state)


def decode_stickers(stickers: tuple[str, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Convierte las 24 pegatinas en permutación y orientación de las 8 esquinas."""
    if len(stickers) != 24:
        raise ValueError("Se necesitan exactamente 24 pegatinas.")
    perm, ori = [], []
    seen = set()
    for pos in range(8):
        observed = tuple(stickers[pos * 3:pos * 3 + 3])
        if len(set(observed)) != 3:
            raise ValueError(f"La esquina {CORNER_NAMES[pos]} tiene colores repetidos: {observed}")
        piece = PIECE_BY_COLOR_SET.get(frozenset(observed))
        if piece is None:
            raise ValueError(f"La combinación de colores {observed} no corresponde a una esquina del cubo.")
        if piece in seen:
            raise ValueError(f"La esquina {''.join(CORNER_FACES[piece])} aparece más de una vez.")
        seen.add(piece)
        canonical = CORNER_FACES[piece]
        if observed == canonical:
            orientation = 0
        elif observed == (canonical[1], canonical[2], canonical[0]):
            orientation = 1
        elif observed == (canonical[2], canonical[0], canonical[1]):
            orientation = 2
        else:
            # La misma terna con orden inverso no es una orientación físicamente posible.
            raise ValueError(f"Orientación imposible en {CORNER_NAMES[pos]}: {observed}.")
        perm.append(piece)
        ori.append(orientation)
    if len(seen) != 8:
        raise ValueError("No aparecen las ocho esquinas exactamente una vez.")
    if sum(ori) % 3 != 0:
        raise ValueError("Estado físicamente imposible: la suma de giros de esquina no es múltiplo de 3.")
    return tuple(perm), tuple(ori)


def encode_stickers(perm: tuple[int, ...], ori: tuple[int, ...]) -> tuple[str, ...]:
    stickers = []
    for pos in range(8):
        canonical = CORNER_FACES[perm[pos]]
        shift = ori[pos] % 3
        stickers.extend(canonical[(i + shift) % 3] for i in range(3))
    return tuple(stickers)


@dataclass(frozen=True)
class Move:
    name: str
    face: str
    # Para cada posición de destino, la posición de origen de su esquina.
    source_for_dest: tuple[int, ...]
    # Giro adicional de la esquina que termina en cada posición de destino.
    delta_for_dest: tuple[int, ...]


def _build_move_definitions():
    quarter_sticker = {f: _build_sticker_permutation(f) for f in FACE_ORDER}
    moves = []
    for face in FACE_ORDER:
        stickers = SOLVED_STICKERS
        perm_q = quarter_sticker[face]
        stickers_q = apply_sticker_move(stickers, perm_q)
        p_q, o_q = decode_stickers(stickers_q)
        # Al aplicar el movimiento a resuelto, p_q[dest] dice qué pieza venía del origen.
        source_for_dest = p_q
        delta_q = o_q
        # Componemos sticker permutations para construir dos giros y un giro inverso.
        for power, suffix in ((1, ""), (2, "2"), (3, "'")):
            p = tuple(range(24))  # source -> destination
            for _ in range(power):
                p = tuple(perm_q[p[src]] for src in range(24))
            # Aplicar a resuelto y decodificar evita confundir el signo de la orientación.
            state = [None] * 24
            for src, dst in enumerate(p):
                state[dst] = SOLVED_STICKERS[src]
            p_corner, o_corner = decode_stickers(tuple(state))
            moves.append(Move(face + suffix, face, p_corner, o_corner))
    return tuple(moves)


MOVES = _build_move_definitions()
MOVE_BY_NAME = {move.name: move for move in MOVES}


def apply_move(state: tuple[tuple[int, ...], tuple[int, ...]], move: Move):
    perm, ori = state
    new_perm = tuple(perm[src] for src in move.source_for_dest)
    new_ori = tuple((ori[src] + move.delta_for_dest[dest]) % 3
                    for dest, src in enumerate(move.source_for_dest))
    return new_perm, new_ori


def apply_moves(state, moves: Iterable[Move]):
    for move in moves:
        state = apply_move(state, move)
    return state


def permutation_rank(perm: tuple[int, ...]) -> int:
    """Rango de Lehmer: codifica una permutación de 8 elementos en [0, 8!-1]."""
    rank = 0
    n = len(perm)
    for i in range(n):
        smaller = sum(1 for j in range(i + 1, n) if perm[j] < perm[i])
        rank = rank * (n - i) + smaller
    return rank


def permutation_unrank(rank: int) -> tuple[int, ...]:
    if not 0 <= rank < 40320:
        raise ValueError("Rango de permutación fuera de límites.")
    available = list(range(8))
    result = []
    for i in range(8):
        factor = 1
        for x in range(1, 8 - i):
            factor *= x
        index, rank = divmod(rank, factor) if factor else (0, 0)
        result.append(available.pop(index))
    return tuple(result)


def twist_encode(ori: tuple[int, ...]) -> int:
    """Codifica los 7 primeros giros; el octavo queda determinado por la suma módulo 3."""
    code = 0
    for value in ori[:7]:
        code = code * 3 + value
    return code


def twist_decode(code: int) -> tuple[int, ...]:
    if not 0 <= code < 2187:
        raise ValueError("Rango de orientación fuera de límites.")
    first = [0] * 7
    for i in range(6, -1, -1):
        code, first[i] = divmod(code, 3)
    last = (-sum(first)) % 3
    return tuple(first + [last])


def _build_pattern_databases():
    """Distancias exactas en dos proyecciones: solo permutación y solo orientación."""
    perm_dist = bytearray([255]) * 40320
    solved_rank = permutation_rank(SOLVED_PERM)
    perm_dist[solved_rank] = 0
    queue = deque([SOLVED_PERM])
    while queue:
        perm = queue.popleft()
        d = perm_dist[permutation_rank(perm)]
        for move in MOVES:
            nxt = tuple(perm[src] for src in move.source_for_dest)
            rank = permutation_rank(nxt)
            if perm_dist[rank] == 255:
                perm_dist[rank] = d + 1
                queue.append(nxt)

    twist_dist = bytearray([255]) * 2187
    twist_dist[0] = 0
    queue_twist = deque([SOLVED_ORI])
    while queue_twist:
        ori = queue_twist.popleft()
        code = twist_encode(ori)
        d = twist_dist[code]
        for move in MOVES:
            nxt = tuple((ori[src] + move.delta_for_dest[dest]) % 3
                        for dest, src in enumerate(move.source_for_dest))
            nxt_code = twist_encode(nxt)
            if twist_dist[nxt_code] == 255:
                twist_dist[nxt_code] = d + 1
                queue_twist.append(nxt)
    if 255 in perm_dist or 255 in twist_dist:
        raise RuntimeError("No se han alcanzado todos los estados de las tablas de patrones.")
    return bytes(perm_dist), bytes(twist_dist)


class PocketCubeSolver:
    def __init__(self):
        start = time.perf_counter()
        self.perm_dist, self.twist_dist = _build_pattern_databases()
        self.table_time = time.perf_counter() - start
        self.nodes = 0
        self.path: list[Move] = []
        self.max_depth = 20

    def heuristic(self, perm, ori):
        return max(self.perm_dist[permutation_rank(perm)], self.twist_dist[twist_encode(ori)])

    @staticmethod
    def _opposite(face: str) -> str:
        return {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}[face]

    def _search(self, perm, ori, depth, bound, previous_face, path, seen):
        self.nodes += 1
        h = self.heuristic(perm, ori)
        score = depth + h
        if score > bound:
            return score
        if perm == SOLVED_PERM and ori == SOLVED_ORI:
            self.path = path.copy()
            return True

        state_key = (perm, ori, previous_face)
        old_depth = seen.get(state_key)
        if old_depth is not None and old_depth <= depth:
            return float("inf")
        seen[state_key] = depth

        minimum = float("inf")
        for move in MOVES:
            if previous_face == move.face:
                continue
            # Las caras opuestas conmutan. Conservamos un solo orden para evitar duplicados.
            if previous_face and self._opposite(previous_face) == move.face:
                if FACE_ORDER.index(previous_face) > FACE_ORDER.index(move.face):
                    continue
            next_state = apply_move((perm, ori), move)
            path.append(move)
            result = self._search(next_state[0], next_state[1], depth + 1, bound, move.face, path, seen)
            if result is True:
                return True
            path.pop()
            if result < minimum:
                minimum = result
        return minimum

    def solve(self, state, max_depth: int = 20):
        perm, ori = state
        if sum(ori) % 3:
            raise ValueError("Estado inválido: la suma de orientaciones debe ser 0 módulo 3.")
        if sorted(perm) != list(range(8)):
            raise ValueError("Estado inválido: cada una de las 8 esquinas debe aparecer una sola vez.")
        self.nodes = 0
        self.path = []
        bound = self.heuristic(perm, ori)
        started = time.perf_counter()
        while bound <= max_depth:
            seen = {}
            result = self._search(perm, ori, 0, bound, None, [], seen)
            if result is True:
                return [m.name for m in self.path], self.nodes, time.perf_counter() - started
            if result == float("inf"):
                break
            bound = int(result)
        raise RuntimeError(f"No se encontró solución hasta profundidad {max_depth}. Prueba un límite mayor.")


def parse_moves(text: str) -> list[Move]:
    tokens = text.replace(",", " ").split()
    moves = []
    for token in tokens:
        normalized = token.strip()
        if normalized not in MOVE_BY_NAME:
            raise ValueError(f"Movimiento '{normalized}' no válido. Usa U, R, F, D, L, B y sufijos 2 o '.")
        moves.append(MOVE_BY_NAME[normalized])
    return moves


def random_scramble(length: int = 9, rng=None) -> list[Move]:
    rng = rng or random
    result = []
    last_face = None
    for _ in range(length):
        choices = [m for m in MOVES if m.face != last_face]
        move = rng.choice(choices)
        result.append(move)
        last_face = move.face
    return result


def color_to_face_map(color_map: dict[str, str]):
    if set(color_map) != set(FACE_ORDER):
        raise ValueError("El mapa debe definir los seis lados: U, R, F, D, L y B.")
    colors = list(color_map.values())
    if len(set(colors)) != 6:
        raise ValueError("Cada cara debe usar un color distinto.")
    return {color.upper(): face for face, color in color_map.items()}


def read_manual_state(color_map=DEFAULT_COLOR_MAP):
    """Pide las tres pegatinas de cada esquina, en el orden escrito en su nombre."""
    inverse = color_to_face_map(color_map)
    print("\nINTRODUCCIÓN MANUAL DEL CUBO")
    print("Para URF, introduce las pegatinas de las caras U, R y F, en ese orden; escribe sus colores, no las letras de cara.")
    print("Mapa de colores: " + " | ".join(f"{f}={color_map[f]} ({COLOR_NAMES.get(color_map[f], 'color')})" for f in FACE_ORDER))
    print("Introduce tres letras separadas o juntas, usando W/Y/G/B/R/O. Ejemplo en URF: W R G (blanco, rojo, verde).")
    stickers = []
    for name, face_tuple in zip(CORNER_NAMES, CORNER_FACES):
        while True:
            raw = input(f"{name} ({', '.join(face_tuple)}): ").strip().upper().replace(",", " ")
            tokens = raw.split() if " " in raw else list(raw)
            if len(tokens) != 3:
                print("  Error: introduce exactamente tres letras de color.")
                continue
            try:
                stickers.extend(inverse[token] for token in tokens)
                break
            except KeyError:
                print("  Error: colores permitidos: " + ", ".join(sorted(inverse)))
    return decode_stickers(tuple(stickers))


def show_cube_summary(state):
    perm, ori = state
    print("\nEstado leído por el programa (posición: pieza / giro):")
    for pos, piece, twist in zip(CORNER_NAMES, perm, ori):
        print(f"  {pos}: {CORNER_NAMES[piece]} / orientación {twist}")


def verify_solution(start_state, solution_names):
    end_state = apply_moves(start_state, [MOVE_BY_NAME[n] for n in solution_names])
    return end_state == (SOLVED_PERM, SOLVED_ORI)


def print_quick_reference():
    print("\nNotación de movimientos:")
    print("  U R F D L B  = giro horario de esa cara, visto de frente a dicha cara")
    print("  '            = giro antihorario (por ejemplo R')")
    print("  2            = media vuelta (por ejemplo U2)")
    print("Ejemplo de secuencia: R U R' U'\n")


def main():
    print("=" * 61)
    print("  POCKET CUBE 2x2x2 - SOLUCIONADOR POR BÚSQUEDA IDA*")
    print("=" * 61)
    print("Construye tablas de patrones pequeñas para orientar la búsqueda...")
    try:
        solver = PocketCubeSolver()
    except Exception as exc:
        print(f"No se pudo inicializar el solucionador: {exc}")
        return
    print(f"Tablas preparadas en {solver.table_time:.2f} s.\n")

    while True:
        print("Menú:")
        print("  1) Generar un scramble de práctica y resolverlo")
        print("  2) Introducir una secuencia de movimientos ya aplicada al cubo")
        print("  3) Introducir manualmente los colores de las 8 esquinas")
        print("  4) Ver la notación de movimientos")
        print("  0) Salir")
        option = input("Elige una opción: ").strip()
        if option == "0":
            print("Hasta luego. Antes de la prueba, practica explicando la heurística y la búsqueda.")
            return
        if option == "4":
            print_quick_reference()
            continue
        try:
            if option == "1":
                length_raw = input("Longitud del scramble [9]: ").strip()
                length = int(length_raw) if length_raw else 9
                if not 1 <= length <= 20:
                    raise ValueError("La longitud debe estar entre 1 y 20.")
                scramble = random_scramble(length)
                state = apply_moves((SOLVED_PERM, SOLVED_ORI), scramble)
                print("\nSCRAMBLE (aplica estos movimientos al cubo resuelto):")
                print(" ".join(m.name for m in scramble))
            elif option == "2":
                print("Escribe los movimientos que has aplicado, separados por espacios.")
                print("Ejemplo: R U R' F2 D L'\n")
                scramble = parse_moves(input("Scramble: "))
                state = apply_moves((SOLVED_PERM, SOLVED_ORI), scramble)
            elif option == "3":
                state = read_manual_state()
                scramble = None
            else:
                print("Opción no reconocida.\n")
                continue

            show_cube_summary(state)
            print("\nBuscando solución...")
            try:
                solution, nodes, seconds = solver.solve(state)
            except RuntimeError as exc:
                print(f"No se encontró solución: {exc}")
                continue
            print("\nSOLUCIÓN:")
            print(" ".join(solution) if solution else "(el cubo ya está resuelto)")
            print(f"Movimientos de la solución: {len(solution)}")
            print(f"Nodos explorados: {nodes:,}")
            print(f"Tiempo de búsqueda: {seconds:.3f} s")
            print("Verificación interna:", "CORRECTA" if verify_solution(state, solution) else "FALLIDA")
            if option == "1":
                print("\nPrueba práctica: aplica primero el SCRAMBLE y después la SOLUCIÓN al cubo físico.")
            print()
        except (ValueError, KeyError) as exc:
            print(f"Entrada no válida: {exc}\n")
        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario.")
            return


if __name__ == "__main__":
    main()
