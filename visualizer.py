"""Visualizador academico interactivo para LL(1), SLR(1) y Evaluador SDD.

Implementado con Streamlit, Graphviz y Pandas consumiendo directamente las
estructuras y algoritmos del modulo principal (main.py).
Diseno sobrio y editorial inspirado en Aho et al. (2da Edicion).
"""

from __future__ import annotations

import graphviz
import pandas as pd
import streamlit as st

import main as core


# =============================================================================
# CONFIGURACION VISUAL Y ESTILOS EDITORIALES (Sobrio, academico, sin emojis)
# =============================================================================

st.set_page_config(
    page_title="Formal Languages & Compilers Workbench",
    layout="wide",
    initial_sidebar_state="expanded",
)

ACADEMIC_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #182232;
    }

    code, pre, .mono {
        font-family: 'IBM Plex Mono', monospace !important;
    }

    .main-header {
        border-bottom: 2px solid #182232;
        padding-bottom: 0.75rem;
        margin-bottom: 1.5rem;
    }

    .main-header h1 {
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        color: #182232;
    }

    .main-header p {
        font-size: 0.92rem;
        color: #526071;
        margin: 0.25rem 0 0 0;
    }

    .section-card {
        background-color: #FFFFFF;
        border: 1px solid #D8E0E8;
        border-radius: 4px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #182232;
        border-bottom: 1px solid #E5E9F0;
        padding-bottom: 0.4rem;
        margin-bottom: 0.75rem;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        font-size: 0.82rem;
        font-weight: 600;
        border-radius: 3px;
        font-family: 'IBM Plex Mono', monospace;
        margin-right: 0.5rem;
    }

    .badge-ok {
        background-color: #F0FDF4;
        color: #15803D;
        border: 1px solid #BBF7D0;
    }

    .badge-conflict {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
    }

    .badge-info {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }

    .step-box {
        background-color: #F8FAFC;
        border-left: 4px solid #1D4ED8;
        border-top: 1px solid #D8E0E8;
        border-right: 1px solid #D8E0E8;
        border-bottom: 1px solid #D8E0E8;
        padding: 0.85rem 1.1rem;
        border-radius: 0 4px 4px 0;
        margin-bottom: 1rem;
    }

    .step-box-error {
        background-color: #FEF2F2;
        border-left: 4px solid #B91C1C;
        border-top: 1px solid #FECACA;
        border-right: 1px solid #FECACA;
        border-bottom: 1px solid #FECACA;
        padding: 0.85rem 1.1rem;
        border-radius: 0 4px 4px 0;
        margin-bottom: 1rem;
    }

    .kv-label {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #526071;
        margin-bottom: 0.15rem;
        font-weight: 600;
    }

    .kv-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1rem;
        font-weight: 600;
        color: #182232;
        background: #FFFFFF;
        border: 1px solid #D8E0E8;
        padding: 0.4rem 0.65rem;
        border-radius: 3px;
    }
