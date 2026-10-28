#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
latex_to_pdf.py
Высококачественный экспорт документов LaTeX (по стандарту БГУИР СТП 01-2017/2024) в формат PDF:
- Точные параметры СТП: поля 30/15/20/20 мм, шрифт Times New Roman 14 pt, абзацный отступ 1.25 см.
- Форматирование кода: строго шрифт Courier New 13 pt, одинарный межстрочный интервал (1.0),
  БЕЗ рамок и БЕЗ фоновых заливок (border: none, background: transparent).
- Нумерация рисунков: строго по СТП 2.5.5 («Рисунок 1 – Название», по центру, без точки в конце).
- Нумерация таблиц: строго по СТП 2.6.2 («Таблица 1 – Название», по левому краю без отступа, без точки в конце).
- Математические формулы: векторный MathML (через latex2mathml) с нативным рендерингом в Edge / Chromium
  и поддержкой кириллических индексов, плюс фоллбек на matplotlib mathtext SVG.
- Нумерация формул: номер в круглых скобках (1), (2) строго у правого края строки (СТП 2.4.7).
- Постраничная векторная нумерация со 2-й страницы в правом нижнем углу (10 мм от края) через reportlab + pypdf.
"""

import os
import sys
import re
import io
import base64
import html as html_lib
import shutil
import argparse
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pypdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# Попытка импорта latex2mathml
try:
    import latex2mathml.converter
    HAS_LATEX2MATHML = True
except ImportError:
    HAS_LATEX2MATHML = False

import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams['mathtext.fontset'] = 'stix'
matplotlib.rcParams['font.family'] = 'STIXGeneral'

def find_edge_path():
    """Находит исполняемый файл Microsoft Edge на Windows."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge.exe") or ""
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None

def math_to_svg_data(formula_str: str, fontsize: int = 14) -> str:
    """Рендерит формулу LaTeX в векторный SVG Data URI через matplotlib.mathtext (шрифт STIX)."""
    f_clean = formula_str.strip()
    if f_clean.startswith('$$') and f_clean.endswith('$$'):
        f_clean = f_clean[2:-2].strip()
    elif f_clean.startswith('$') and f_clean.endswith('$'):
        f_clean = f_clean[1:-1].strip()

    f_clean = f_clean.replace(r'\quad', ' ')
    f_clean = f_clean.replace(r'\,', ' ')

    try:
        fig = plt.figure(dpi=300)
        text = fig.text(0, 0, f'${f_clean}$', fontsize=fontsize, ha='left', va='bottom')
        fig.canvas.draw()
        bbox = text.get_window_extent()
        width_in = max(0.2, (bbox.width + 10) / 300.0)
        height_in = max(0.15, (bbox.height + 8) / 300.0)
        fig.set_size_inches(width_in, height_in)

        buf = io.BytesIO()
        plt.savefig(buf, format='svg', bbox_inches='tight', transparent=True, pad_inches=0.01)
        plt.close(fig)

        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/svg+xml;base64,{b64}"
    except Exception:
        plt.close('all')
        return ""

def render_math_to_html(formula_str: str, is_block: bool = False) -> str:
    """
    Преобразует математическую формулу LaTeX в HTML:
    Приоритет 1: Native MathML (latex2mathml) - идеальное типографическое качество в Edge,
    поддержка кириллицы, выравнивание по базовой линии.
    Приоритет 2: Векторный SVG через matplotlib.mathtext.
    """
    f_clean = formula_str.strip()
    if f_clean.startswith('$$') and f_clean.endswith('$$'):
        f_clean = f_clean[2:-2].strip()
    elif f_clean.startswith('$') and f_clean.endswith('$'):
        f_clean = f_clean[1:-1].strip()

    if HAS_LATEX2MATHML:
        try:
            mathml = latex2mathml.converter.convert(f_clean)
            if not is_block:
                # Для инлайн-математики используем display inline
                mathml = mathml.replace('display="inline"', 'display="inline" class="inline-math"')
            return mathml
        except Exception:
            pass

    # Фоллбек на SVG
    svg_data = math_to_svg_data(f_clean, fontsize=15 if is_block else 13)
    if svg_data:
        if is_block:
            return f'<img class="equation-svg" src="{svg_data}" alt="{html_lib.escape(f_clean)}">'
        else:
            return f'<img class="inline-math" src="{svg_data}" alt="{html_lib.escape(f_clean)}">'

    return f'<em>{html_lib.escape(f_clean)}</em>'

