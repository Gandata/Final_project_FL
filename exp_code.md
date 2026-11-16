# Guia de Sustentacion Oral y Explicacion Linea por Linea (`main.py`)

Este documento prepara a todos los integrantes del grupo para defender el proyecto final de **Lenguajes Formales y Compiladores** ante el profesor. Explica la arquitectura general, las estructuras de datos nativas elegidas, el funcionamiento detallado linea por linea de cada algoritmo implementado en `main.py` con su referencia exacta al libro de Aho et al. (*Compilers: Principles, Techniques, and Tools*, 2da Edicion, Capitulos 4 y 5), y un banco de preguntas trampa y modificaciones en vivo.

---

## 1. Arquitectura General y Estructuras de Datos

El archivo `main.py` utiliza **exclusivamente la libreria estandar de Python** (`sys`, `dataclasses`, `typing`), cumpliendo estrictamente la restriccion de la Seccion 2 de `docs/sdt_revised.pdf`.

### 1.1 Constantes Globales (Lineas 17–21)
- `EPSILON = "e"`: Representa la cadena vacia $\varepsilon$. Por la Seccion 2.2, `'e'` nunca es un simbolo terminal.
- `ENDMARKER = "$"`: Marca el fin de la cadena de entrada y el fondo de la pila en LL(1).
- `INITIAL_SYMBOL = "S"`: Toda gramatica de entrada tiene a `'S'` como simbolo inicial.
- `AUGMENTED_START = "S'"`: Nuevo simbolo inicial para la gramatica aumentada $G'$ en SLR(1) con la produccion $S' \to S$ (Seccion 4.6.2, pag. 243).

### 1.2 Estructuras de Datos Principales
1. **`Grammar` (`@dataclass`, Lineas 29–37)**:
   - `nonterminals: list[str]`: Lista de no terminales en el orden en que aparecen en la entrada (letras mayusculas).
   - `terminals: set[str]`: Conjunto de simbolos terminales detectados en los cuerpos de las producciones.
   - `productions: dict[str, list[str]]`: Mapa de cada no terminal $A$ a su lista de alternativas $[\alpha_1, \alpha_2, \dots]$.
   - `production_list: list[tuple[str, str]]`: Lista plana de pares `(cabeza, cuerpo)` que preserva el orden exacto de las producciones para numerarlas en SLR(1).
   - `start_symbol: str`: Inicializado en `"S"`.

2. **`ParseNode` (`@dataclass`, Lineas 228–235)**:
   - Representa un nodo del arbol de analisis sintactico (*Parse Tree*, Seccion 4.2.4 y Seccion 5.1.2).
   - `symbol: str`: Simbolo gramatical del nodo (no terminal, terminal o `'e'`).
   - `production: tuple[str, str] | None`: Produccion `(A, alfa)` aplicada en ese nodo si es un nodo interno; `None` si es una hoja terminal o epsilon.
   - `children: list[ParseNode]`: Lista ordenada de hijos de izquierda a derecha.
   - `attributes: dict[str, Any]`: Diccionario donde se guardan los valores de los atributos del nodo (ej. `{"lexval": "2"}` en hojas o `{"scale": 2, "val": 4}` en nodos internos).
   - `node_id: int`: Identificador entero unico asignado en preorden para distinguir multiples apariciones del mismo simbolo en el arbol.

3. **`LR0Item` (`tuple[str, str, int]`, Linea 353)**:
   - Representa un item $LR(0)$ $[A \to \alpha \cdot \beta]$ mediante la tupla `(head, body, dot_pos)`, donde `dot_pos` es el indice entero $(0 \le \text{dot\_pos} \le |\text{body}|)$ que indica cuantos simbolos del cuerpo estan a la izquierda del punto.
   - Un estado del automata $LR(0)$ es un `frozenset[LR0Item]`, lo que permite usar conjuntos de items como llaves de diccionarios en Python (`state_index`).

