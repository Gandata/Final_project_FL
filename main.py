"""Implementacion de Conjuntos FIRST/FOLLOW, Parsers LL(1) y SLR(1), y Evaluador SDD.

Basado estrictamente en:
- Aho, Lam, Sethi & Ullman, "Compilers: Principles, Techniques, and Tools" (2da Ed.),
  Capitulos 4 (Secciones 4.4, 4.5, 4.6) y 5 (Secciones 5.1, 5.2).
- Especificacion oficial del proyecto (docs/sdt_revised.pdf).

Restriccion cumplida: Utiliza unicamente la libreria estandar de Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import sys
from typing import Any, Callable


# Constantes de simbolos especiales segun la Seccion 2.2 de sdt_revised.pdf
EPSILON = "e"
ENDMARKER = "$"
INITIAL_SYMBOL = "S"
AUGMENTED_START = "S'"


# =============================================================================
# ESTRUCTURAS DE DATOS PARA LA GRAMATICA (Seccion 4.2 y Seccion 2.2)
# =============================================================================


@dataclass
class Grammar:
    """Representa una gramatica libre de contexto G = (N, T, P, S)."""

    nonterminals: list[str]
    terminals: set[str]
    productions: dict[str, list[str]]
    production_list: list[tuple[str, str]]
    start_symbol: str = INITIAL_SYMBOL


def is_nonterminal(symbol: str) -> bool:
    """Verifica si un simbolo es no terminal (letra mayuscula o S')."""
    return symbol == AUGMENTED_START or (len(symbol) == 1 and symbol.isupper())


def is_terminal(symbol: str) -> bool:
    """Verifica si un simbolo es terminal segun la Seccion 2.2."""
    return (
        len(symbol) == 1
        and not symbol.isupper()
        and symbol != EPSILON
        and symbol != ENDMARKER
        and not symbol.isspace()
    )


def parse_grammar_lines(lines: list[str]) -> Grammar:
    """Construye el objeto Grammar a partir de las n lineas de producciones (Seccion 2.2.1)."""
    nonterminals: list[str] = []
    terminals: set[str] = set()
    productions: dict[str, list[str]] = {}
    production_list: list[tuple[str, str]] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        head_part, body_part = line.split("->")
        head = head_part.strip()
        alternatives = body_part.strip().split()

        if head not in productions:
            nonterminals.append(head)
            productions[head] = []

        for alt in alternatives:
            productions[head].append(alt)
            production_list.append((head, alt))
            if alt != EPSILON:
                for ch in alt:
                    if not is_nonterminal(ch):
                        terminals.add(ch)

    return Grammar(
        nonterminals=nonterminals,
        terminals=terminals,
        productions=productions,
        production_list=production_list,
        start_symbol=INITIAL_SYMBOL,
    )


def read_grammar_from_stdin() -> Grammar | None:
    """Lee un entero n > 0 y luego n lineas de producciones desde la entrada estandar."""
    first_line = sys.stdin.readline()
    if not first_line:
        return None
    n = int(first_line.strip())
    lines: list[str] = []
    for _ in range(n):
        line = sys.stdin.readline()
        lines.append(line)
    return parse_grammar_lines(lines)


# =============================================================================
# ITEM 1: CONJUNTOS FIRST Y FOLLOW (Seccion 4.4.2, pags. 220-222 de Aho)
# =============================================================================


def compute_first_sets(grammar: Grammar) -> dict[str, set[str]]:
    """Calcula FIRST(X) para todo simbolo gramatical X (Seccion 4.4.2, pag. 221).

    Reglas del libro:
    1. Si X es terminal, FIRST(X) = {X}.
    2. Si X -> Y1 Y2 ... Yk, agregar a FIRST(X) todo a != e en FIRST(Yi) si
       FIRST(Y1), ..., FIRST(Yi-1) contienen todos a e. Si todo Yj tiene e
       en FIRST(Yj), agregar e a FIRST(X).
    3. Si X -> e es produccion, agregar e a FIRST(X).
    """
    first: dict[str, set[str]] = {}

    # Regla 1: Para todo terminal X, FIRST(X) = {X}
    for t in grammar.terminals:
        first[t] = {t}

    # Inicializar conjuntos vacios para los no terminales
    for nt in grammar.nonterminals:
        first[nt] = set()

    # Bucle de punto fijo hasta que no se puedan agregar mas simbolos
    changed = True
    while changed:
        changed = False
        for head, body in grammar.production_list:
            before_size = len(first[head])

            # Regla 3: Si X -> e es una produccion, agregar e a FIRST(X)
            if body == EPSILON:
                first[head].add(EPSILON)
            else:
                # Regla 2: X -> Y1 Y2 ... Yk
                all_nullable = True
                for symbol in body:
                    sym_first = first.get(symbol, {symbol})
                    for tok in sym_first:
                        if tok != EPSILON:
                            first[head].add(tok)
                    if EPSILON not in sym_first:
                        all_nullable = False
                        break
                if all_nullable:
                    first[head].add(EPSILON)

            if len(first[head]) > before_size:
                changed = True

    return first


def compute_first_of_string(alpha: str, first_sets: dict[str, set[str]]) -> set[str]:
    """Calcula FIRST(X1 X2 ... Xn) para una cadena alfa (Seccion 4.4.2, pag. 221)."""
    if not alpha or alpha == EPSILON:
        return {EPSILON}

    result: set[str] = set()
    all_nullable = True

    for symbol in alpha:
        sym_first = first_sets.get(symbol, {symbol})
        for tok in sym_first:
            if tok != EPSILON:
                result.add(tok)
        if EPSILON not in sym_first:
            all_nullable = False
            break

    if all_nullable:
        result.add(EPSILON)

    return result


def compute_follow_sets(
    grammar: Grammar, first_sets: dict[str, set[str]]
) -> dict[str, set[str]]:
    """Calcula FOLLOW(A) para todos los no terminales A (Seccion 4.4.2, pags. 221-222).

    Reglas del libro:
    1. Colocar $ en FOLLOW(S), donde S es el simbolo inicial.
    2. Si hay una produccion A -> alfa B beta, todo en FIRST(beta) excepto e
       se agrega a FOLLOW(B).
    3. Si hay una produccion A -> alfa B, o A -> alfa B beta donde FIRST(beta)
       contiene a e, todo en FOLLOW(A) se agrega a FOLLOW(B).
    """
    follow: dict[str, set[str]] = {nt: set() for nt in grammar.nonterminals}

    # Regla 1: Colocar $ en FOLLOW(S)
    if grammar.start_symbol in follow:
        follow[grammar.start_symbol].add(ENDMARKER)

    # Bucle de punto fijo hasta que ningun FOLLOW cambie
    changed = True
    while changed:
        changed = False
        for head, body in grammar.production_list:
            if body == EPSILON:
                continue
            length = len(body)
            for i, symbol in enumerate(body):
                if symbol not in follow:
                    continue
                before_size = len(follow[symbol])
                beta = body[i + 1 :] if i + 1 < length else ""

                if beta:
                    # Regla 2: Todo en FIRST(beta) - {e} entra en FOLLOW(B)
                    first_beta = compute_first_of_string(beta, first_sets)
                    for tok in first_beta:
                        if tok != EPSILON:
                            follow[symbol].add(tok)
                    # Regla 3 (con beta anulable): FOLLOW(A) entra en FOLLOW(B)
                    if EPSILON in first_beta:
                        follow[symbol].update(follow[head])
                else:
                    # Regla 3 (B al final del cuerpo): FOLLOW(A) entra en FOLLOW(B)
                    follow[symbol].update(follow[head])

                if len(follow[symbol]) > before_size:
                    changed = True

    return follow


def format_symbol_set(symbols: set[str]) -> str:
    """Formatea un conjunto ordenando terminales en ASCII, luego 'e' y al final '$' (Seccion 2.1)."""
    regular_terminals = sorted(
        s for s in symbols if s != EPSILON and s != ENDMARKER
    )
    ordered: list[str] = list(regular_terminals)
    if EPSILON in symbols:
        ordered.append(EPSILON)
    if ENDMARKER in symbols:
        ordered.append(ENDMARKER)
    return "{" + ", ".join(ordered) + "}"


def print_first_and_follow_sets(
    grammar: Grammar,
    first_sets: dict[str, set[str]],
    follow_sets: dict[str, set[str]],
) -> None:
    """Imprime los conjuntos First(A) y Follow(A) en orden alfabetico de no terminales (Seccion 2.1)."""
    sorted_nts = sorted(grammar.nonterminals)
    for nt in sorted_nts:
        print(f"First({nt}) = {format_symbol_set(first_sets[nt])}")
    for nt in sorted_nts:
        print(f"Follow({nt}) = {format_symbol_set(follow_sets[nt])}")


# =============================================================================
# ARBOL DE ANALISIS SINTACTICO (PARSE TREE) (Seccion 4.2.4 y Seccion 5.1.2)
# =============================================================================


@dataclass
class ParseNode:
    """Nodo del arbol de analisis sintactico para evaluar la SDD (Seccion 3, Paso 5.2)."""

    symbol: str
    production: tuple[str, str] | None = None
    children: list[ParseNode] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    node_id: int = 0


# =============================================================================
# ITEM 2 (PARTE A): PARSER PREDICTIVO LL(1) (Secciones 4.4.3 y 4.4.4)
# =============================================================================

LL1Table = dict[tuple[str, str], list[tuple[str, str]]]


def find_ll1_conflicts(
    grammar: Grammar,
    first_sets: dict[str, set[str]],
    follow_sets: dict[str, set[str]],
) -> list[str]:
    """Verifica la condicion de gramatica LL(1) de la Seccion 4.4.3 (pags. 223-224).

    Una gramatica es LL(1) si y solo si, para cada par de producciones distintas
    A -> alfa | beta, se cumple:
    1. alfa y beta no derivan cadenas que empiecen con el mismo terminal.
    2. A lo sumo una de las dos (alfa o beta) deriva e.
    3. Si beta deriva e, alfa no deriva cadenas que empiecen con un terminal de
       FOLLOW(A); y lo mismo intercambiando alfa y beta.
    El libro las reescribe con conjuntos (pag. 224), que es lo que se revisa aqui:
    - Condiciones 1 y 2: FIRST(alfa) y FIRST(beta) son disjuntos.
    - Condicion 3: si e esta en FIRST(beta), FIRST(alfa) y FOLLOW(A) son
      disjuntos; y lo mismo si e esta en FIRST(alfa).

    Retorna la lista de condiciones violadas (vacia si la gramatica es LL(1)).
    """
    conflicts: list[str] = []
    for nt in grammar.nonterminals:
        # Una alternativa repetida es la misma produccion, por eso se quitan duplicados
        bodies = list(dict.fromkeys(grammar.productions[nt]))
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                alpha, beta = bodies[i], bodies[j]
                first_alpha = compute_first_of_string(alpha, first_sets)
                first_beta = compute_first_of_string(beta, first_sets)
                follow_a = follow_sets[nt]
                pair = f"{nt} -> {alpha} | {beta}"

                # Condiciones 1 y 2: FIRST(alfa) y FIRST(beta) deben ser disjuntos
                common = first_alpha & first_beta
                if common:
                    conflicts.append(
                        f"{pair}: FIRST de ambas comparte {format_symbol_set(common)}"
                    )
                # Condicion 3: si beta deriva e, FIRST(alfa) y FOLLOW(A) deben ser disjuntos
                if EPSILON in first_beta and first_alpha & follow_a:
                    conflicts.append(
                        f"{pair}: {beta} deriva e y FIRST({alpha}) comparte "
                        f"{format_symbol_set(first_alpha & follow_a)} con FOLLOW({nt})"
                    )
                # Condicion 3 intercambiando alfa y beta
                if EPSILON in first_alpha and first_beta & follow_a:
                    conflicts.append(
                        f"{pair}: {alpha} deriva e y FIRST({beta}) comparte "
                        f"{format_symbol_set(first_beta & follow_a)} con FOLLOW({nt})"
                    )
    return conflicts


def build_ll1_table(
    grammar: Grammar,
    first_sets: dict[str, set[str]],
    follow_sets: dict[str, set[str]],
) -> tuple[LL1Table, bool]:
    """Algoritmo 4.31: Construccion de una tabla de analisis sintactico predictivo (pag. 224).

    Tambien decide si la gramatica es LL(1) con la condicion de la Seccion 4.4.3
    (ver find_ll1_conflicts). Si la condicion se cumple, ninguna entrada M[A, a]
    queda con mas de una produccion.
    """
    table: LL1Table = {}
    input_symbols = set(grammar.terminals) | {ENDMARKER}
    for nt in grammar.nonterminals:
        for sym in input_symbols:
            table[(nt, sym)] = []

    for head, body in grammar.production_list:
        first_alpha = compute_first_of_string(body, first_sets)

        # Paso 1 del Algoritmo 4.31: Para cada terminal a en FIRST(alfa), agregar A -> alfa a M[A, a]
        for a in first_alpha:
            if a != EPSILON:
                cell = table[(head, a)]
                if (head, body) not in cell:
                    cell.append((head, body))

        # Paso 2 del Algoritmo 4.31: Si e esta en FIRST(alfa), para cada b en FOLLOW(A)
        # (incluyendo $), agregar A -> alfa a M[A, b]
        if EPSILON in first_alpha:
            for b in follow_sets[head]:
                cell = table[(head, b)]
                if (head, body) not in cell:
                    cell.append((head, body))

    # Condicion LL(1) (Seccion 4.4.3): la gramatica es LL(1) si no viola ninguna condicion
    is_ll1 = not find_ll1_conflicts(grammar, first_sets, follow_sets)
    return table, is_ll1


def contains_only_terminals(w: str, terminals: set[str]) -> bool:
    """Verifica que todos los caracteres de la cadena w sean terminales de la gramatica.

    Una cadena del lenguaje solo tiene terminales (Seccion 2.2): un no terminal
    como 'S', o el marcador '$' (que lo agrega el programa), nunca pueden estar
    en ella. Sin esta verificacion, el parser LL(1) emparejaria la letra 'S' de la
    entrada con el no terminal S del tope de la pila, y el parser SLR(1) aceptaria
    antes de tiempo al encontrar un '$' en medio de la cadena.
    """
    return all(ch in terminals for ch in w)


def parse_ll1(
    input_string: str,
    grammar: Grammar,
    table: LL1Table,
) -> tuple[bool, ParseNode | None, list[dict[str, str]]]:
    """Algoritmo 4.34 (Fig. 4.20): Analisis sintactico predictivo no recursivo (pags. 226-227).

    Retorna (aceptada, raiz_del_arbol, traza_de_pasos).
    """
    # Preparar buffer de entrada w$: si la linea es 'e', la cadena es vacia y w$ = "$"
    w = "" if input_string == EPSILON else input_string
    buffer = w + ENDMARKER
    ip = 0

    # Una cadena con simbolos que no son terminales no pertenece al lenguaje
    if not contains_only_terminals(w, grammar.terminals):
        start_stack = grammar.start_symbol + ENDMARKER
        return False, None, [{"stack": start_stack, "input": buffer, "action": "error"}]

    # Pila explicita con $ en el fondo y el simbolo inicial S en el tope
    root = ParseNode(symbol=grammar.start_symbol)
    end_node = ParseNode(symbol=ENDMARKER)
    stack: list[ParseNode] = [end_node, root]
    trace: list[dict[str, str]] = []

    while True:
        top_node = stack[-1]
        X = top_node.symbol
        a = buffer[ip] if ip < len(buffer) else ""

        stack_str = "".join(node.symbol for node in reversed(stack))
        rem_input = buffer[ip:]

        # Condicion de parada del bucle while (X != $) en Fig. 4.20
        if X == ENDMARKER:
            if a == ENDMARKER and ip == len(buffer) - 1:
                trace.append(
                    {"stack": stack_str, "input": rem_input, "action": "accept"}
                )
                return True, root, trace
            trace.append(
                {"stack": stack_str, "input": rem_input, "action": "error"}
            )
            return False, None, trace

        if X == a:
            # Coincidencia de terminal X con el simbolo de entrada a
            trace.append(
                {
                    "stack": stack_str,
                    "input": rem_input,
                    "action": f"match {a}",
                }
            )
            top_node.attributes["lexval"] = a
            stack.pop()
            ip += 1
        elif not is_nonterminal(X):
            # Error: X es un terminal distinto de a
            trace.append(
                {"stack": stack_str, "input": rem_input, "action": "error"}
            )
            return False, None, trace
        else:
            # X es no terminal: consultar entrada M[X, a] en la tabla predictiva
            entries = table.get((X, a), [])
            if not entries:
                trace.append(
                    {"stack": stack_str, "input": rem_input, "action": "error"}
                )
                return False, None, trace

            head, body = entries[0]
            trace.append(
                {
                    "stack": stack_str,
                    "input": rem_input,
                    "action": f"output {head} -> {body}",
                }
            )
            stack.pop()
            top_node.production = (head, body)

            if body == EPSILON:
                eps_child = ParseNode(symbol=EPSILON)
                top_node.children.append(eps_child)
            else:
                # Crear hijos Y1, Y2, ..., Yk y apilar Yk, ..., Y1 con Y1 en el tope
                children = [ParseNode(symbol=sym) for sym in body]
                top_node.children.extend(children)
                for child in reversed(children):
                    stack.append(child)


# =============================================================================
# ITEM 2 (PARTE B): PARSER SLR(1) (Secciones 4.6.2, 4.6.3 y 4.6.4)
# =============================================================================

# Un item LR(0) se representa como (cabeza, cuerpo_original, posicion_del_punto).
# Para una produccion A -> e, el cuerpo efectivo es "" de longitud 0 y dot_pos = 0 (pag. 242).
LR0Item = tuple[str, str, int]


def effective_body(body: str) -> str:
    """Retorna la secuencia de simbolos del cuerpo (vacia si el cuerpo es 'e')."""
    return "" if body == EPSILON else body


def closure(items: set[LR0Item], augmented_productions: list[tuple[str, str]]) -> frozenset[LR0Item]:
    """Calcula CLOSURE(I) para un conjunto de items LR(0) (Seccion 4.6.2, Fig. 4.32, pag. 245)."""
    j_set: set[LR0Item] = set(items)
    changed = True
    while changed:
        changed = False
        new_items: set[LR0Item] = set()
        for head, body, dot in j_set:
            eff = effective_body(body)
            if dot < len(eff):
                B = eff[dot]
                if is_nonterminal(B):
                    for prod_head, prod_body in augmented_productions:
                        if prod_head == B:
                            candidate: LR0Item = (B, prod_body, 0)
                            if candidate not in j_set:
                                new_items.add(candidate)
        if new_items:
            j_set.update(new_items)
            changed = True
    return frozenset(j_set)


def goto(
    items: frozenset[LR0Item],
    symbol: str,
    augmented_productions: list[tuple[str, str]],
) -> frozenset[LR0Item]:
    """Calcula GOTO(I, X) moviendo el punto sobre X y aplicando CLOSURE (Seccion 4.6.2, pag. 246)."""
    moved: set[LR0Item] = set()
    for head, body, dot in items:
        eff = effective_body(body)
        if dot < len(eff) and eff[dot] == symbol:
            moved.add((head, body, dot + 1))
    if not moved:
        return frozenset()
    return closure(moved, augmented_productions)


def build_canonical_collection(
    grammar: Grammar,
) -> tuple[
    list[frozenset[LR0Item]],
    dict[tuple[int, str], int],
    list[tuple[str, str]],
]:
    """Construye la coleccion canonica C = {I0, I1, ..., In} de conjuntos de items LR(0) (Fig. 4.33, pag. 246)."""
    augmented_productions: list[tuple[str, str]] = [
        (AUGMENTED_START, grammar.start_symbol)
    ] + list(grammar.production_list)

    initial_item: LR0Item = (AUGMENTED_START, grammar.start_symbol, 0)
    i0 = closure({initial_item}, augmented_productions)

    collection: list[frozenset[LR0Item]] = [i0]
    state_index: dict[frozenset[LR0Item], int] = {i0: 0}
    transitions: dict[tuple[int, str], int] = {}

    # Simbolos gramaticales ordenados de forma determinista
    all_symbols = list(grammar.nonterminals) + sorted(grammar.terminals)

    idx = 0
    while idx < len(collection):
        current_set = collection[idx]
        for sym in all_symbols:
            next_set = goto(current_set, sym, augmented_productions)
            if next_set:
                if next_set not in state_index:
                    state_index[next_set] = len(collection)
                    collection.append(next_set)
                transitions[(idx, sym)] = state_index[next_set]
        idx += 1

    return collection, transitions, augmented_productions


SLRAction = tuple[str, Any]
SLRActionTable = dict[tuple[int, str], list[SLRAction]]
SLRGotoTable = dict[tuple[int, str], int]


def build_slr_table(
    grammar: Grammar,
    follow_sets: dict[str, set[str]],
) -> tuple[
    SLRActionTable,
    SLRGotoTable,
    list[frozenset[LR0Item]],
    bool,
]:
    """Algoritmo 4.46: Construccion de una tabla de analisis sintactico SLR(1) (pags. 253-254)."""
    collection, transitions, _ = build_canonical_collection(grammar)
    action_table: SLRActionTable = {}
    goto_table: SLRGotoTable = {}

    terminals_and_end = set(grammar.terminals) | {ENDMARKER}
    for state_idx in range(len(collection)):
        for a in terminals_and_end:
            action_table[(state_idx, a)] = []

    for i, item_set in enumerate(collection):
        for head, body, dot in item_set:
            eff = effective_body(body)

            # Regla 2a: Si [A -> alfa . a beta] esta en Ii y GOTO(Ii, a) = Ij, ACTION[i, a] = shift j
            if dot < len(eff):
                a = eff[dot]
                if not is_nonterminal(a) and (i, a) in transitions:
                    j = transitions[(i, a)]
                    act: SLRAction = ("shift", j)
                    if act not in action_table[(i, a)]:
                        action_table[(i, a)].append(act)
            else:
                # El punto esta al final del cuerpo: [A -> alfa .]
                if head == AUGMENTED_START and body == grammar.start_symbol:
                    # Regla 2c: Si [S' -> S.] esta en Ii, ACTION[i, $] = accept
                    act = ("accept", None)
                    if act not in action_table[(i, ENDMARKER)]:
                        action_table[(i, ENDMARKER)].append(act)
                elif head != AUGMENTED_START:
                    # Regla 2b: Para todo a en FOLLOW(A), ACTION[i, a] = reduce A -> body
                    for a in follow_sets[head]:
                        act = ("reduce", (head, body))
                        if act not in action_table[(i, a)]:
                            action_table[(i, a)].append(act)

        # Regla 3: Transiciones GOTO para los no terminales A
        for nt in grammar.nonterminals:
            if (i, nt) in transitions:
                goto_table[(i, nt)] = transitions[(i, nt)]

    # La gramatica es SLR(1) si ninguna celda ACTION[i, a] tiene conflictos
    is_slr1 = all(len(acts) <= 1 for acts in action_table.values())
    return action_table, goto_table, collection, is_slr1


def parse_slr1(
    input_string: str,
    action_table: SLRActionTable,
    goto_table: SLRGotoTable,
) -> tuple[bool, ParseNode | None, list[dict[str, str]]]:
    """Algoritmo 4.44 (Fig. 4.36): Algoritmo de analisis sintactico LR (pags. 250-251).

    Retorna (aceptada, raiz_del_arbol, traza_de_pasos).
    """
    w = "" if input_string == EPSILON else input_string
    buffer = w + ENDMARKER
    ip = 0

    # Una cadena con simbolos que no son terminales no pertenece al lenguaje.
    # Los terminales son las columnas de ACTION (build_slr_table crea una por
    # cada terminal y otra para '$', que no puede aparecer dentro de la cadena).
    terminals = {a for (_, a) in action_table if a != ENDMARKER}
    if not contains_only_terminals(w, terminals):
        return False, None, [
            {"stack": "0", "symbols": "$", "input": buffer, "action": "error"}
        ]

    # Pila de estados con el estado inicial s0 = 0, y pila paralela de nodos del arbol
    state_stack: list[int] = [0]
    node_stack: list[ParseNode] = []
    trace: list[dict[str, str]] = []

    while True:
        s = state_stack[-1]
        a = buffer[ip] if ip < len(buffer) else ""

        stack_str = " ".join(str(st) for st in state_stack)
        symbols_str = "$" + "".join(nd.symbol for nd in node_stack)
        rem_input = buffer[ip:]

        actions = action_table.get((s, a), [])
        if not actions:
            trace.append(
                {
                    "stack": stack_str,
                    "symbols": symbols_str,
                    "input": rem_input,
                    "action": "error",
                }
            )
            return False, None, trace

        act_type, target = actions[0]

        if act_type == "shift":
            t = int(target)
            trace.append(
                {
                    "stack": stack_str,
                    "symbols": symbols_str,
                    "input": rem_input,
                    "action": f"shift {t}",
                }
            )
            state_stack.append(t)
            leaf = ParseNode(symbol=a, attributes={"lexval": a})
            node_stack.append(leaf)
            ip += 1

        elif act_type == "reduce":
            head, body = target
            trace.append(
                {
                    "stack": stack_str,
                    "symbols": symbols_str,
                    "input": rem_input,
                    "action": f"reduce {head} -> {body}",
                }
            )
            eff = effective_body(body)
            k = len(eff)

            if k > 0:
                del state_stack[-k:]
                children = node_stack[-k:]
                del node_stack[-k:]
            else:
                children = [ParseNode(symbol=EPSILON)]

            t = state_stack[-1]
            next_state = goto_table.get((t, head))
            if next_state is None:
                return False, None, trace

            state_stack.append(next_state)
            parent_node = ParseNode(
                symbol=head,
                production=(head, body),
                children=children,
            )
            node_stack.append(parent_node)

        elif act_type == "accept":
            trace.append(
                {
                    "stack": stack_str,
                    "symbols": symbols_str,
                    "input": rem_input,
                    "action": "accept",
                }
            )
            root = node_stack[-1] if node_stack else None
            return True, root, trace


# =============================================================================
# ITEM 3: DEFINICION DIRIGIDA POR LA SINTAXIS (SDD) Y GRAFO DE DEPENDENCIAS
# (Capitulo 5, Secciones 5.1 y 5.2 de Aho; Seccion 3 de sdt_revised.pdf)
# =============================================================================

# Referencia a una ocurrencia de simbolo dentro de una produccion:
# indice 0 = cabeza A; indice i >= 1 = i-esimo simbolo del cuerpo X_i (1-based).
AttrRef = tuple[int, str]


@dataclass
class SemanticRule:
    """Representa una regla semantica declarativa (Seccion 3, Paso 5.1: SDD como datos).

    - target: (indice_simbolo, nombre_atributo) que esta regla define.
    - dependencies: lista de (indice_simbolo, nombre_atributo) de los que depende.
    - compute: funcion que recibe la tupla de valores de 'dependencies' y retorna el valor.
    - description: expresion legible de la regla para visualizacion y trazabilidad.
    """

    target: AttrRef
    dependencies: list[AttrRef]
    compute: Callable[[ list[Any]], Any]
    description: str


@dataclass
class SDD:
    """Almacena la SDD como datos puros separados del motor evaluador (Paso 5.1)."""

    grammar: Grammar
    rules_by_production: dict[tuple[str, str], list[SemanticRule]]
    main_attribute: str


def build_default_sdd(circular: bool = False) -> SDD:
    """Construye la gramatica y SDD original del Item 3 (Pasos 1 y 2).

    Lenguaje: Expresiones de suma ponderada con operador prefijo de duplicacion de escala '^'.
    Gramatica G_SDD:
      3 no terminales: S, R, B
      6 producciones:
        1) S -> B R
        2) R -> + B R
        3) R -> e
        4) B -> ^ B
        5) B -> 2
        6) B -> 3
    Cumple G1 (convenciones de 2.2, es tanto LL(1) como SLR(1)),
    G2 (3 no terminales, 6 producciones, R y B son recursivos),
    y G3 (gramatica y calculo originales, distintos del libro y del PDF).

    Atributos:
      - scale (heredado, int) en B y R: factor de escala posicional/jerarquico.
      - val (sintetizado, int) en S, R y B: valor numerico ponderado del subarbol.
      - lexval (sintetizado, str) en los terminales '2', '3', '+', '^'.
    El simbolo inicial S NO tiene atributos heredados.
    """
    grammar_lines = [
        "S -> BR",
        "R -> +BR e",
        "B -> ^B 2 3",
    ]
    grammar = parse_grammar_lines(grammar_lines)

    # Reglas semanticas para S -> B R (indices: 0=S, 1=B, 2=R)
    if not circular:
        s_br_rules = [
            SemanticRule(
                target=(1, "scale"),
                dependencies=[],
                compute=lambda vals: 1,
                description="B.scale = 1",
            ),
            SemanticRule(
                target=(2, "scale"),
                dependencies=[(1, "scale")],
                compute=lambda vals: vals[0] + 1,
                description="R.scale = B.scale + 1",
            ),
            SemanticRule(
                target=(0, "val"),
                dependencies=[(1, "val"), (2, "val")],
                compute=lambda vals: vals[0] + vals[1],
                description="S.val = B.val + R.val",
            ),
        ]
    else:
        # Modificacion temporal del Paso 6 para demostrar deteccion de SDD circular:
        # B.scale depende de S.val y S.val depende de B.val (que depende de B.scale),
        # formando el ciclo B.scale -> B.val -> S.val -> B.scale.
        s_br_rules = [
            SemanticRule(
                target=(1, "scale"),
                dependencies=[(0, "val")],
                compute=lambda vals: vals[0],
                description="B.scale = S.val (CIRCULAR)",
            ),
            SemanticRule(
                target=(2, "scale"),
                dependencies=[(1, "scale")],
                compute=lambda vals: vals[0] + 1,
                description="R.scale = B.scale + 1",
            ),
            SemanticRule(
                target=(0, "val"),
                dependencies=[(1, "val"), (2, "val")],
                compute=lambda vals: vals[0] + vals[1],
                description="S.val = B.val + R.val",
            ),
        ]

    rules: dict[tuple[str, str], list[SemanticRule]] = {
        # 1) S -> B R (0=S, 1=B, 2=R)
        ("S", "BR"): s_br_rules,
        # 2) R -> + B R1 (0=R, 1='+', 2=B, 3=R1)
        ("R", "+BR"): [
            SemanticRule(
                target=(2, "scale"),
                dependencies=[(0, "scale")],
                compute=lambda vals: vals[0],
                description="B.scale = R.scale",
            ),
            SemanticRule(
                target=(3, "scale"),
                dependencies=[(0, "scale")],
                compute=lambda vals: vals[0] + 1,
                description="R1.scale = R.scale + 1",
            ),
            SemanticRule(
                target=(0, "val"),
                dependencies=[(2, "val"), (3, "val")],
                compute=lambda vals: vals[0] + vals[1],
                description="R.val = B.val + R1.val",
            ),
        ],
        # 3) R -> e (0=R)
        ("R", "e"): [
            SemanticRule(
                target=(0, "val"),
                dependencies=[],
                compute=lambda vals: 0,
                description="R.val = 0",
            ),
        ],
        # 4) B -> ^ B1 (0=B, 1='^', 2=B1)
        ("B", "^B"): [
            SemanticRule(
                target=(2, "scale"),
                dependencies=[(0, "scale")],
                compute=lambda vals: vals[0] * 2,
                description="B1.scale = B.scale * 2",
            ),
            SemanticRule(
                target=(0, "val"),
                dependencies=[(2, "val")],
                compute=lambda vals: vals[0],
                description="B.val = B1.val",
            ),
        ],
        # 5) B -> 2 (0=B, 1='2')
        ("B", "2"): [
            SemanticRule(
                target=(0, "val"),
                dependencies=[(1, "lexval"), (0, "scale")],
                compute=lambda vals: int(vals[0]) * vals[1],
                description="B.val = int(2.lexval) * B.scale",
            ),
        ],
        # 6) B -> 3 (0=B, 1='3')
        ("B", "3"): [
            SemanticRule(
                target=(0, "val"),
                dependencies=[(1, "lexval"), (0, "scale")],
                compute=lambda vals: int(vals[0]) * vals[1],
                description="B.val = int(3.lexval) * B.scale",
            ),
        ],
    }

    return SDD(
        grammar=grammar,
        rules_by_production=rules,
        main_attribute="val",
    )


def assign_node_ids(root: ParseNode) -> list[ParseNode]:
    """Asigna identificadores unicos en preorden a cada nodo del arbol de parseo."""
    nodes: list[ParseNode] = []

    def _visit(node: ParseNode) -> None:
        node.node_id = len(nodes) + 1
        nodes.append(node)
        for child in node.children:
            _visit(child)

    _visit(root)
    return nodes


# Un vertice del grafo de dependencias es (node_id, attr_name)
DepVertex = tuple[int, str]


@dataclass
class DependencyGraph:
    """Grafo de dependencias de atributos sobre un arbol de parseo (Seccion 5.2.1, pag. 310)."""

    vertices: list[DepVertex]
    edges: list[tuple[DepVertex, DepVertex]]
    vertex_rules: dict[DepVertex, tuple[SemanticRule, list[DepVertex]]]
    node_map: dict[int, ParseNode]


def build_dependency_graph(root: ParseNode, sdd: SDD) -> DependencyGraph:
    """Construye el grafo de dependencias instanciando las reglas de cada nodo interno (Seccion 5.2.1).

    Para cada regla que define el atributo b usando el atributo c, agrega una arista dirigida
    (c -> b), es decir, desde el atributo usado hacia el atributo definido.
    """
    all_nodes = assign_node_ids(root)
    node_map = {nd.node_id: nd for nd in all_nodes}

    vertices: list[DepVertex] = []
    vertex_set: set[DepVertex] = set()
    edges: list[tuple[DepVertex, DepVertex]] = []
    vertex_rules: dict[DepVertex, tuple[SemanticRule, list[DepVertex]]] = {}

    def _add_vertex(v: DepVertex) -> None:
        if v not in vertex_set:
            vertex_set.add(v)
            vertices.append(v)

    # Primero registrar los atributos lexval ya conocidos en las hojas terminales
    for nd in all_nodes:
        if "lexval" in nd.attributes:
            _add_vertex((nd.node_id, "lexval"))

    # Instanciar las reglas semanticas en cada nodo interno (no terminal)
    for nd in all_nodes:
        if nd.production is None:
            continue

        prod_rules = sdd.rules_by_production.get(nd.production, [])
        # Mapa de indice de simbolo en la produccion -> ParseNode:
        # 0 es la cabeza (nd), i >= 1 es el i-esimo hijo (nd.children[i - 1])
        symbol_nodes: dict[int, ParseNode] = {0: nd}
        for idx, child in enumerate(nd.children, start=1):
            symbol_nodes[idx] = child

        for rule in prod_rules:
            target_sym_idx, target_attr = rule.target
            target_node = symbol_nodes[target_sym_idx]
            target_vertex: DepVertex = (target_node.node_id, target_attr)
            _add_vertex(target_vertex)

            dep_vertices: list[DepVertex] = []
            for dep_sym_idx, dep_attr in rule.dependencies:
                dep_node = symbol_nodes[dep_sym_idx]
                dep_vertex: DepVertex = (dep_node.node_id, dep_attr)
                _add_vertex(dep_vertex)
                dep_vertices.append(dep_vertex)
                # Arista dirigida desde el atributo usado hacia el atributo definido
                edges.append((dep_vertex, target_vertex))

            vertex_rules[target_vertex] = (rule, dep_vertices)

    return DependencyGraph(
        vertices=vertices,
        edges=edges,
        vertex_rules=vertex_rules,
        node_map=node_map,
    )


def topological_sort(dep_graph: DependencyGraph) -> tuple[list[DepVertex], bool]:
    """Calcula un orden topologico del grafo de dependencias (Seccion 5.2.2, pag. 312).

    Retorna (orden_topologico, tiene_ciclo).
    """
    in_degree: dict[DepVertex, int] = {v: 0 for v in dep_graph.vertices}
    adj: dict[DepVertex, list[DepVertex]] = {v: [] for v in dep_graph.vertices}

    for u, v in dep_graph.edges:
        adj[u].append(v)
        in_degree[v] += 1

    # Cola de vertices con grado de entrada 0 (manteniendo el orden de aparicion)
    ready: list[DepVertex] = [v for v in dep_graph.vertices if in_degree[v] == 0]
    order: list[DepVertex] = []

    idx = 0
    while idx < len(ready):
        curr = ready[idx]
        idx += 1
        order.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                ready.append(neighbor)

    has_cycle = len(order) < len(dep_graph.vertices)
    return order, has_cycle


def evaluate_sdd_on_tree(
    root: ParseNode, sdd: SDD
) -> tuple[bool, DependencyGraph, list[DepVertex]]:
    """Construye el grafo de dependencias, obtiene el orden topologico y evalua los atributos (Paso 5.4)."""
    dep_graph = build_dependency_graph(root, sdd)
    order, has_cycle = topological_sort(dep_graph)
    if has_cycle:
        return False, dep_graph, order

    # Evaluar cada atributo siguiendo estrictamente el orden topologico
    for vertex in order:
        node_id, attr_name = vertex
        node = dep_graph.node_map[node_id]

        # Si es un terminal, su atributo lexval ya fue provisto por el scanner
        if vertex not in dep_graph.vertex_rules:
            continue

        rule, dep_vertices = dep_graph.vertex_rules[vertex]
        dep_values = [
            dep_graph.node_map[d_id].attributes[d_attr]
            for d_id, d_attr in dep_vertices
        ]
        node.attributes[attr_name] = rule.compute(dep_values)

    return True, dep_graph, order


def format_annotated_tree(root: ParseNode) -> str:
    """Formatea el arbol de parseo anotado (un nodo por linea, indentado por profundidad) (Paso 5.5)."""
    lines: list[str] = []

    def _render(node: ParseNode, depth: int) -> None:
        indent = "  " * depth
        if node.attributes:
            attrs_str = ", ".join(
                f"{k}={v}" for k, v in sorted(node.attributes.items())
            )
            lines.append(f"{indent}{node.symbol} (node {node.node_id}) [{attrs_str}]")
        else:
            lines.append(f"{indent}{node.symbol} (node {node.node_id})")
        for child in node.children:
            _render(child, depth + 1)

    _render(root, 0)
    return "\n".join(lines)


def run_sdd_mode(circular: bool = False) -> None:
    """Ejecuta el flujo del Item 3 (Seccion 3, Paso 5.5 de sdt_revised.pdf)."""
    sdd = build_default_sdd(circular=circular)

    # Leer todas las lineas disponibles en stdin
    raw_lines = [line.rstrip("\r\n") for line in sys.stdin]

    # Permitir opcionalmente que la gramatica de la SDD venga al inicio en formato Seccion 2.2
    start_idx = 0
    if (
        len(raw_lines) >= 2
        and raw_lines[0].strip().isdigit()
        and "->" in raw_lines[1]
    ):
        n = int(raw_lines[0].strip())
        sdd.grammar = parse_grammar_lines(raw_lines[1 : 1 + n])
        start_idx = 1 + n

    first_sets = compute_first_sets(sdd.grammar)
    follow_sets = compute_follow_sets(sdd.grammar, first_sets)
    ll1_table, is_ll1 = build_ll1_table(sdd.grammar, first_sets, follow_sets)
    slr_action, slr_goto, _, is_slr1 = build_slr_table(sdd.grammar, follow_sets)

    for line in raw_lines[start_idx:]:
        if line == "":
            break

        if is_ll1:
            accepted, tree_root, _ = parse_ll1(line, sdd.grammar, ll1_table)
        elif is_slr1:
            accepted, tree_root, _ = parse_slr1(line, slr_action, slr_goto)
        else:
            accepted, tree_root = False, None

        if not accepted or tree_root is None:
            print("no")
            continue

        ok, dep_graph, eval_order = evaluate_sdd_on_tree(tree_root, sdd)
        if not ok:
            print("Error: SDD is circular (cycle detected in dependency graph).")
            return

        print("Annotated Parse Tree:")
        print(format_annotated_tree(tree_root))

        formatted_order: list[str] = []
        for idx, (nid, attr) in enumerate(eval_order, start=1):
            sym = dep_graph.node_map[nid].symbol
            val = dep_graph.node_map[nid].attributes.get(attr)
            formatted_order.append(f"{idx}. {sym}(node {nid}).{attr} = {val}")

        print("Evaluation Order:")
        print(" -> ".join(formatted_order))
        print(
            f"{sdd.grammar.start_symbol}.{sdd.main_attribute} = "
            f"{tree_root.attributes[sdd.main_attribute]}"
        )


# =============================================================================
# FLUJO PRINCIPAL DE ENTRADA / SALIDA (Seccion 2.2.2 de sdt_revised.pdf)
# =============================================================================


def parse_lines_until_empty(parse_fn: Callable[[str], bool]) -> None:
    """Lee cadenas una por linea hasta recibir una linea vacia e imprime yes o no."""
    for raw_line in sys.stdin:
        line = raw_line.rstrip("\r\n")
        if line == "":
            break
        result = parse_fn(line)
        print("yes" if result else "no")


def main() -> None:
    """Punto de entrada principal del programa (Items 1, 2 y 3)."""
    args = sys.argv[1:]

    if "--sdd-circular" in args:
        run_sdd_mode(circular=True)
        return
    if "--sdd" in args:
        run_sdd_mode(circular=False)
        return

    show_sets = "--sets" in args

    grammar = read_grammar_from_stdin()
    if grammar is None:
        return

    # Item 1: Calcular conjuntos FIRST y FOLLOW
    first_sets = compute_first_sets(grammar)
    follow_sets = compute_follow_sets(grammar, first_sets)

    if show_sets:
        print_first_and_follow_sets(grammar, first_sets, follow_sets)

    # Item 2: Construir tablas LL(1) y SLR(1) y verificar condiciones sin conflictos
    ll1_table, is_ll1 = build_ll1_table(grammar, first_sets, follow_sets)
    slr_action, slr_goto, _, is_slr1 = build_slr_table(grammar, follow_sets)

    def _run_ll1(s: str) -> bool:
        accepted, _, _ = parse_ll1(s, grammar, ll1_table)
        return accepted

    def _run_slr1(s: str) -> bool:
        accepted, _, _ = parse_slr1(s, slr_action, slr_goto)
        return accepted

    # Casos 1, 2, 3 y 4 de la Seccion 2.2.2 de sdt_revised.pdf
    if is_ll1 and is_slr1:
        # Caso 1: La gramatica es tanto SLR(1) como LL(1)
        while True:
            print("Select a parser (T: for LL(1), B: for SLR(1), Q: quit):")
            choice_line = sys.stdin.readline()
            if not choice_line:
                break
            choice = choice_line.strip()
            if choice == "Q":
                break
            if choice == "T":
                parse_lines_until_empty(_run_ll1)
            elif choice == "B":
                parse_lines_until_empty(_run_slr1)
    elif is_ll1 and not is_slr1:
        # Caso 2: La gramatica es solo LL(1)
        print("Grammar is LL(1).")
        parse_lines_until_empty(_run_ll1)
    elif is_slr1 and not is_ll1:
        # Caso 3: La gramatica es solo SLR(1)
        print("Grammar is SLR(1).")
        parse_lines_until_empty(_run_slr1)
    else:
        # Caso 4: La gramatica no es ni LL(1) ni SLR(1)
        print("Grammar is neither LL(1) nor SLR(1).")


if __name__ == "__main__":
    main()