</style>
"""
st.markdown(ACADEMIC_CSS, unsafe_allow_html=True)


# =============================================================================
# GRAMATICAS PREDEFINIDAS PARA PRUEBAS ACADEMICAS
# =============================================================================

PRESET_GRAMMARS: dict[str, dict[str, str]] = {
    "Ejemplo 1 (PDF): Expresiones Aritmeticas [Solo SLR(1)]": {
        "grammar": "S -> S+T T\nT -> T*F F\nF -> (S) i",
        "sample_input": "(i+i)*i",
        "description": "Gramatica clasica de expresiones con recursividad izquierda (Seccion 5, Ejemplo 1 de sdt_revised.pdf). Es SLR(1) pero no LL(1).",
    },
    "Ejemplo 2 (PDF): Gramatica Factorizada [LL(1) y SLR(1)]": {
        "grammar": "S -> AB\nA -> aA d\nB -> bBc e",
        "sample_input": "adbc",
        "description": "Gramatica con produccion epsilon (Seccion 5, Ejemplo 2 de sdt_revised.pdf). Cumple tanto LL(1) como SLR(1).",
    },
    "Ejemplo 3 (PDF): Gramatica Ambigua [Ni LL(1) ni SLR(1)]": {
        "grammar": "S -> SS a",
        "sample_input": "aa",
        "description": "Gramatica ambigua y recursiva por la izquierda (Seccion 5, Ejemplo 3 de sdt_revised.pdf). Presenta conflictos en ambas tablas.",
    },
    "Ejercicio 4.6.5 (Aho): Gramatica Solo LL(1) [No SLR(1)]": {
        "grammar": "S -> AaAb BbBa\nA -> e\nB -> e",
        "sample_input": "ab",
        "description": "Ejercicio 4.6.5 del libro de Aho (pag. 258): es LL(1) sin conflictos, pero tiene conflicto reduce/reduce en SLR(1).",
    },
    "Gramatica del Item 3 (SDD): Suma Ponderada con Escala": {
        "grammar": "S -> BR\nR -> +BR e\nB -> ^B 2 3",
        "sample_input": "^2+3",
        "description": "Gramatica original disenada para el Item 3 (SDD). Es tanto LL(1) como SLR(1), tiene 3 no terminales y 6 producciones.",
    },
}


# =============================================================================
# FUNCIONES AUXILIARES DE TABLAS Y GRAFOS GRAPHVIZ
# =============================================================================


def format_lr0_item(item: core.LR0Item) -> str:
    """Formatea un item LR(0) (head, body, dot) con el punto en la posicion correspondiente."""
    head, body, dot = item
    eff = core.effective_body(body)
    with_dot = eff[:dot] + "." + eff[dot:]
    return f"{head} -> {with_dot}"


def build_ll1_dataframe(
    grammar: core.Grammar, ll1_table: core.LL1Table
) -> pd.DataFrame:
    """Construye un DataFrame de la tabla predictiva LL(1) M[A, a]."""
    cols = sorted(grammar.terminals) + [core.ENDMARKER]
    rows: list[dict[str, str]] = []
    for nt in grammar.nonterminals:
        row: dict[str, str] = {"No Terminal": nt}
        for a in cols:
            entries = ll1_table.get((nt, a), [])
            if not entries:
                row[a] = ""
            else:
                row[a] = " | ".join(f"{h} -> {b}" for h, b in entries)
        rows.append(row)
    return pd.DataFrame(rows).set_index("No Terminal")


def build_slr_dataframe(
    grammar: core.Grammar,
    action_table: core.SLRActionTable,
    goto_table: core.SLRGotoTable,
    num_states: int,
    prod_index: dict[tuple[str, str], int],
) -> pd.DataFrame:
    """Construye un DataFrame combinando las tablas ACTION y GOTO SLR(1)."""
    term_cols = sorted(grammar.terminals) + [core.ENDMARKER]
    nt_cols = list(grammar.nonterminals)
    rows: list[dict[str, str]] = []

    for state in range(num_states):
        row: dict[str, str] = {"Estado": f"I_{state}"}
        for a in term_cols:
            acts = action_table.get((state, a), [])
            formatted: list[str] = []
            for act_type, target in acts:
                if act_type == "shift":
                    formatted.append(f"s{target}")
                elif act_type == "reduce":
                    head, body = target
                    p_num = prod_index.get((head, body), 0)
                    formatted.append(f"r{p_num} ({head}->{body})")
                elif act_type == "accept":
                    formatted.append("acc")
            row[f"ACTION[{a}]"] = " / ".join(formatted)

        for nt in nt_cols:
            target_state = goto_table.get((state, nt))
            row[f"GOTO[{nt}]"] = str(target_state) if target_state is not None else ""
        rows.append(row)

    return pd.DataFrame(rows).set_index("Estado")


def render_lr0_automaton(
    collection: list[frozenset[core.LR0Item]],
    transitions: dict[tuple[int, str], int],
) -> graphviz.Digraph:
    """Construye el grafo Graphviz del Automata Canonico LR(0) (Seccion 4.6.2, Fig. 4.31)."""
    dot = graphviz.Digraph(name="LR0_Automaton")
    dot.attr(rankdir="LR", fontname="IBM Plex Sans", bgcolor="#FFFFFF", pad="0.2")
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fillcolor="#F8FAFC",
        color="#182232",
        fontname="IBM Plex Mono",
        fontsize="10",
    )
    dot.attr("edge", fontname="IBM Plex Mono", fontsize="10", color="#334155")

    for idx, item_set in enumerate(collection):
        # Ordenar items colocando primero los de nucleo y luego el resto
        sorted_items = sorted(
            item_set,
            key=lambda it: (
                0 if (it[0] == core.AUGMENTED_START or it[2] > 0) else 1,
                it[0],
                it[1],
                it[2],
            ),
        )
        items_str = "\\l".join(format_lr0_item(it) for it in sorted_items) + "\\l"
        label = f"I_{idx}\\n----------------\\n{items_str}"
        fill = "#EFF6FF" if idx == 0 else "#F8FAFC"
        dot.node(f"I{idx}", label=label, fillcolor=fill)

    for (src, sym), dst in sorted(transitions.items()):
        dot.edge(f"I{src}", f"I{dst}", label=f" {sym} ")

    return dot


def render_parse_tree_graphviz(
    root: core.ParseNode,
    active_vertex: core.DepVertex | None = None,
    evaluated_vertices: set[core.DepVertex] | None = None,
    dep_graph: core.DependencyGraph | None = None,
    show_dep_edges: bool = True,
) -> graphviz.Digraph:
    """Construye el Arbol de Parseo Anotado y (opcionalmente) las aristas de dependencia."""
    dot = graphviz.Digraph(name="Annotated_Parse_Tree")
    dot.attr(rankdir="TB", fontname="IBM Plex Sans", bgcolor="#FFFFFF", pad="0.25")
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="IBM Plex Mono",
        fontsize="10",
    )

    evaluated_vertices = evaluated_vertices or set()
    core.assign_node_ids(root)

    def _visit(node: core.ParseNode) -> None:
        nid = node.node_id
        attr_lines: list[str] = []
        node_is_active = False
        node_has_evaluated = False

        if node.symbol == core.EPSILON:
            label = "e (epsilon)"
            fill = "#F8FAFC"
            border = "#94A3B8"
        else:
            # Mostrar atributos conocidos/evaluados hasta el paso actual
            for attr_name, attr_val in sorted(node.attributes.items()):
                v_key = (nid, attr_name)
                if active_vertex == v_key:
                    node_is_active = True
                    attr_lines.append(f"* {attr_name} = {attr_val} [ACTIVO]")
                elif v_key in evaluated_vertices:
                    node_has_evaluated = True
                    attr_lines.append(f"{attr_name} = {attr_val}")
                else:
                    attr_lines.append(f"{attr_name} = ?")

            header = f"{node.symbol} (nodo #{nid})"
            if attr_lines:
                label = header + "\\n----------------\\n" + "\\n".join(attr_lines)
            else:
                label = header

            if node_is_active:
                fill = "#DBEAFE"
                border = "#1D4ED8"
            elif node_has_evaluated:
                fill = "#F0FDF4"
                border = "#15803D"
            else:
                fill = "#FFFFFF"
                border = "#475569"

        dot.node(
            f"N{nid}",
            label=label,
            fillcolor=fill,
            color=border,
            penwidth="2.2" if node_is_active else "1.2",
        )

        for child in node.children:
            _visit(child)
            dot.edge(
                f"N{nid}",
                f"N{child.node_id}",
                style="dotted" if show_dep_edges else "solid",
                color="#94A3B8" if show_dep_edges else "#334155",
                arrowhead="none",
            )

    _visit(root)

    if show_dep_edges and dep_graph is not None:
        for (u_nid, u_attr), (v_nid, v_attr) in dep_graph.edges:
            is_curr_edge = active_vertex == (v_nid, v_attr)
            dot.edge(
                f"N{u_nid}",
                f"N{v_nid}",
                label=f" {u_attr}->{v_attr} ",
                color="#1D4ED8" if is_curr_edge else "#15803D",
                penwidth="2.0" if is_curr_edge else "1.1",
                style="solid",
                constraint="false",
                fontsize="9",
            )

    return dot


def render_dependency_graph_graphviz(
    dep_graph: core.DependencyGraph,
    eval_order: list[core.DepVertex],
    active_step_idx: int,
    has_cycle: bool = False,
) -> graphviz.Digraph:
    """Construye el Grafo de Dependencias de Atributos (Seccion 5.2.1, Fig. 5.7)."""
    dot = graphviz.Digraph(name="Attribute_Dependency_Graph")
    dot.attr(rankdir="LR", fontname="IBM Plex Sans", bgcolor="#FFFFFF", pad="0.25")
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="IBM Plex Mono",
        fontsize="10",
    )
    dot.attr("edge", fontname="IBM Plex Mono", fontsize="9")

    order_pos = {v: idx + 1 for idx, v in enumerate(eval_order)}
    evaluated_set = set(eval_order[:active_step_idx])
    active_vertex = (
        eval_order[active_step_idx - 1]
        if 1 <= active_step_idx <= len(eval_order)
        else None
    )

    # Identificar vertices en ciclo si has_cycle es True
    in_cycle_vertices = set(dep_graph.vertices) - set(eval_order) if has_cycle else set()

    for nid, attr in dep_graph.vertices:
        v = (nid, attr)
        node_obj = dep_graph.node_map[nid]
        val = node_obj.attributes.get(attr, "?")

        if v in in_cycle_vertices:
            step_tag = "CICLO"
            val_str = "indefinido"
            fill = "#FEF2F2"
            border = "#B91C1C"
            penwidth = "2.2"
        elif v == active_vertex:
            step_tag = f"Paso #{order_pos[v]} [ACTUAL]"
            val_str = str(val)
            fill = "#DBEAFE"
            border = "#1D4ED8"
            penwidth = "2.4"
        elif v in evaluated_set:
            step_tag = f"Paso #{order_pos[v]}"
            val_str = str(val)
            fill = "#F0FDF4"
            border = "#15803D"
            penwidth = "1.4"
        else:
            step_tag = f"Paso #{order_pos.get(v, '?')} (pendiente)"
            val_str = "?"
            fill = "#F8FAFC"
            border = "#94A3B8"
            penwidth = "1.0"

        label = f"{step_tag}\\n{node_obj.symbol}(nodo #{nid}).{attr}\\nvalor = {val_str}"
        dot.node(
            f"V_{nid}_{attr}",
            label=label,
            fillcolor=fill,
            color=border,
            penwidth=penwidth,
        )

    for u, v in dep_graph.edges:
        u_id = f"V_{u[0]}_{u[1]}"
        v_id = f"V_{v[0]}_{v[1]}"
        if has_cycle and u in in_cycle_vertices and v in in_cycle_vertices:
            dot.edge(u_id, v_id, color="#B91C1C", penwidth="2.2", label=" ciclo ")
        elif v == active_vertex:
            dot.edge(u_id, v_id, color="#1D4ED8", penwidth="2.2")
        elif u in evaluated_set and v in evaluated_set:
            dot.edge(u_id, v_id, color="#15803D", penwidth="1.4")
        else:
            dot.edge(u_id, v_id, color="#94A3B8", penwidth="1.0")

    return dot


# =============================================================================
# CABECERA PRINCIPAL Y BARRA LATERAL DE CONFIGURACION DE GRAMATICA
# =============================================================================

st.markdown(
    """
    <div class="main-header">
        <h1>Formal Languages &amp; Compilers — Interactive Workbench</h1>
        <p>
            Conjuntos FIRST/FOLLOW (Seccion 4.4.2) &middot; Analizadores LL(1) y SLR(1) (Secciones 4.4.3–4.6.4)
            &middot; Evaluador General de SDD por Grafo de Dependencias (Secciones 5.1–5.2)
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Configuracion de Gramatica (Items 1 y 2)")
    preset_choice = st.selectbox(
        "Seleccionar gramatica de referencia:",
        options=list(PRESET_GRAMMARS.keys()) + ["Personalizada (Entrada libre)"],
        index=1,
    )

    if preset_choice != "Personalizada (Entrada libre)":
        default_grammar_text = PRESET_GRAMMARS[preset_choice]["grammar"]
        default_sample_str = PRESET_GRAMMARS[preset_choice]["sample_input"]
        st.caption(PRESET_GRAMMARS[preset_choice]["description"])
    else:
        default_grammar_text = "S -> aSb e"
        default_sample_str = "aabb"
        st.caption(
            "Convenciones Seccion 2.2: 'S' es el simbolo inicial, mayusculas son no terminales, "
            "'e' representa epsilon y '$' es el marcador de fin."
        )

    grammar_text = st.text_area(
        "Producciones (una por no terminal, alternativas separadas por espacio):",
        value=default_grammar_text,
        height=135,
    )

    st.markdown("---")
    st.markdown("### Referencia Teorica (Aho et al., 2da Ed.)")
    st.markdown(
        "- **Seccion 4.4.2**: Calculo de `FIRST` y `FOLLOW`\n"
        "- **Algoritmo 4.31**: Tabla predictiva `LL(1)`\n"
        "- **Algoritmo 4.34**: Parser `LL(1)` con pila\n"
        "- **Seccion 4.6.2**: `CLOSURE`, `GOTO` y automata `LR(0)`\n"
        "- **Algoritmo 4.46**: Tablas `ACTION` y `GOTO` `SLR(1)`\n"
        "- **Algoritmo 4.44**: Motor de analisis `LR`\n"
        "- **Secciones 5.1–5.2**: SDD, Grafo de Dependencias y Orden Topologico"
    )