4. **`SemanticRule` y `SDD` (`@dataclass`, Lineas 525–548)**:
   - Cumplen el requisito del Paso 5.1 (*Representation of the SDD: data, not code*).
   - `AttrRef = tuple[int, str]`: Referencia declarativa a un atributo dentro de una produccion: el indice `0` representa la cabeza $A$ de la produccion, y el indice $i \ge 1$ representa el $i$-esimo simbolo del cuerpo $X_i$ (de izquierda a derecha, 1-based).
   - `SemanticRule`: Contiene `target` (que atributo define), `dependencies` (lista de `AttrRef` que usa), `compute` (funcion pura `lambda` que calcula el valor a partir de la lista de valores de sus dependencias) y `description`.
   - `SDD`: Contiene la gramatica, el diccionario `rules_by_production` y el nombre del atributo principal `main_attribute`.

5. **`DependencyGraph` (`@dataclass`, Lineas 672–680)**:
   - Un vertice del grafo de dependencias es `DepVertex = tuple[int, str]`, es decir, `(node_id, nombre_atributo)`.
   - `vertices`: Lista de todos los vertices $(N, a)$ del arbol.
   - `edges`: Lista de aristas dirigidas `(u, v)` donde el atributo `u` se usa para calcular el atributo `v` (`usado -> definido`).
   - `vertex_rules`: Asocia cada vertice calculable con la tupla `(regla_semantica, lista_de_vertices_dependientes)`.

---

## 2. Explicacion Linea por Linea de `main.py`

### 2.1 Lectura de la Gramatica (`parse_grammar_lines` y `read_grammar_from_stdin`, Lineas 40–93)
- **`is_nonterminal(symbol)` (Lineas 40–42)**: Retorna `True` si el simbolo es `"S'"` o un caracter en mayuscula (`symbol.isupper()`).
- **`is_terminal(symbol)` (Lineas 45–53)**: Verifica las reglas de la Seccion 2.2: longitud 1, no es mayuscula, no es `'e'`, no es `'$'` y no es espacio.
- **`parse_grammar_lines(lines)` (Lineas 56–83)**:
  - Recorre cada linea, divide por `"->"` en `head_part` y `body_part`.
  - Separa las alternativas por espacios en blanco con `body_part.strip().split()`.
  - Por cada alternativa `alt`, la guarda en `productions[head]` y en `production_list`.
  - Si `alt != "e"`, recorre cada caracter `ch` de la alternativa; si no es no terminal (`not is_nonterminal(ch)`), lo agrega al conjunto `terminals`.

---

### 2.2 Item 1: Conjuntos `FIRST` y `FOLLOW` (Seccion 4.4.2, pags. 220–222)

#### Funcion `compute_first_sets(grammar)` (Lineas 99–144)
Implementa las 3 reglas de la Seccion 4.4.2 (pag. 221):
1. **Lineas 110–115**: Inicializa `first[t] = {t}` para cada terminal `t` (Regla 1) y `first[nt] = set()` para cada no terminal `nt`.
2. **Lineas 118–142 (Bucle de punto fijo `while changed`)**:
   - Recorre cada produccion `(head, body)` de la gramatica.
   - Guarda `before_size = len(first[head])` para detectar si se anadio algun elemento nuevo en esta iteracion.
   - **Caso `body == "e"` (Lineas 125–126)**: Aplica la Regla 3: agrega `"e"` a `first[head]`.
   - **Caso `body != "e"` (Lineas 127–139)**: Aplica la Regla 2 para $X \to Y_1 Y_2 \dots Y_k$:
     - Inicializa `all_nullable = True`.
     - Recorre cada simbolo $Y_i$ del cuerpo de izquierda a derecha:
       - Agrega todos los simbolos de `FIRST(Y_i)` distintos de `"e"` a `first[head]`.
       - **Condicion clave (Linea 134)**: `if EPSILON not in sym_first:`. Si $Y_i$ **no** puede derivar $\varepsilon$, entonces ningun simbolo posterior $Y_{i+1}$ puede iniciar una cadena derivada desde $X$. Por eso se marca `all_nullable = False` y se ejecuta `break` para detener el recorrido del cuerpo.
     - **Lineas 137–138**: Si el bucle termino sin hacer `break` (`all_nullable == True`), significa que **todos** los $Y_1, \dots, Y_k$ tienen `'e'` en su `FIRST`, por lo que la produccion completa puede derivar $\varepsilon$ y se agrega `'e'` a `first[head]`.
   - **Lineas 140–141**: Si `len(first[head]) > before_size`, algun conjunto crecio, por lo que `changed = True` y el `while` repite otra pasada. Cuando en una pasada completa ningun conjunto crece, se alcanzo el punto fijo y termina.