def render_inline_math(text: str) -> str:
    """Находит все $$...$$ и $...$ в тексте и преобразует их в MathML / SVG."""
    def repl_block(match):
        formula = match.group(1)
        res = render_math_to_html(formula, is_block=True)
        return f'<div class="equation-row"><div class="equation-math">{res}</div></div>'

    text = re.sub(r'\$\$([^\$]+?)\$\$', repl_block, text)

    def repl_inline(match):
        formula = match.group(1)
        return render_math_to_html(formula, is_block=False)

    return re.sub(r'\$([^\$\n]+?)\$', repl_inline, text)

def clean_latex_text(text: str, label_map: dict = None) -> str:
    """Преобразует команды LaTeX в HTML с разрешением перекрестных ссылок \ref{}."""
    if not text:
        return ""

    # Разрешение ссылок \ref{...}
    if label_map:
        def ref_repl(m):
            lbl = m.group(1)
            return str(label_map.get(lbl, lbl))
        text = re.sub(r'\\ref\{([^}]+)\}', ref_repl, text)

    # Разрыв строки \\[12pt]
    text = re.sub(r'\\\\(?:\[[^\]]*\])?', '<br>', text)
    # <<текст>> или ``текст'' в кавычки «...»
    text = text.replace('<<', '«').replace('>>', '»')
    text = re.sub(r"``([^'']*)''", r'«\1»', text)
    text = text.replace(r'\,', '&nbsp;').replace('~', '&nbsp;')
    # Жирный и курсив
    text = re.sub(r'\\textbf\{([^}]+)\}', r'<strong>\1</strong>', text)
    text = re.sub(r'\\textit\{([^}]+)\}', r'<em>\1</em>', text)
    text = re.sub(r'\\texttt\{([^}]+)\}', r'<code>\1</code>', text)
    # Тире
    text = text.replace('---', '—').replace('--', '–')
    # Разрывы страниц LaTeX
    text = re.sub(r'\\(?:clearpage|newpage|pagebreak)\b', '', text)
    # Спецсимволы
    text = text.replace(r'\%', '%').replace(r'\&', '&').replace(r'\_', '_')
    # Инлайн формулы
    text = render_inline_math(text)
    return text

def parse_latex_document(tex_path: Path):
    """Парсит документ main.tex отчета БГУИР в структурированные данные."""
    raw_content = tex_path.read_text(encoding="utf-8")
    project_dir = tex_path.parent

    data = {
        "title": {},
        "sections": [],
        "labels": {}
    }

    fields = [
        "stpFaculty", "stpDepartment", "stpSubject", "stpLabNumber",
        "stpLabTopic", "stpVariant", "stpStudent", "stpGroup",
        "stpTeacher", "stpTeacherRole", "stpCity", "stpYear"
    ]
    for f in fields:
        m = re.search(r'\\' + f + r'\{([^}]+)\}', raw_content)
        if m:
            data["title"][f] = m.group(1).strip()

    doc_body_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', raw_content, re.DOTALL)
    body = doc_body_match.group(1) if doc_body_match else raw_content

    # Предварительный проход для сбора меток (labels) рисунков, таблиц и формул
    fig_idx = 1
    for m in re.finditer(r'\\begin\{figure\}.*?\\caption\{.*?\}.*?\\label\{([^}]+)\}.*?\\end\{figure\}', body, re.DOTALL):
        data["labels"][m.group(1)] = fig_idx
        fig_idx += 1

    table_idx = 1
    for m in re.finditer(r'\\begin\{table\}.*?\\caption\{.*?\}.*?\\label\{([^}]+)\}.*?\\end\{table\}', body, re.DOTALL):
        data["labels"][m.group(1)] = table_idx
        table_idx += 1

    section_splits = re.split(r'\\(?:section\*?|anonsection)\{([^}]+)\}', body)

    sec_num = 1
    for i in range(1, len(section_splits), 2):
        sec_title = section_splits[i].strip()
        sec_content = section_splits[i+1].strip() if i+1 < len(section_splits) else ""

        parsed_items = parse_section_content(sec_content, project_dir, data["labels"])
        data["sections"].append({
            "number": sec_num,
            "title": sec_title,
            "items": parsed_items
        })
        sec_num += 1

    return data