# Parsear la gramatica activa
raw_grammar_lines = [
    ln.strip() for ln in grammar_text.strip().splitlines() if ln.strip()
]
grammar_error: str | None = None
active_grammar: core.Grammar | None = None

try:
    if not raw_grammar_lines:
        grammar_error = "Ingrese al menos una produccion con el formato A -> alt1 alt2."
    else:
        for ln in raw_grammar_lines:
            if "->" not in ln:
                raise ValueError(f"Falta el separador '->' en la linea: {ln}")
        active_grammar = core.parse_grammar_lines(raw_grammar_lines)
except Exception as exc:
    grammar_error = str(exc)

if grammar_error or active_grammar is None:
    st.error(f"Error de formato en la gramatica: {grammar_error}")
    st.stop()

# Calcular FIRST, FOLLOW, tabla LL(1) y tabla SLR(1)
first_sets = core.compute_first_sets(active_grammar)
follow_sets = core.compute_follow_sets(active_grammar, first_sets)
ll1_table, is_ll1 = core.build_ll1_table(active_grammar, first_sets, follow_sets)
slr_action, slr_goto, lr0_collection, is_slr1 = core.build_slr_table(
    active_grammar, follow_sets
)
_, lr0_transitions, aug_prods = core.build_canonical_collection(active_grammar)
prod_index = {prod: idx for idx, prod in enumerate(aug_prods)}