#### Funcion `compute_first_of_string(alpha, first_sets)` (Lineas 147–166)
Extiende `FIRST` a cualquier cadena $\alpha = X_1 X_2 \dots X_n$ (necesario para `FOLLOW` y para la tabla `LL(1)`):
- Si `alpha` es vacia o `"e"`, retorna `{"e"}`.
- De lo contrario, recorre $X_1, X_2, \dots, X_n$ copiando `FIRST(X_i) - {"e"}` mientras `"e" in FIRST(X_i)`. Si todos contienen `"e"`, agrega `"e"` al resultado.

#### Funcion `compute_follow_sets(grammar, first_sets)` (Lineas 169–216)
Implementa las 3 reglas de `FOLLOW(A)` de la Seccion 4.4.2 (pags. 221–222):
1. **Lineas 181–185 (Regla 1)**: Inicializa `follow[nt] = set()` para todo no terminal y coloca `"$"` en `follow["S"]` porque `'S'` es el simbolo inicial.
2. **Lineas 188–214 (Bucle de punto fijo `while changed`)**:
   - Recorre cada produccion $A \to \text{body}$. Si `body == "e"`, no hay simbolos en el cuerpo y pasa a la siguiente (`continue`).
   - Recorre cada posicion `i` y simbolo $B = \text{body}[i]$. Si $B$ es terminal (`symbol not in follow`), lo ignora.
   - Si $B$ es un no terminal, obtiene la subcadena derecha $\beta = \text{body}[i+1:]$.
   - **Si $\beta$ no es vacia (Lineas 200–208)**:
     - Calcula `first_beta = compute_first_of_string(beta, first_sets)`.
     - **Regla 2**: Agrega todo elemento de `first_beta` distinto de `"e"` a `follow[B]`.
     - **Regla 3 (parte a)**: `if EPSILON in first_beta: follow[symbol].update(follow[head])`. Si $\beta \Rightarrow^* \varepsilon$, entonces $B$ puede quedar al final de la forma sentencial derivada de $A$, por lo que todo lo que siga a $A$ (`FOLLOW(A)`) tambien puede seguir a $B$.
   - **Si $\beta$ es vacia (Lineas 209–211)**:
     - **Regla 3 (parte b)**: $B$ esta al extremo derecho de $A \to \alpha B$, por lo que `follow[symbol].update(follow[head])`.

#### Formateo para `--sets` (`format_symbol_set` y `print_first_and_follow_sets`, Lineas 219–238)
- Separa los terminales ordinarios (`s != "e"` y `s != "$"`), los ordena por codigo ASCII con `sorted(...)`, y luego anade `"e"` (si pertenece al conjunto) y finalmente `"$"` (si pertenece al conjunto).
- Imprime primero todas las lineas `First(A) = {...}` con `A` en orden alfabetico y luego todas las lineas `Follow(A) = {...}` en orden alfabetico, cumpliendo al pie de la letra la Seccion 2.1.

---

### 2.3 Item 2 (Parte A): Parser Predictivo `LL(1)` (Secciones 4.4.3 y 4.4.4)