def parse_section_content(content: str, project_dir: Path, label_map: dict):
    """Парсит элементы внутри секции (текст, код, рисунки, таблицы, списки, формулы)."""
    items = []
    lines = content.split('\n')
    idx = 0

    while idx < len(lines):
        line = lines[idx].strip()
        if not line or line.startswith('%') or line.startswith(r'\clearpage') or line.startswith(r'\newpage') or line.startswith(r'\pagebreak'):
            idx += 1
            continue

        # 1. Включение файла с кодом: \lstinputlisting[...]{path}
        m_lstinput = re.match(r'\\lstinputlisting(?:\[([^\]]*)\])?\{([^}]+)\}', line)
        if m_lstinput:
            opts = m_lstinput.group(1) or ""
            code_rel = m_lstinput.group(2).strip()
            code_file = project_dir / code_rel

            cap_match = re.search(r'caption=\{?([^,\]\}]+)\}?', opts)
            caption = cap_match.group(1) if cap_match else ""

            code_text = ""
            if code_file.exists():
                code_text = code_file.read_text(encoding="utf-8")

            items.append({
                "type": "code",
                "code": code_text,
                "caption": caption
            })
            idx += 1
            continue

        # 2. Блок листинга: \begin{lstlisting}... \end{lstlisting}
        if line.startswith(r'\begin{lstlisting}'):
            opts_match = re.match(r'\\begin\{lstlisting\}(?:\[([^\]]*)\])?', line)
            opts = opts_match.group(1) if opts_match else ""
            cap_match = re.search(r'caption=\{?([^,\]\}]+)\}?', opts)
            caption = cap_match.group(1) if cap_match else ""

            code_lines = []
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith(r'\end{lstlisting}'):
                code_lines.append(lines[idx])
                idx += 1
            idx += 1
            items.append({
                "type": "code",
                "code": "\n".join(code_lines),
                "caption": caption
            })
            continue

        # 3. Блок рисунка: \begin{figure}... \end{figure}
        if line.startswith(r'\begin{figure}'):
            fig_lines = []
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith(r'\end{figure}'):
                fig_lines.append(lines[idx])
                idx += 1
            idx += 1
            fig_text = "\n".join(fig_lines)

            img_match = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', fig_text)
            cap_match = re.search(r'\\caption\{([^}]+)\}', fig_text)
            lbl_match = re.search(r'\\label\{([^}]+)\}', fig_text)

            img_rel = img_match.group(1) if img_match else ""
            caption = cap_match.group(1) if cap_match else ""
            label = lbl_match.group(1) if lbl_match else ""

            img_file = project_dir / img_rel
            img_b64 = ""
            if img_file.exists():
                with open(img_file, "rb") as f:
                    mime = "image/png" if img_file.suffix.lower() == ".png" else "image/jpeg"
                    img_b64 = f"data:{mime};base64," + base64.b64encode(f.read()).decode("utf-8")

            items.append({
                "type": "figure",
                "img_b64": img_b64,
                "caption": clean_latex_text(caption, label_map),
                "label": label
            })
            continue

        # 4. Блок таблицы: \begin{table}... \end{table} или \begin{tabular}
        if line.startswith(r'\begin{table}'):
            tab_lines = []
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith(r'\end{table}'):
                tab_lines.append(lines[idx])
                idx += 1
            idx += 1
            tab_text = "\n".join(tab_lines)

            cap_match = re.search(r'\\caption\{([^}]+)\}', tab_text)
            lbl_match = re.search(r'\\label\{([^}]+)\}', tab_text)
            caption = cap_match.group(1) if cap_match else ""
            label = lbl_match.group(1) if lbl_match else ""

            tabular_rows = parse_tabular_content(tab_text, label_map)
            items.append({
                "type": "table",
                "caption": clean_latex_text(caption, label_map),
                "label": label,
                "rows": tabular_rows
            })
            continue

        if line.startswith(r'\begin{tabular}'):
            tab_lines = [line]
            idx += 1
            while idx < len(lines):
                tab_lines.append(lines[idx])
                if lines[idx].strip().startswith(r'\end{tabular}'):
                    break
                idx += 1
            idx += 1
            tab_text = "\n".join(tab_lines)
            tabular_rows = parse_tabular_content(tab_text, label_map)
            items.append({
                "type": "table",
                "caption": "",
                "label": "",
                "rows": tabular_rows
            })
            continue

        # 5. Нумерованный список \begin{enumerate}... \end{enumerate}
        if line.startswith(r'\begin{enumerate}'):
            list_items = []
            current_start = 1
            if items and items[-1].get("type") == "enumerate":
                prev_enum = items[-1]
                current_start = prev_enum.get("start", 1) + len(prev_enum.get("items", []))
            elif len(items) >= 2 and items[-1].get("type") == "itemize" and items[-2].get("type") == "enumerate":
                prev_enum = items[-2]
                current_start = prev_enum.get("start", 1) + len(prev_enum.get("items", []))

            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith(r'\end{enumerate}'):
                l_str = lines[idx].strip()
                if l_str.startswith(r'\begin{itemize}'):
                    nested_items = []
                    idx += 1
                    while idx < len(lines) and not lines[idx].strip().startswith(r'\end{itemize}'):
                        n_str = lines[idx].strip()
                        if n_str.startswith(r'\item'):
                            nested_items.append(clean_latex_text(n_str[5:].strip(), label_map))
                        elif nested_items and not n_str.startswith('%'):
                            nested_items[-1] += " " + clean_latex_text(n_str, label_map)
                        idx += 1
                    if idx < len(lines):
                        idx += 1
                    if nested_items:
                        ul_html = "<ul>" + "".join(f"<li>{x}</li>" for x in nested_items) + "</ul>"
                        if list_items:
                            list_items[-1] += ul_html
                        else:
                            list_items.append(ul_html)
                    continue
                elif l_str.startswith(r'\begin{table}'):
                    if list_items:
                        items.append({
                            "type": "enumerate",
                            "start": current_start,
                            "items": list_items
                        })
                        current_start += len(list_items)
                        list_items = []
                    tab_lines = []
                    while idx < len(lines) and not lines[idx].strip().startswith(r'\end{table}'):
                        tab_lines.append(lines[idx])
                        idx += 1
                    if idx < len(lines):
                        tab_lines.append(lines[idx])
                        idx += 1
                    tab_text = "\n".join(tab_lines)
                    cap_match = re.search(r'\\caption\{([^}]+)\}', tab_text)
                    lbl_match = re.search(r'\\label\{([^}]+)\}', tab_text)
                    items.append({
                        "type": "table",
                        "caption": clean_latex_text(cap_match.group(1) if cap_match else "", label_map),
                        "label": lbl_match.group(1) if lbl_match else "",
                        "rows": parse_tabular_content(tab_text, label_map)
                    })
                    continue
                elif l_str.startswith(r'\item'):
                    list_items.append(clean_latex_text(l_str[5:].strip(), label_map))
                elif list_items and not l_str.startswith('%'):
                    list_items[-1] += " " + clean_latex_text(l_str, label_map)
                idx += 1
            idx += 1
            if list_items:
                items.append({
                    "type": "enumerate",
                    "start": current_start,
                    "items": list_items
                })
            continue

        # 6. Маркированный список \begin{itemize}... \end{itemize}
        if line.startswith(r'\begin{itemize}'):
            list_items = []
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith(r'\end{itemize}'):
                l_str = lines[idx].strip()
                if l_str.startswith(r'\begin{enumerate}'):
                    nested_items = []
                    idx += 1
                    while idx < len(lines) and not lines[idx].strip().startswith(r'\end{enumerate}'):
                        n_str = lines[idx].strip()
                        if n_str.startswith(r'\item'):
                            nested_items.append(clean_latex_text(n_str[5:].strip(), label_map))
                        elif nested_items and not n_str.startswith('%'):
                            nested_items[-1] += " " + clean_latex_text(n_str, label_map)
                        idx += 1
                    if idx < len(lines):
                        idx += 1
                    if nested_items:
                        ol_html = "<ol>" + "".join(f"<li>{x}</li>" for x in nested_items) + "</ol>"
                        if list_items:
                            list_items[-1] += ol_html
                        else:
                            list_items.append(ol_html)
                    continue
                elif l_str.startswith(r'\item'):
                    list_items.append(clean_latex_text(l_str[5:].strip(), label_map))
                elif list_items and not l_str.startswith('%'):
                    list_items[-1] += " " + clean_latex_text(l_str, label_map)
                idx += 1
            idx += 1
            items.append({
                "type": "itemize",
                "items": list_items
            })
            continue


        # 7. Выделенная формула: \begin{equation}... или $$...$$
        if line.startswith(r'\begin{equation}') or line.startswith('$$'):
            eq_lines = [line]
            if line.startswith('$$') and line.endswith('$$') and len(line) > 2:
                eq_text = line
            else:
                idx += 1
                while idx < len(lines):
                    eq_lines.append(lines[idx])
                    if lines[idx].strip().startswith(r'\end{equation}') or lines[idx].strip().endswith('$$'):
                        break
                    idx += 1
                eq_text = "\n".join(eq_lines)
            idx += 1

            clean_eq = re.sub(r'\\begin\{equation\*?\}|\\end\{equation\*?\}|\$\$', '', eq_text).strip()
            items.append({
                "type": "equation",
                "formula": clean_eq
            })
            continue

        # 8. Обычный абзац текста
        para_lines = [line]
        idx += 1
        while idx < len(lines):
            next_l = lines[idx].strip()
            if not next_l or next_l.startswith('%') or next_l.startswith(r'\begin{') or next_l.startswith(r'\lstinput') or next_l.startswith('$$'):
                break
            para_lines.append(next_l)
            idx += 1

        full_para = " ".join(para_lines)
        items.append({
            "type": "paragraph",
            "text": clean_latex_text(full_para, label_map)
        })

    return items