# =============================================================================
# ORGANIZACION EN 3 PESTANAS (st.tabs)
# =============================================================================

tab_grammar, tab_simulator, tab_sdd = st.tabs(
    [
        "1. Analisis Gramatical (Items 1 y 2)",
        "2. Simulador Paso a Paso de Parsing",
        "3. Evaluador Interactivo SDD (Item 3)",
    ]
)


# -----------------------------------------------------------------------------
# PESTANA 1: ANALISIS GRAMATICAL (FIRST, FOLLOW, LL(1), AUTOMATA LR(0), SLR(1))
# -----------------------------------------------------------------------------
with tab_grammar:
    # Resumen de clasificacion segun Seccion 2.2.2
    ll1_badge = (
        '<span class="status-badge badge-ok">LL(1): SI (Sin conflictos)</span>'
        if is_ll1
        else '<span class="status-badge badge-conflict">LL(1): NO (Conflicto M[A,a])</span>'
    )
    slr1_badge = (
        '<span class="status-badge badge-ok">SLR(1): SI (Sin conflictos)</span>'
        if is_slr1
        else '<span class="status-badge badge-conflict">SLR(1): NO (Conflicto ACTION)</span>'
    )

    if is_ll1 and is_slr1:
        case_msg = "Caso 1 (Seccion 2.2.2): Select a parser (T: for LL(1), B: for SLR(1), Q: quit):"
    elif is_ll1 and not is_slr1:
        case_msg = "Caso 2 (Seccion 2.2.2): Grammar is LL(1)."
    elif is_slr1 and not is_ll1:
        case_msg = "Caso 3 (Seccion 2.2.2): Grammar is SLR(1)."
    else:
        case_msg = "Caso 4 (Seccion 2.2.2): Grammar is neither LL(1) nor SLR(1)."

    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">Diagnostico de Clasificacion Gramatical (Seccion 2.2.2)</div>
            <div>{ll1_badge} {slr1_badge}
                <span class="status-badge badge-info">{case_msg}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_sets, col_ll1 = st.columns([1, 1.35])

    with col_sets:
        st.markdown("#### Item 1: Conjuntos FIRST y FOLLOW (Seccion 4.4.2)")
        sets_rows = []
        for nt in sorted(active_grammar.nonterminals):
            sets_rows.append(
                {
                    "No Terminal": nt,
                    "FIRST(A)": core.format_symbol_set(first_sets[nt]),
                    "FOLLOW(A)": core.format_symbol_set(follow_sets[nt]),
                }
            )
        st.dataframe(
            pd.DataFrame(sets_rows).set_index("No Terminal"),
            width="stretch",
        )

        # Salida exacta del flag --sets
        sets_cli_lines = [
            f"First({nt}) = {core.format_symbol_set(first_sets[nt])}"
            for nt in sorted(active_grammar.nonterminals)
        ] + [
            f"Follow({nt}) = {core.format_symbol_set(follow_sets[nt])}"
            for nt in sorted(active_grammar.nonterminals)
        ]
        with st.expander("Ver salida exacta en consola para el flag --sets"):
            st.code("\n".join(sets_cli_lines), language="text")

    with col_ll1:
        st.markdown("#### Item 2 (Parte A): Tabla Predictiva LL(1) (Algoritmo 4.31)")
        df_ll1 = build_ll1_dataframe(active_grammar, ll1_table)

        def _highlight_ll1_conflicts(val: str) -> str:
            if "|" in str(val):
                return "background-color: #FEF2F2; color: #B91C1C; font-weight: 600;"
            if str(val).strip():
                return "background-color: #F8FAFC; color: #182232;"
            return ""

        st.dataframe(
            df_ll1.style.map(_highlight_ll1_conflicts),
            width="stretch",
        )
        if not is_ll1:
            st.caption(
                "Las celdas resaltadas en rojo contienen multiples producciones (conflicto LL(1))."
            )

    st.markdown("---")
    st.markdown(
        "#### Item 2 (Parte B): Coleccion Canonica de Items LR(0) y Tabla SLR(1) (Secciones 4.6.2 y 4.6.4)"
    )

    subtab_automaton, subtab_slr_table, subtab_items = st.tabs(
        [
            "Automata Canonico LR(0) (Graphviz)",
            "Tabla ACTION y GOTO SLR(1)",
            "Detalle de Estados LR(0) y Producciones Numeradas",
        ]
    )

    with subtab_automaton:
        lr0_dot = render_lr0_automaton(lr0_collection, lr0_transitions)
        st.graphviz_chart(lr0_dot.source, width="stretch")

    with subtab_slr_table:
        df_slr = build_slr_dataframe(
            active_grammar,
            slr_action,
            slr_goto,
            len(lr0_collection),
            prod_index,
        )

        def _highlight_slr_conflicts(val: str) -> str:
            if " / " in str(val):
                return "background-color: #FEF2F2; color: #B91C1C; font-weight: 600;"
            if str(val) == "acc":
                return "background-color: #F0FDF4; color: #15803D; font-weight: 600;"
            return ""

        st.dataframe(
            df_slr.style.map(_highlight_slr_conflicts),
            width="stretch",
        )
        if not is_slr1:
            st.caption(
                "Las celdas resaltadas en rojo presentan conflictos shift/reduce o reduce/reduce."
            )

    with subtab_items:
        c_prods, c_states = st.columns([1, 2])
        with c_prods:
            st.markdown("**Gramatica Aumentada Numerada ($G'$):**")
            prod_rows = [
                {"#": i, "Produccion": f"{h} -> {b}"}
                for i, (h, b) in enumerate(aug_prods)
            ]
            st.dataframe(
                pd.DataFrame(prod_rows).set_index("#"),
                width="stretch",
            )
        with c_states:
            st.markdown(f"**Conjuntos de Items LR(0) ({len(lr0_collection)} estados):**")
            state_rows = []
            for idx, item_set in enumerate(lr0_collection):
                sorted_it = sorted(
                    item_set,
                    key=lambda it: (
                        0 if (it[0] == core.AUGMENTED_START or it[2] > 0) else 1,
                        it[0],
                        it[1],
                        it[2],
                    ),
                )
                state_rows.append(
                    {
                        "Estado": f"I_{idx}",
                        "CLOSURE(I)": " ;  ".join(
                            format_lr0_item(it) for it in sorted_it
                        ),
                    }
                )
            st.dataframe(
                pd.DataFrame(state_rows).set_index("Estado"),
                width="stretch",
            )