#### Funcion `build_ll1_table(grammar, first_sets, follow_sets)` (Lineas 256–294)
Implementa el **Algoritmo 4.31** (pag. 224):
- Cada celda `table[(nt, sym)]` es una **lista** de producciones `list[tuple[str, str]]`. Usamos una lista en lugar de sobrescribir un unico valor para poder detectar si caen 2 o mas producciones en la misma celda (conflicto LL(1)).
- Para cada produccion $A \to \alpha$:
  1. Calcula `first_alpha = compute_first_of_string(body, first_sets)`.
  2. **Paso 1 (Lineas 275–279)**: Para cada terminal $a \in \text{FIRST}(\alpha)$ con $a \neq \text{'e'}$, agrega `(head, body)` a $M[A, a]$.
  3. **Paso 2 (Lineas 283–287)**: Si `'e' in first_alpha`, para cada simbolo $b \in \text{FOLLOW}(A)$ (incluyendo `'$'`), agrega `(head, body)` a $M[A, b]$.
- **Verificacion de la condicion LL(1) (Linea 290)**:
  `is_ll1 = all(len(prods) <= 1 for prods in table.values())`.
  Segun el teorema de la Seccion 4.4.3 (pags. 223–225), las 3 condiciones formales de una gramatica LL(1) ($\text{FIRST}(\alpha) \cap \text{FIRST}(\beta) = \emptyset$, a lo sumo una alternativa deriva $\varepsilon$, y si $\beta \Rightarrow^* \varepsilon$ entonces $\text{FIRST}(\alpha) \cap \text{FOLLOW}(A) = \emptyset$) equivalen exactamente a que ninguna celda $M[A, a]$ tenga entradas multiplemente definidas.

#### Funcion `parse_ll1(input_string, grammar, table)` (Lineas 297–374)
Implementa el **Algoritmo 4.34 / Figura 4.20** (pag. 227) construyendo a la vez el arbol de parseo:
- **Linea 306**: Si `input_string == "e"`, la cadena de entrada $w$ es `""`; le concatena `"$"` para formar `buffer = w + "$"`.
- **Lineas 310–312**: Crea el nodo raiz `ParseNode(symbol="S")` y el marcador de fondo `ParseNode(symbol="$")`, e inicializa la pila `stack = [end_node, root]` (el tope de la pila es `stack[-1]`).
- En cada iteracion del bucle:
  - Sea $X$ el simbolo del nodo en el tope de la pila (`stack[-1]`) y $a = \text{buffer}[\text{ip}]$.
  - **Caso 1 (`X == "$"`)**: Si $a == \text{"\$"}$, la pila y la entrada llegaron simultaneamente a `$`, por lo que retorna `True` (`accept`). Si no, retorna `False`.
  - **Caso 2 (`X == a`)**: Coinciden el terminal en el tope de la pila y el simbolo actual de entrada. Guarda `top_node.attributes["lexval"] = a`, desapila (`stack.pop()`) y avanza el puntero de entrada `ip += 1`.
  - **Caso 3 (`X` es un terminal distinto de `a`)**: Error sintactico (`return False`).
  - **Caso 4 (`X` es no terminal)**: Consulta `entries = table.get((X, a), [])`.
    - Si `entries` esta vacia, la celda $M[X, a]$ es de error (`return False`).
    - Si hay produccion $X \to Y_1 Y_2 \dots Y_k$, desapila $X$, asigna `top_node.production = (head, body)` y:
      - Si `body == "e"`, le agrega al nodo en el arbol un hijo hoja `ParseNode(symbol="e")` pero **no apila nada** en `stack` (porque $\varepsilon$ no consume entrada).
      - Si `body != "e"`, crea los nodos hijos `[ParseNode(symbol=sym) for sym in body]`, los enlaza en `top_node.children`, y los apila en **orden inverso** (`for child in reversed(children): stack.append(child)`) para que $Y_1$ quede en el tope de la pila.

---