def parse_tabular_content(tab_text: str, label_map: dict):
    """Парсит строки и ячейки tabular в массив для генерации HTML-таблицы."""
    match = re.search(r'\\begin\{tabular\}\{([^}]+)\}(.*?)\\end\{tabular\}', tab_text, re.DOTALL)
    if not match:
        return []
    body = match.group(2)
    rows = []
    for r in re.split(r'\\\\', body):
        r_clean = r.replace(r'\hline', '').strip()
        if not r_clean:
            continue
        cells = [clean_latex_text(c.strip(), label_map) for c in r_clean.split('&')]
        rows.append(cells)
    return rows

def render_html_report(data: dict):
    """
    Генерирует высококачественный чистый HTML с точными стилями СТП 01-2017/2024:
    - Поля: 30/15/20/20 мм.
    - Текст: Times New Roman 14 pt, одинарный интервал, отступ 1.25 см.
    - Код: Courier New 13 pt, одинарный интервал, БЕЗ рамок и БЕЗ фона.
    - Рисунки: по центру, подпись «Рисунок N – Название» без точки в конце.
    - Таблицы: по левому краю таблицы без отступа, заголовок «Таблица N – Название» без точки в конце.
    - Формулы: векторные MathML / SVG, номер (N) строго у правого края листа.
    """
    tp = data["title"]
    faculty = tp.get("stpFaculty", "Факультет компьютерных систем и сетей")
    dept = tp.get("stpDepartment", "Кафедра программного обеспечения информационных технологий")
    subject = tp.get("stpSubject", "Основы алгоритмизации и программирования")
    lab_num = tp.get("stpLabNumber", "1")
    lab_topic = tp.get("stpLabTopic", "Исследование алгоритмических структур")
    variant = tp.get("stpVariant", "1")
    student = tp.get("stpStudent", "Иванов И. И.")
    group = tp.get("stpGroup", "150501")
    teacher_role = tp.get("stpTeacherRole", "старший преподаватель")
    teacher = tp.get("stpTeacher", "Петров П. П.")
    city = tp.get("stpCity", "Минск")
    year = tp.get("stpYear", "2026")

    # Глобальные счетчики документов СТП
    fig_counter = 0
    table_counter = 0
    eq_counter = 0
    code_counter = 0

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='ru'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Отчет по лабораторной работе</title>",
        "<style>",
        "@page {",
        "  size: A4 portrait;",
        "  margin-left: 30mm;",
        "  margin-right: 15mm;",
        "  margin-top: 20mm;",
        "  margin-bottom: 20mm;",
        "}",
        "body {",
        "  font-family: 'Times New Roman', serif;",
        "  font-size: 14pt;",
        "  line-height: 1.0;",
        "  color: #000000;",
        "  background-color: #ffffff;",
        "  margin: 0;",
        "  padding: 0;",
        "}",
        ".title-page {",
        "  min-height: 250mm;",
        "  display: flex;",
        "  flex-direction: column;",
        "  justify-content: space-between;",
        "  page-break-after: always;",
        "}",
        ".title-header {",
        "  text-align: center;",
        "  font-size: 12pt;",
        "  line-height: 1.2;",
        "}",
        ".title-center {",
        "  text-align: center;",
        "  margin: 45pt 0;",
        "}",
        ".title-main {",
        "  font-size: 14pt;",
        "  font-weight: bold;",
        "  line-height: 1.3;",
        "}",
        ".title-sign-block {",
        "  margin-left: auto;",
        "  width: 35%;",
        "  text-align: left;",
        "  font-size: 14pt;",
        "  line-height: 1.25;",
        "}",
        ".title-footer {",
        "  text-align: center;",
        "  font-size: 14pt;",
        "  margin-top: 35pt;",
        "}",
        ".section-title {",
        "  break-before: page;",
        "  page-break-before: always;",
        "  font-size: 14pt;",
        "  font-weight: bold;",
        "  text-transform: uppercase;",
        "  text-align: left;",
        "  text-indent: 1.25cm;",
        "  margin-top: 0;",
        "  margin-bottom: 18pt;",
        "  page-break-after: avoid;",
        "}",
        "p {",
        "  text-align: justify;",
        "  text-indent: 1.25cm;",
        "  margin: 0 0 0 0;",
        "  line-height: 1.15;",
        "}",
        "ol, ul {",
        "  margin: 6pt 0 6pt 1.25cm;",
        "  padding-left: 0;",
        "  line-height: 1.15;",
        "}",
        "li {",
        "  text-align: justify;",
        "  margin-bottom: 3pt;",
        "}",
        "ul { list-style-type: '– '; }",
        "/* Формат кода строго по СТП и требованиям: Courier New 13 pt, одинарный интервал, БЕЗ рамок */",
        ".code-block {",
        "  font-family: 'Courier New', monospace;",
        "  font-size: 13pt;",
        "  line-height: 1.0;",
        "  text-indent: 0;",
        "  margin: 14pt 0;",
        "  white-space: pre-wrap;",
        "  word-break: break-all;",
        "  background: transparent;",
        "  border: none;",
        "  padding: 0;",
        "  page-break-inside: auto;",
        "}",
        ".code-caption {",
        "  font-weight: bold;",
        "  font-size: 14pt;",
        "  text-indent: 1.25cm;",
        "  margin-top: 14pt;",
        "  margin-bottom: 6pt;",
        "}",
        "/* Иллюстрации строго по СТП 2.5.3, 2.5.5, Приложение Н */",
        ".figure-container {",
        "  text-align: center;",
        "  margin: 12pt 0;",
        "  page-break-inside: avoid;",
        "}",
        ".figure-img {",
        "  max-width: 80%;",
        "  height: auto;",
        "  border: none;",
        "}",
        ".figure-caption {",
        "  text-align: center;",
        "  font-size: 14pt;",
        "  margin-top: 8pt;",
        "  text-indent: 0;",
        "}",
        "/* Таблицы строго по СТП 2.6.2, 2.6.4, Приложение Л */",
        ".table-container {",
        "  margin: 18pt 0;",
        "  page-break-inside: avoid;",
        "}",
        ".table-caption {",
        "  text-align: left;",
        "  font-size: 14pt;",
        "  margin-bottom: 6pt;",
        "  text-indent: 0;",
        "}",
        ".stp-table {",
        "  width: 100%;",
        "  border-collapse: collapse;",
        "  font-size: 12pt;",
        "  line-height: 1.15;",
        "  margin: 0;",
        "}",
        ".stp-table th, .stp-table td {",
        "  border: 1px solid #000000;",
        "  padding: 5pt 8pt;",
        "  vertical-align: middle;",
        "  text-align: left;",
        "}",
        ".stp-table th {",
        "  font-weight: bold;",
        "  text-align: center;",
        "}",
        "/* Формулы строго по СТП 2.4.6, 2.4.7, Приложение М: номер у правого края */",
        ".equation-row {",
        "  display: flex;",
        "  justify-content: space-between;",
        "  align-items: center;",
        "  margin: 14pt 0;",
        "  page-break-inside: avoid;",
        "}",
        ".equation-math {",
        "  flex-grow: 1;",
        "  text-align: center;",
        "}",
        ".equation-num {",
        "  text-align: right;",
        "  min-width: 45pt;",
        "  font-family: 'Times New Roman', serif;",
        "  font-size: 14pt;",
        "}",
        ".equation-svg {",
        "  max-height: 45pt;",
        "  height: auto;",
        "  vertical-align: middle;",
        "}",
        ".inline-math {",
        "  display: inline-block;",
        "  vertical-align: -2px;",
        "  height: 1.15em;",
        "  margin: 0 1px;",
        "}",
        "math {",
        "  font-size: 14pt;",
        "  font-family: 'Times New Roman', serif;",
        "}",
        ".page-break { page-break-after: always; }",
        "</style>",
        "</head>",
        "<body>"
    ]

    # 1. ТИТУЛЬНЫЙ ЛИСТ (СТП Приложение В)
    html_parts.extend([
        "<div class='title-page'>",
        "  <div class='title-header'>",
        "    МИНИСТЕРСТВО ОБРАЗОВАНИЯ РЕСПУБЛИКИ БЕЛАРУСЬ<br>",
        "    УЧРЕЖДЕНИЕ ОБРАЗОВАНИЯ<br>",
        "    «БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ ИНФОРМАТИКИ И РАДИОЭЛЕКТРОНИКИ»<br>",
        f"    {faculty}<br>",
        f"    {dept}",
        "  </div>",
        "  <div class='title-center'>",
        "    <div class='title-main'>",
        "      ОТЧЕТ<br>",
        f"      по лабораторной работе №&nbsp;{lab_num}<br>",
        f"      по дисциплине «{subject}»<br>",
        f"      на тему: «{lab_topic}»<br><br>",
        f"      Вариант №&nbsp;{variant}",
        "    </div>",
        "  </div>",
        "  <div class='title-sign-block'>",
        "    <strong>Выполнил(а):</strong><br>",
        f"    студент(ка) гр.&nbsp;{group}<br>",
        f"    {student}<br><br>",
        "    <strong>Проверил:</strong><br>",
        f"    {teacher_role}<br>",
        f"    {teacher}",
        "  </div>",
        "  <div class='title-footer'>",
        f"    {city} {year}",
        "  </div>",
        "</div>"
    ])

    # 2. РАЗДЕЛЫ ОТЧЕТА
    for sec in data["sections"]:
        sec_num = sec["number"]
        sec_title = sec["title"]
        html_parts.append(f"<div class='section-title'>{sec_num} {sec_title}</div>")

        for item in sec["items"]:
            itype = item["type"]
            if itype == "paragraph":
                html_parts.append(f"<p>{item['text']}</p>")

            elif itype == "code":
                code_counter += 1
                if item["caption"]:
                    html_parts.append(f"<div class='code-caption'>{item['caption']}</div>")
                # Код строго шрифтом Courier New 13 pt, БЕЗ рамок и БЕЗ фона
                escaped_code = html_lib.escape(item["code"])
                html_parts.append(f"<div class='code-block'>{escaped_code}</div>")

            elif itype == "figure":
                fig_counter += 1
                raw_cap = item.get("caption", "").strip()
                # Удаляем завершающую точку по СТП 2.5.5
                raw_cap = raw_cap.rstrip('.')
                if not re.match(r'^(?:Рисунок|рис\.)\s*\d+', raw_cap, re.IGNORECASE):
                    full_caption = f"Рисунок {fig_counter} – {raw_cap}" if raw_cap else f"Рисунок {fig_counter}"
                else:
                    full_caption = raw_cap

                if item["img_b64"]:
                    html_parts.append("<div class='figure-container'>")
                    html_parts.append(f"  <img class='figure-img' src='{item['img_b64']}' alt='{full_caption}'>")
                    html_parts.append(f"  <div class='figure-caption'>{full_caption}</div>")
                    html_parts.append("</div>")

            elif itype == "table":
                table_counter += 1
                raw_cap = item.get("caption", "").strip().rstrip('.')
                if not re.match(r'^(?:Таблица|табл\.)\s*\d+', raw_cap, re.IGNORECASE):
                    full_caption = f"Таблица {table_counter} – {raw_cap}" if raw_cap else f"Таблица {table_counter}"
                else:
                    full_caption = raw_cap

                html_parts.append("<div class='table-container'>")
                if full_caption:
                    html_parts.append(f"  <div class='table-caption'>{full_caption}</div>")
                html_parts.append("  <table class='stp-table'>")

                rows = item.get("rows", [])
                for r_idx, row in enumerate(rows):
                    html_parts.append("    <tr>")
                    tag = "th" if r_idx == 0 else "td"
                    for cell in row:
                        html_parts.append(f"      <{tag}>{cell}</{tag}>")
                    html_parts.append("    </tr>")

                html_parts.append("  </table>")
                html_parts.append("</div>")

            elif itype == "enumerate":
                start_val = item.get("start", 1)
                html_parts.append(f"<ol start='{start_val}'>")
                for li in item["items"]:
                    html_parts.append(f"  <li>{li}</li>")
                html_parts.append("</ol>")

            elif itype == "itemize":
                html_parts.append("<ul>")
                for li in item["items"]:
                    html_parts.append(f"  <li>{li}</li>")
                html_parts.append("</ul>")

            elif itype == "equation":
                eq_counter += 1
                formula_html = render_math_to_html(item["formula"], is_block=True)
                html_parts.append("<div class='equation-row'>")
                html_parts.append(f"  <div class='equation-math'>{formula_html}</div>")
                html_parts.append(f"  <div class='equation-num'>({eq_counter})</div>")
                html_parts.append("</div>")

    html_parts.extend(["</body>", "</html>"])
    return "\n".join(html_parts)