# -----------------------------------------------------------------------------
# PESTANA 2: SIMULADOR PASO A PASO DE PARSING (LL(1) Y SLR(1))
# -----------------------------------------------------------------------------
with tab_simulator:
    st.markdown(
        "#### Simulador Interactivo Paso a Paso de Analisis Sintactico (Algoritmos 4.34 y 4.44)"
    )

    sim_col1, sim_col2 = st.columns([1.4, 1])
    with sim_col1:
        sim_input = st.text_input(
            "Cadena de entrada w (sin '$'; ingrese 'e' para la cadena vacia):",
            value=default_sample_str,
            key="sim_input_str",
        )
    with sim_col2:
        default_parser_idx = 0 if is_ll1 else 1
        sim_parser_type = st.radio(
            "Algoritmo de Parsing:",
            options=[
                "LL(1) — Predictivo No Recursivo (Seccion 4.4.4)",
                "SLR(1) — Shift-Reduce LR (Seccion 4.6.3)",
            ],
            index=default_parser_idx,
            horizontal=False,
        )

    use_ll1_sim = sim_parser_type.startswith("LL(1)")

    if use_ll1_sim and not is_ll1:
        st.warning(
            "Nota: La gramatica actual NO es LL(1) (existen conflictos en M[A, a]). "
            "El simulador ejecutara la primera entrada de la celda para fines demostrativos."
        )
    if (not use_ll1_sim) and not is_slr1:
        st.warning(
            "Nota: La gramatica actual NO es SLR(1) (existen conflictos en ACTION). "
            "El simulador ejecutara la primera accion registrada en la celda."
        )

    if use_ll1_sim:
        sim_accepted, sim_tree, sim_trace = core.parse_ll1(
            sim_input.strip(), active_grammar, ll1_table
        )
    else:
        sim_accepted, sim_tree, sim_trace = core.parse_slr1(
            sim_input.strip(), slr_action, slr_goto
        )

    total_sim_steps = len(sim_trace)
    sim_state_key = f"sim_step_{preset_choice}_{sim_input}_{use_ll1_sim}"
    if sim_state_key not in st.session_state:
        st.session_state[sim_state_key] = 1

    # Botones de navegacion paso a paso
    btn_c1, btn_c2, btn_c3, btn_c4, slider_col = st.columns([1, 1, 1, 1, 3])
    with btn_c1:
        if st.button("Reiniciar", width="stretch", key="btn_sim_first"):
            st.session_state[sim_state_key] = 1
    with btn_c2:
        if st.button(
            "Paso anterior",
            width="stretch",
            disabled=st.session_state[sim_state_key] <= 1,
            key="btn_sim_prev",
        ):
            st.session_state[sim_state_key] = max(
                1, st.session_state[sim_state_key] - 1
            )
    with btn_c3:
        if st.button(
            "Paso siguiente",
            width="stretch",
            disabled=st.session_state[sim_state_key] >= total_sim_steps,
            key="btn_sim_next",
        ):
            st.session_state[sim_state_key] = min(
                total_sim_steps, st.session_state[sim_state_key] + 1
            )
    with btn_c4:
        if st.button("Ir al final", width="stretch", key="btn_sim_last"):
            st.session_state[sim_state_key] = total_sim_steps
    with slider_col:
        curr_sim_step = st.slider(
            "Paso de la traza:",
            min_value=1,
            max_value=max(1, total_sim_steps),
            value=st.session_state[sim_state_key],
            key=f"slider_{sim_state_key}",
        )
        st.session_state[sim_state_key] = curr_sim_step

    if sim_trace:
        step_info = sim_trace[curr_sim_step - 1]
        verdict_badge = (
            '<span class="status-badge badge-ok">Resultado Final: yes (Cadena Aceptada)</span>'
            if sim_accepted
            else '<span class="status-badge badge-conflict">Resultado Final: no (Cadena Rechazada)</span>'
        )
        st.markdown(
            f'<div style="margin-bottom: 0.75rem;">{verdict_badge} '
            f'<span class="status-badge badge-info">Paso {curr_sim_step} de {total_sim_steps}</span></div>',
            unsafe_allow_html=True,
        )

        if use_ll1_sim:
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown(
                    f'<div class="kv-label">Pila (Tope a la izquierda, Fig. 4.21)</div>'
                    f'<div class="kv-value">{step_info["stack"]}</div>',
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f'<div class="kv-label">Entrada Restante (w$)</div>'
                    f'<div class="kv-value">{step_info["input"]}</div>',
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f'<div class="kv-label">Accion Ejecutada</div>'
                    f'<div class="kv-value">{step_info["action"]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    f'<div class="kv-label">Pila de Estados (Tope a la derecha)</div>'
                    f'<div class="kv-value">{step_info["stack"]}</div>',
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f'<div class="kv-label">Simbolos en Pila (Fig. 4.38)</div>'
                    f'<div class="kv-value">{step_info["symbols"]}</div>',
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f'<div class="kv-label">Entrada Restante (w$)</div>'
                    f'<div class="kv-value">{step_info["input"]}</div>',
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    f'<div class="kv-label">Accion Ejecutada</div>'
                    f'<div class="kv-value">{step_info["action"]}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("##### Tabla Completa de Configuraciones del Parser")
        trace_rows = []
        for idx, item in enumerate(sim_trace, start=1):
            row_data: dict[str, str] = {"Paso": str(idx)}
            if use_ll1_sim:
                row_data["STACK (Tope izq.)"] = item["stack"]
                row_data["INPUT"] = item["input"]
                row_data["ACTION"] = item["action"]
            else:
                row_data["STACK (Estados)"] = item["stack"]
                row_data["SYMBOLS"] = item["symbols"]
                row_data["INPUT"] = item["input"]
                row_data["ACTION"] = item["action"]
            trace_rows.append(row_data)

        df_trace = pd.DataFrame(trace_rows).set_index("Paso")

        def _highlight_active_row(row: pd.Series) -> list[str]:
            if row.name == str(curr_sim_step):
                return [
                    "background-color: #DBEAFE; color: #1E3A8A; font-weight: 600;"
                ] * len(row)
            return [""] * len(row)

        st.dataframe(
            df_trace.style.apply(_highlight_active_row, axis=1),
            width="stretch",
        )


# -----------------------------------------------------------------------------
# PESTANA 3: EVALUADOR INTERACTIVO SDD (ITEM 3, SECCIONES 5.1 Y 5.2)
# -----------------------------------------------------------------------------
with tab_sdd:
    st.markdown(
        "#### Item 3: Definicion Dirigida por la Sintaxis (SDD) y Evaluacion por Orden Topologico"
    )

    sdd_top_c1, sdd_top_c2, sdd_top_c3 = st.columns([1.2, 1.3, 1.2])
    with sdd_top_c1:
        sdd_mode = st.radio(
            "Configuracion de Reglas Semanticas:",
            options=[
                "SDD Aciclica Oficial (Pasos 1-5)",
                "SDD Circular (Prueba de Ciclo del Paso 6)",
            ],
            index=0,
        )
    is_circular_mode = sdd_mode.startswith("SDD Circular")

    with sdd_top_c2:
        preset_sdd_strings = {
            "^2+3 (Ejemplo de 4 terminales del Paso 3 -> S.val = 10)": "^2+3",
            "2 (Cadena mas corta del lenguaje -> S.val = 2)": "2",
            "^^3+^2+3 (Anidamiento y recursion profunda -> S.val = 29)": "^^3+^2+3",
            "2+3+2 (Suma multiple con desplazamiento de escala -> S.val = 14)": "2+3+2",
            "^3+^^2 (Combinacion de prefijos -> S.val = 22)": "^3+^^2",
            "2++3 (Cadena invalida fuera del lenguaje -> no)": "2++3",
            "Entrada personalizada": "",
        }
        chosen_sdd_sample = st.selectbox(
            "Casos de prueba del Paso 6:",
            options=list(preset_sdd_strings.keys()),
            index=0,
        )

    with sdd_top_c3:
        default_sdd_str = (
            preset_sdd_strings[chosen_sdd_sample]
            if chosen_sdd_sample != "Entrada personalizada"
            else "^2+3"
        )
        sdd_input_str = st.text_input(
            "Cadena a evaluar en la SDD:",
            value=default_sdd_str,
        )

    sdd_instance = core.build_default_sdd(circular=is_circular_mode)

    with st.expander(
        "Ver Especificacion Formal de la Gramatica G_SDD, Tabla de Atributos y Reglas Semanticas (Paso 2)",
        expanded=False,
    ):
        spec_c1, spec_c2 = st.columns([1, 1.35])
        with spec_c1:
            st.markdown("**Tabla de Atributos (Paso 2.1):**")
            attr_table = pd.DataFrame(
                [
                    {
                        "Simbolo": "S",
                        "Atributo": "val",
                        "Clase": "Sintetizado",
                        "Tipo": "int",
                        "Significado": "Valor total ponderado de la expresion (S no tiene atributos heredados).",
                    },
                    {
                        "Simbolo": "B, R",
                        "Atributo": "scale",
                        "Clase": "Heredado",
                        "Tipo": "int",
                        "Significado": "Factor de escala posicional/jerarquico recibido del contexto padre/hermano.",
                    },
                    {
                        "Simbolo": "B, R",
                        "Atributo": "val",
                        "Clase": "Sintetizado",
                        "Tipo": "int",
                        "Significado": "Valor numerico ponderado calculado para el subarbol de B o la lista R.",
                    },
                    {
                        "Simbolo": "2, 3, +, ^",
                        "Atributo": "lexval",
                        "Clase": "Sintetizado (Scanner)",
                        "Tipo": "str",
                        "Significado": "Caracter literal del terminal provisto directamente por el analizador lexico.",
                    },
                ]
            )
            st.dataframe(attr_table.set_index("Simbolo"), width="stretch")

        with spec_c2:
            st.markdown("**Reglas Semanticas por Produccion (Formato Fig. 5.1 de Aho):**")
            rule_rows = []
            for prod_head, prod_body in sdd_instance.grammar.production_list:
                p_rules = sdd_instance.rules_by_production.get(
                    (prod_head, prod_body), []
                )
                rule_rows.append(
                    {
                        "Produccion": f"{prod_head} -> {prod_body}",
                        "Reglas Semanticas (Datos en SDD)": " ;  ".join(
                            r.description for r in p_rules
                        ),
                    }
                )
            st.dataframe(
                pd.DataFrame(rule_rows).set_index("Produccion"),
                width="stretch",
            )

    # Parsear la cadena con nuestro parser LL(1) del Item 2 y evaluar la SDD
    sdd_first = core.compute_first_sets(sdd_instance.grammar)
    sdd_follow = core.compute_follow_sets(sdd_instance.grammar, sdd_first)
    sdd_ll1_table, _ = core.build_ll1_table(
        sdd_instance.grammar, sdd_first, sdd_follow
    )

    sdd_accepted, sdd_root, _ = core.parse_ll1(
        sdd_input_str.strip(), sdd_instance.grammar, sdd_ll1_table
    )

    if not sdd_accepted or sdd_root is None:
        st.markdown(
            f"""
            <div class="step-box-error">
                <strong>Cadena rechazada por el parser:</strong> La cadena
                <code>{sdd_input_str}</code> no pertenece al lenguaje generado por <code>G_SDD</code>.
                Salida de <code>main.py --sdd</code>: <code>no</code>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        ok_eval, dep_graph, eval_order = core.evaluate_sdd_on_tree(
            sdd_root, sdd_instance
        )

        if not ok_eval:
            st.markdown(
                """
                <div class="step-box-error">
                    <strong>Deteccion de SDD Circular (Seccion 5.2.2 / Paso 5.4 y Paso 6):</strong><br/>
                    El algoritmo de ordenamiento topologico detecto un ciclo dirigido en el grafo de dependencias:
                    <code>B(nodo #2).scale -&gt; B(nodo #2).val -&gt; S(nodo #1).val -&gt; B(nodo #2).scale</code>.<br/>
                    Salida exacta del evaluador: <code>Error: SDD is circular (cycle detected in dependency graph).</code>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cyc_dot = render_dependency_graph_graphviz(
                dep_graph, eval_order, len(eval_order), has_cycle=True
            )
            st.graphviz_chart(cyc_dot.source, width="stretch")
        else:
            total_attr_steps = len(eval_order)
            sdd_step_key = f"sdd_step_{sdd_input_str}_{is_circular_mode}"
            if sdd_step_key not in st.session_state:
                st.session_state[sdd_step_key] = total_attr_steps

            c_b1, c_b2, c_b3, c_b4, c_sl = st.columns([1, 1, 1, 1, 3])
            with c_b1:
                if st.button(
                    "Paso 1", width="stretch", key="btn_sdd_first"
                ):
                    st.session_state[sdd_step_key] = 1
            with c_b2:
                if st.button(
                    "Atributo anterior",
                    width="stretch",
                    disabled=st.session_state[sdd_step_key] <= 1,
                    key="btn_sdd_prev",
                ):
                    st.session_state[sdd_step_key] = max(
                        1, st.session_state[sdd_step_key] - 1
                    )
            with c_b3:
                if st.button(
                    "Atributo siguiente",
                    width="stretch",
                    disabled=st.session_state[sdd_step_key] >= total_attr_steps,
                    key="btn_sdd_next",
                ):
                    st.session_state[sdd_step_key] = min(
                        total_attr_steps, st.session_state[sdd_step_key] + 1
                    )
            with c_b4:
                if st.button(
                    "Evaluacion completa",
                    width="stretch",
                    key="btn_sdd_last",
                ):
                    st.session_state[sdd_step_key] = total_attr_steps
            with c_sl:
                curr_attr_step = st.slider(
                    "Paso del Orden Topologico:",
                    min_value=1,
                    max_value=total_attr_steps,
                    value=st.session_state[sdd_step_key],
                    key=f"slider_{sdd_step_key}",
                )
                st.session_state[sdd_step_key] = curr_attr_step

            active_v = eval_order[curr_attr_step - 1]
            evaluated_v_set = set(eval_order[:curr_attr_step])
            act_nid, act_attr = active_v
            act_node = dep_graph.node_map[act_nid]
            act_val = act_node.attributes.get(act_attr)

            if active_v in dep_graph.vertex_rules:
                rule_obj, dep_vs = dep_graph.vertex_rules[active_v]
                rule_desc = rule_obj.description
                if dep_vs:
                    deps_str = ", ".join(
                        f"{dep_graph.node_map[dn].symbol}(nodo #{dn}).{da} = "
                        f"{dep_graph.node_map[dn].attributes[da]}"
                        for dn, da in dep_vs
                    )
                else:
                    deps_str = "Constante inicial (sin dependencias previas)"
            else:
                rule_desc = f"{act_node.symbol}.lexval = '{act_val}' (Provisto por el scanner)"
                deps_str = "Hoja terminal"

            st.markdown(
                f"""
                <div class="step-box">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                        <div>
                            <span class="status-badge badge-info">Orden Topologico: Paso {curr_attr_step} / {total_attr_steps}</span>
                            <span class="status-badge badge-ok">Atributo Evaluado: {act_node.symbol}(nodo #{act_nid}).{act_attr} = {act_val}</span>
                        </div>
                        <div>
                            <strong>Resultado Final S.val = {sdd_root.attributes['val']}</strong>
                        </div>
                    </div>
                    <div style="margin-top:0.55rem; font-size:0.9rem; color:#334155;">
                        <strong>Regla semantica aplicada:</strong> <code>{rule_desc}</code>
                        &nbsp;&middot;&nbsp; <strong>Entradas usadas:</strong> <code>{deps_str}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            show_overlay = st.checkbox(
                "Superponer aristas del Grafo de Dependencias sobre el Arbol de Parseo (Estilo Fig. 5.7 de Aho)",
                value=True,
            )

            vis_c1, vis_c2 = st.columns([1.05, 1.15])
            with vis_c1:
                st.markdown("##### Arbol de Analisis Sintactico Anotado (Seccion 5.1.2)")
                tree_dot = render_parse_tree_graphviz(
                    sdd_root,
                    active_vertex=active_v,
                    evaluated_vertices=evaluated_v_set,
                    dep_graph=dep_graph,
                    show_dep_edges=show_overlay,
                )
                st.graphviz_chart(tree_dot.source, width="stretch")

            with vis_c2:
                st.markdown(
                    "##### Grafo de Dependencias y Orden Topologico (Secciones 5.2.1–5.2.2)"
                )
                dep_dot = render_dependency_graph_graphviz(
                    dep_graph,
                    eval_order,
                    active_step_idx=curr_attr_step,
                    has_cycle=False,
                )
                st.graphviz_chart(dep_dot.source, width="stretch")

            out_c1, out_c2 = st.columns(2)
            with out_c1:
                st.markdown("##### Salida de Consola: Arbol Anotado Indentado")
                st.code(core.format_annotated_tree(sdd_root), language="text")
            with out_c2:
                st.markdown("##### Salida de Consola: Secuencia de Evaluacion Topologica")
                order_lines = [
                    f"{i}. {dep_graph.node_map[nid].symbol}(node {nid}).{attr} = "
                    f"{dep_graph.node_map[nid].attributes[attr]}"
                    for i, (nid, attr) in enumerate(eval_order, start=1)
                ]
                order_lines.append(
                    f"\nValor principal del simbolo inicial: S.val = {sdd_root.attributes['val']}"
                )
                st.code("\n".join(order_lines), language="text")