### 2.4 Item 2 (Parte B): Parser `SLR(1)` (Secciones 4.6.2, 4.6.3 y 4.6.4)

#### Funcion `effective_body(body)` (Lineas 382–384)
- **Detalle clave del libro (Seccion 4.6.2, pag. 242)**: *"The production $A \to \varepsilon$ generates only one item, $A \to \cdot$."*
- En nuestra entrada, $\varepsilon$ se escribe como `'e'`. Si trataramos `'e'` como un caracter normal de longitud 1, generariamos erroneamente dos items ($A \to \cdot e$ y $A \to e \cdot$) y el automata intentaria hacer *shift* con `'e'`.
- Por eso `effective_body("e")` devuelve `""` (longitud 0). Asi, para $A \to e$, `dot` solo puede valer `0`, lo cual cumple simultaneamente `dot == len(eff)` (el punto ya esta al final del cuerpo, listo para reducir 0 simbolos).

#### Funcion `closure(items, augmented_productions)` (Lineas 387–407)
Implementa la **Figura 4.32** (pag. 245):
- Parte de `j_set = set(items)`.
- En un bucle `while changed`: por cada item $(A, \text{body}, \text{dot}) \in J$, si el punto no esta al final (`dot < len(eff)`) y el simbolo inmediatamente despues del punto $B = \text{eff}[\text{dot}]$ es un no terminal, busca todas las producciones $B \to \gamma$ y agrega el item $(B, \gamma, 0)$ si no estaba ya en $J$.
- Retorna `frozenset(j_set)`.

#### Funcion `goto(items, symbol, augmented_productions)` (Lineas 410–423)
Implementa la funcion `GOTO(I, X)` (Seccion 4.6.2, pag. 246):
- Busca todos los items en `items` que tengan a `symbol` inmediatamente a la derecha del punto (`dot < len(eff) and eff[dot] == symbol`).
- Crea el conjunto nucleo `moved` desplazando el punto una posicion a la derecha (`dot + 1`).
- Si `moved` es vacio, retorna `frozenset()`; de lo contrario, retorna `closure(moved, augmented_productions)`.