def stamp_page_numbers(input_pdf: Path, output_pdf: Path):
    """
    Накладывает векторные номера страниц в правый нижний угол (10 мм от края, 15 мм от правого края)
    начиная со страницы 2 по правилам СТП 2.2.8.
    """
    reader = pypdf.PdfReader(str(input_pdf))
    writer = pypdf.PdfWriter()
    total_pages = len(reader.pages)

    for idx, page in enumerate(reader.pages, start=1):
        if idx == 1:
            # Титульный лист (стр. 1): номер не печатается!
            writer.add_page(page)
        else:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)
            can.setFont("Times-Roman", 14)
            can.drawRightString(210 * mm - 15 * mm, 10 * mm, str(idx))
            can.save()

            packet.seek(0)
            overlay = pypdf.PdfReader(packet)
            page.merge_page(overlay.pages[0])
            writer.add_page(page)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(output_pdf, "wb") as f:
        writer.write(f)

    return total_pages

def export_latex_to_pdf(tex_file: Path, output_pdf: Path, force_engine: str = None):
    """Основная функция экспорта LaTeX в PDF по стандарту БГУИР СТП 01-2017/2024."""
    if not tex_file.exists():
        print(f"[ERROR] Файл LaTeX не найден: {tex_file}")
        return False

    project_dir = tex_file.parent

    # 1. Проверяем компиляторы TeX (если не форсирован HTML)
    tex_compiler = None
    if force_engine != "html":
        for c in ["xelatex", "pdflatex", "tectonic"]:
            if shutil.which(c):
                tex_compiler = c
                break

    if tex_compiler and force_engine != "html":
        print(f"[INFO] Обнаружен компилятор {tex_compiler}. Запуск компиляции TeX...")
        try:
            cmd = ["tectonic", str(tex_file.name)] if tex_compiler == "tectonic" else [tex_compiler, "-interaction=nonstopmode", str(tex_file.name)]
            subprocess.run(cmd, cwd=str(project_dir), capture_output=True, timeout=60)
            if tex_compiler != "tectonic":
                subprocess.run(cmd, cwd=str(project_dir), capture_output=True, timeout=60)

            generated_pdf = project_dir / f"{tex_file.stem}.pdf"
            if generated_pdf.exists():
                shutil.copy2(generated_pdf, output_pdf)
                print(f"[SUCCESS] Документ скомпилирован через {tex_compiler}: {output_pdf}")
                return True
        except Exception as e:
            print(f"[WARN] Ошибка компиляции TeX: {e}. Переключение на встроенный векторный рендерер.")

    # 2. Высокоточный встроенный рендерер (HTML + Headless Edge + MathML + ReportLab)
    edge_exe = find_edge_path()
    if not edge_exe:
        print("[ERROR] Не найден Microsoft Edge для векторного рендеринга.")
        return False

    print("[INFO] Векторный экспорт: MathML формулы, код Courier New 13 pt без рамок, нумерация СТП...")
    data = parse_latex_document(tex_file)
    html_content = render_html_report(data)

    temp_html = project_dir / "_temp_render.html"
    temp_pdf = project_dir / "_temp_render.pdf"

    temp_html.write_text(html_content, encoding="utf-8")

    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={temp_pdf.resolve()}",
        str(temp_html.resolve())
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if not temp_pdf.exists() or temp_pdf.stat().st_size == 0:
        print(f"[ERROR] Сбой генерации PDF через Edge. Код: {res.returncode}")
        return False

    # 3. Наложение векторных номеров страниц в правый нижний угол (10 мм от края)
    total_pages = stamp_page_numbers(temp_pdf, output_pdf)

    temp_html.unlink(missing_ok=True)
    temp_pdf.unlink(missing_ok=True)

    print(f"[SUCCESS] Документ PDF успешно экспортирован по стандарту БГУИР СТП!")
    print(f"  Файл:      {output_pdf}")
    print(f"  Размер:    {output_pdf.stat().st_size / 1024:.1f} КБ")
    print(f"  Страниц:   {total_pages} (титульный лист без номера, далее со 2-й страницы)")
    return True

def main():
    parser = argparse.ArgumentParser(description="Экспорт LaTeX отчета БГУИР в PDF по стандарту СТП")
    parser.add_argument("tex_file", type=str, help="Путь к файлу main.tex")
    parser.add_argument("-o", "--output", type=str, help="Путь к результирующему PDF")
    parser.add_argument("--force-engine", type=str, choices=["html", "tex"], default=None, help="Принудительный выбор движка")
    args = parser.parse_args()

    tex_path = Path(args.tex_file).resolve()
    out_pdf = Path(args.output).resolve() if args.output else tex_path.with_suffix(".pdf")

    success = export_latex_to_pdf(tex_path, out_pdf, force_engine=args.force_engine)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