#### Funcion `build_canonical_collection(grammar)` (Lineas 426–460)
Implementa la **Figura 4.33** (pag. 246):
- Crea las producciones aumentadas encabezadas por `("S'", "S")`.
- Calcula el estado inicial $I_0 = \text{CLOSURE}(\{[S' \to \cdot S]\})$.
- Recorre con una cola indice `idx` todos los estados descubiertos en `collection`: para cada simbolo gramatical $X$, calcula `next_set = goto(current_set, sym, augmented_productions)`. Si no es vacio y no estaba en `collection`, le asigna un nuevo numero de estado y registra la transicion `transitions[(idx, sym)] = state_index[next_set]`.

#### Funcion `build_slr_table(grammar, follow_sets)` (Lineas 467–524)
Implementa el **Algoritmo 4.46** (pags. 253–254):
- Para cada estado $i$ y su conjunto de items $I_i$:
  - **Regla 2a (Shift, Lineas 488–494)**: Si `dot < len(eff)` y el simbolo $a = \text{eff}[\text{dot}]$ es un terminal con $\text{GOTO}(I_i, a) = j$, agrega `("shift", j)` a `action_table[(i, a)]`.
  - **Regla 2c (Accept, Lineas 497–501)**: Si `dot == len(eff)` y el item es $[S' \to S \cdot]$, agrega `("accept", None)` a `action_table[(i, "$")]`.
  - **Regla 2b (Reduce, Lineas 502–507)**: Si `dot == len(eff)` y la cabeza $A \neq S'$, entonces para cada simbolo $a \in \text{FOLLOW}(A)$, agrega `("reduce", (A, body))` a `action_table[(i, a)]`.
  - **Regla 3 (GOTO, Lineas 510–512)**: Para cada no terminal $A$, si existe transicion $(i, A) \to j$, define `goto_table[(i, A)] = j`.
- **Condicion SLR(1) (Linea 515)**: `is_slr1 = all(len(acts) <= 1 for acts in action_table.values())`. Si alguna celda `ACTION[i, a]` tiene 2 o mas acciones (por ejemplo, un `shift` y un `reduce` = conflicto *shift/reduce*, o dos `reduce` distintos = conflicto *reduce/reduce*), `is_slr1` es `False`.

#### Funcion `parse_slr1(input_string, action_table, goto_table)` (Lineas 527–618)
Implementa el **Algoritmo 4.44 / Figura 4.36** (pags. 250–251):
- Mantiene `state_stack = [0]` (pila de estados con $s_0 = 0$) y `node_stack = []` (pila paralela de subarboles para construir el arbol de parseo *bottom-up*).
- En cada paso consulta `actions = action_table.get((s, a), [])` donde $s$ es el estado en el tope de `state_stack` y $a$ es el simbolo actual de entrada:
  - Si `actions` es vacia: error sintactico (`return False`).
  - Si es `("shift", t)`: apila el estado `t` en `state_stack`, crea una hoja terminal `ParseNode(symbol=a, attributes={"lexval": a})` en `node_stack`, y avanza `ip += 1`.
  - Si es `("reduce", (head, body))`:
    - Calcula la longitud efectiva $k = |\text{effective\_body}(\text{body})|$.
    - Si $k > 0$, desapila $k$ estados de `state_stack` y toma los ultimos $k$ nodos de `node_stack` como hijos del nuevo nodo `head`.
    - Si $k == 0$ (produccion $A \to e$), **no desapila ningun estado** de `state_stack` y crea como unico hijo `ParseNode(symbol="e")`.
    - Consulta el estado $t$ que quedo en el tope de `state_stack`, busca `next_state = goto_table[(t, head)]`, lo apila en `state_stack` y apila el nuevo subarbol `parent_node` en `node_stack`.
  - Si es `("accept", None)`: retorna `True` y la raiz del arbol `node_stack[-1]`.

---

### 2.5 Item 3: Evaluador de SDD por Grafo de Dependencias (Secciones 5.1 y 5.2)

#### Funcion `build_default_sdd(circular=False)` (Lineas 551–660)
Define declarativamente nuestra gramatica original $G_{\text{SDD}}$ (`S -> BR`, `R -> +BR | e`, `B -> ^B | 2 | 3`) y sus reglas semanticas como objetos `SemanticRule`:
- Nota sobre indices en cada produccion:
  - En `S -> BR`: `0` es `S`, `1` es `B`, `2` es `R`.
  - En `R -> +BR`: `0` es `R` (cabeza), `1` es `'+'`, `2` es `B`, `3` es $R_1$ (hijo recursivo).
  - En `B -> ^B`: `0` es `B` (cabeza), `1` es `'^'`, `2` es $B_1$ (hijo recursivo).
  - Gracias a esta convencion posicional, distinguir entre la cabeza $B$ (indice `0`) y el hijo $B_1$ (indice `2`) en una produccion recursiva es inmediato y libre de ambiguedad.

#### Funcion `build_dependency_graph(root, sdd)` (Lineas 683–737)
Implementa la construccion del grafo de dependencias de la **Seccion 5.2.1** (pag. 310):
1. Numera todos los nodos del arbol en preorden (`assign_node_ids(root)`), de modo que cada nodo del arbol tiene un `node_id` unico $(1, 2, \dots, m)$.
2. Registra primero los vertices `(nd.node_id, "lexval")` de todas las hojas terminales (cuyo valor ya fue entregado por el analizador lexico durante el parseo).
3. Para cada nodo interno `nd` con `nd.production = (head, body)`:
   - Construye el diccionario local `symbol_nodes`: `{0: nd, 1: nd.children[0], 2: nd.children[1], ...}`.
   - Por cada `rule` de esa produccion:
     - Traduce `rule.target` `(target_sym_idx, target_attr)` al vertice real del arbol `target_vertex = (symbol_nodes[target_sym_idx].node_id, target_attr)`.
     - Traduce cada dependencia `(dep_sym_idx, dep_attr)` al vertice real `dep_vertex = (symbol_nodes[dep_sym_idx].node_id, dep_attr)`.
     - **Direccion de la arista (Linea 728)**: `edges.append((dep_vertex, target_vertex))`. La arista va **desde el atributo del que se depende (`dep_vertex`) hacia el atributo definido (`target_vertex`)**, tal como exige la Seccion 5.2.1.

#### Funcion `topological_sort(dep_graph)` (Lineas 740–765)
Implementa el ordenamiento topologico y deteccion de ciclos de la **Seccion 5.2.2** (pag. 312) mediante el algoritmo de grados de entrada (Kahn):
1. Calcula `in_degree[v]` (numero de aristas que entran a `v`) para cada vertice `v`.
2. Coloca en la cola `ready` todos los vertices con `in_degree[v] == 0` (atributos que no dependen de ningun otro, como los `lexval` de las hojas y las constantes iniciales como `B.scale = 1` o `R.val = 0`).
3. Extrae vertices de `ready` uno por uno, los agrega a `order`, y decrementa en 1 el `in_degree` de todos sus vecinos `neighbor`. Si algun vecino llega a `in_degree == 0`, entra a `ready`.
4. **Deteccion de ciclos (Linea 763)**: `has_cycle = len(order) < len(dep_graph.vertices)`.
   - Si existe un ciclo en el grafo de dependencias, ningun vertice del ciclo tendra jamas `in_degree == 0`, por lo que nunca entraran a `ready` y `len(order)` sera estrictamente menor que el total de vertices.

#### Funcion `evaluate_sdd_on_tree(root, sdd)` (Lineas 768–792)
- Llama a `build_dependency_graph` y `topological_sort`.
- Si `has_cycle` es `True`, retorna inmediatamente `(False, dep_graph, order)` y el programa reporta que la SDD es circular.
- Si no hay ciclo, recorre `for vertex in order:` y calcula cada atributo invocando `rule.compute(dep_values)`. Como sigue el orden topologico, cuando se evalua `vertex`, **todos** los atributos en `dep_vertices` ya fueron calculados previamente.

---

## 3. Banco de Preguntas Trampa y Modificaciones en Vivo para la Sustentacion

### Pregunta 1: "¿Por que una gramatica con recursion por la izquierda nunca puede ser LL(1)?"
- **Respuesta**: Si un no terminal $A$ tiene una produccion recursiva por la izquierda $A \to A\alpha \mid \beta$, entonces todo terminal $a \in \text{FIRST}(\beta)$ pertenece tambien a $\text{FIRST}(A)$, y por tanto pertenece tambien a $\text{FIRST}(A\alpha)$. Al aplicar el **Algoritmo 4.31**, en la celda $M[A, a]$ se insertaran tanto $A \to A\alpha$ como $A \to \beta$, generando una entrada multiplemente definida (conflicto LL(1)). Ademas, si $\beta \Rightarrow^* \varepsilon$, entonces $\varepsilon \in \text{FIRST}(\beta)$ y todo simbolo de $\text{FOLLOW}(A)$ generara conflicto en $M[A, b]$.

### Pregunta 2: "¿Por que el Ejemplo 1 (`S -> S+T | T`) no es LL(1) pero si es SLR(1)?"
- **Respuesta**: No es LL(1) porque `S` y `T` son recursivos por la izquierda, por lo que `FIRST(S+T)` y `FIRST(T)` comparten `{(, i}`, causando conflicto en `M[S, (]` y `M[S, i]`. En cambio, si es SLR(1) porque el parser bottom-up desplaza (*shifts*) los simbolos a la pila y solo decide reducir cuando ya vio todo el cuerpo de la produccion (`S+T.` o `T.`), usando `FOLLOW(S) = {+, ), $}` y `FOLLOW(T) = {+, *, ), $}` sin ningun conflicto *shift/reduce* ni *reduce/reduce*.

### Pregunta 3: "¿Puede una gramatica ser LL(1) pero NO ser SLR(1)? Muestre un ejemplo."
- **Respuesta**: Si, aunque es poco comun, existen gramaticas LL(1) que no son SLR(1) porque SLR(1) usa todo el conjunto global `FOLLOW(A)` sin recordar el contexto izquierdo en la pila. El ejemplo clasico es el **Ejercicio 4.6.5 del libro de Aho (pag. 258)**:
  `S -> AaAb | BbBa`, `A -> e`, `B -> e`.
  - Es **LL(1)** porque `FIRST(AaAb) = {a}` y `FIRST(BbBa) = {b}` son disjuntos.
  - **No es SLR(1)** porque en el estado inicial $I_0$ estan simultaneamente los items completos $[A \to \cdot]$ y $[B \to \cdot]$, y como `FOLLOW(A) = {a, b}` y `FOLLOW(B) = {a, b}`, en `ACTION[0, a]` y `ACTION[0, b]` hay un conflicto **reduce/reduce** entre reducir por $A \to \varepsilon$ y reducir por $B \to \varepsilon$.

### Pregunta 4: "¿Que ocurre exactamente en su codigo cuando hay una produccion epsilon (`A -> e`) en SLR(1)?"
- **Respuesta**: En la funcion `effective_body(body)` (linea 382), si `body == "e"` devolvemos la cadena vacia `""` de longitud 0. Asi:
  1. En `closure`, el item $(A, \text{"e"}, 0)$ tiene `dot = 0 == len(eff)`, por lo que ya es un item completo $[A \to \cdot]$ (como indica la pag. 242 del libro).
  2. En `build_slr_table`, ese item genera acciones `reduce A -> e` para todo $a \in \text{FOLLOW}(A)$.
  3. En `parse_slr1` (linea 586), al reducir por $A \to e$, como $k = |\text{eff}| = 0$, no se saca ningun estado de `state_stack`, simplemente se mira el estado $t$ en el tope, se apila `GOTO[t, A]` y se crea en `node_stack` un nodo `A` con un hijo hoja `e`.

### Pregunta 5: "¿Como me demuestra en el codigo que su evaluador del Item 3 no evalua el arbol recursivamente en un orden fijo?"
- **Respuesta**: En la funcion `evaluate_sdd_on_tree` (lineas 768–792), no existe ninguna recursion sobre los hijos del arbol. El evaluador toma la lista plana `order` devuelta por `topological_sort(dep_graph)` y ejecuta un unico bucle lineal `for vertex in order:` (linea 777). Si cambiamos las reglas en `build_default_sdd` para que un atributo heredado del hijo izquierdo dependa de un atributo del hijo derecho (una SDD que ni siquiera es L-atribuida), `build_dependency_graph` invierte la arista y `topological_sort` evalua primero el hijo derecho y luego el izquierdo sin tocar una sola linea del motor evaluador.

### Pregunta 6 (Modificacion en vivo): "Cambie en vivo el factor multiplicador de `^` para que triplique la escala en vez de duplicarla, o cambie la escala inicial de `B` a 10."
- **Respuesta**: Como la SDD esta guardada como datos en `build_default_sdd` (`main.py`, lineas 575–653):
  - Para que `^` triplique la escala: en la produccion `("B", "^B")` (linea 632), cambiamos `compute=lambda vals: vals[0] * 2` por `compute=lambda vals: vals[0] * 3`.
  - Para que la escala inicial sea 10: en la produccion `("S", "BR")` (linea 579), cambiamos `compute=lambda vals: 1` por `compute=lambda vals: 10`.
  No hay que modificar ni el parser, ni el constructor del grafo, ni el ordenador topologico.
