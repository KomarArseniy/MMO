#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py
Генератор отчетов по лабораторным работам по стандарту БГУИР СТП 01-2017 / СТП 01-2024 в формате LaTeX.

Особенности:
- Полная автоматизация подготовки проекта LaTeX со структурой из 7 обязательных разделов.
- Проверка лимита теории (СТРОГО не более 4 страниц).
- Автоматическое обнаружение исходных файлов (код, скриншоты, задания) в директории.
- Автоматическая генерация ссылок на рисунки в тексте (по требованию СТП 2.5.6).
- Защита формул LaTeX при конвертации Markdown.
- Создание готового ZIP-архива для быстрой загрузки в Overleaf.
- Попытка автоматической компиляции при наличии pdflatex/xelatex/tectonic.
"""

import os
import sys
import re
import json
import shutil
import zipfile
import argparse
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Попытка импорта yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".h": "C",
    ".c": "C",
    ".cs": "[Sharp]C",
    ".java": "Java",
    ".js": "JavaScript",
    ".ts": "JavaScript",
    ".sql": "SQL",
    ".html": "HTML",
    ".xml": "XML",
    ".sh": "bash",
    ".ps1": "bash",
    ".go": "Go",
    ".rs": "Rust",
    ".asm": "Assembler"
}

def format_inline_markdown(text: str) -> str:
    """Обрабатывает инлайн маркдаун вне математических блоков."""
    # Инлайн код: `code` -> \texttt{code}
    text = re.sub(r'`([^`]+)`', r'\\texttt{\1}', text)
    # Жирный шрифт: **bold**
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\\textbf{\1}', text)
    # Курсив: *italic*
    text = re.sub(r'(?<!\*)\*([^\*\s][^\*]*[^\*\s]|[^\*\s])\*(?!\*)', r'\\textit{\1}', text)
    return text

def convert_markdown_tables_in_text(text: str) -> str:
    """Конвертирует таблицы Markdown (|...|) в таблицы LaTeX."""
    lines = text.split('\n')
    new_lines = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith('|') and line.endswith('|'):
            table_lines = []
            while idx < len(lines) and lines[idx].strip().startswith('|') and lines[idx].strip().endswith('|'):
                table_lines.append(lines[idx].strip())
                idx += 1
            if len(table_lines) >= 2:
                rows = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip('|').split('|')]
                    if all(re.match(r'^:?-+:?$', c) for c in cells):
                        continue
                    rows.append(cells)
                if rows:
                    num_cols = max(len(r) for r in rows)
                    col_spec = '|' + '|'.join(['c'] * num_cols) + '|'
                    caption_text = "Параметры и исходные данные варианта"
                    tex_table = [
                        '\\begin{table}[H]',
                        '\\centering',
                        f'\\caption{{{caption_text}}}',
                        f'\\label{{tab:data}}',
                        f'\\begin{{tabular}}{{{col_spec}}}',
                        '\\hline'
                    ]
                    for r in rows:
                        while len(r) < num_cols:
                            r.append('')
                        tex_table.append(' & '.join(r) + ' \\\\')
                        tex_table.append('\\hline')
                    tex_table.append('\\end{tabular}')
                    tex_table.append('\\end{table}')
                    new_lines.append('\n'.join(tex_table))
                    continue
        new_lines.append(lines[idx])
        idx += 1
    return '\n'.join(new_lines)

def markdown_to_latex(text: str) -> str:
    """Преобразует базовую markdown-разметку (жирный, курсив, списки, таблицы) в LaTeX с защитой математики."""
    if not text:
        return ""

    # Конвертируем таблицы Markdown перед разбором текста
    text = convert_markdown_tables_in_text(text)

    # 1. Защита математических формул и таблиц LaTeX
    math_blocks = []
    def save_math(match):
        math_blocks.append(match.group(0))
        return f"XXMATHBLOCK{len(math_blocks)-1}XX"

    # Защищаем таблицы LaTeX
    text = re.sub(r'\\begin\{table\*?\}.*?\\end\{table\*?\}', save_math, text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}', save_math, text, flags=re.DOTALL)
    # Защищаем многострочные формулы и уравнения
    text = re.sub(r'\\begin\{(?:equation|align|gather)\*?\}.*?\\end\{(?:equation|align|gather)\*?\}', save_math, text, flags=re.DOTALL)
    text = re.sub(r'\$\$.*?\$\$', save_math, text, flags=re.DOTALL)
    text = re.sub(r'\\\[.*?\\\]', save_math, text, flags=re.DOTALL)
    text = re.sub(r'\$[^\$\n]+?\$', save_math, text)
    lines = text.strip().split('\n')
    latex_lines = []
    in_enumerate = False
    nested_itemize = False
    in_itemize = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Маркированный список
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:].strip()
            content = format_inline_markdown(content)
            if in_enumerate:
                if not nested_itemize:
                    latex_lines.append(r"  \begin{itemize}")
                    nested_itemize = True
                latex_lines.append(f"    \\item {content}")
            else:
                if not in_itemize:
                    latex_lines.append(r"\begin{itemize}")
                    in_itemize = True
                latex_lines.append(f"  \\item {content}")
            i += 1
            continue

        # Нумерованный список
        num_match = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if num_match:
            content = num_match.group(2).strip()
            content = format_inline_markdown(content)
            if nested_itemize:
                latex_lines.append(r"  \end{itemize}")
                nested_itemize = False
            if in_itemize:
                latex_lines.append(r"\end{itemize}")
                in_itemize = False
            if not in_enumerate:
                latex_lines.append(r"\begin{enumerate}")
                in_enumerate = True
            latex_lines.append(f"  \\item {content}")
            i += 1
            continue

        # Формула или блок внутри списка
        if (in_enumerate or in_itemize) and ("XXMATHBLOCK" in stripped):
            latex_lines.append(f"  {stripped}")
            i += 1
            continue

        # Обычный абзац вне списка
        if nested_itemize:
            latex_lines.append(r"  \end{itemize}")
            nested_itemize = False
        if in_itemize:
            latex_lines.append(r"\end{itemize}")
            in_itemize = False
        if in_enumerate:
            latex_lines.append(r"\end{enumerate}")
            in_enumerate = False
        formatted_line = format_inline_markdown(stripped)
        latex_lines.append(formatted_line)
        i += 1

    if nested_itemize:
        latex_lines.append(r"  \end{itemize}")
    if in_itemize:
        latex_lines.append(r"\end{itemize}")
    if in_enumerate:
        latex_lines.append(r"\end{enumerate}")

    result = "\n".join(latex_lines)

    # Восстановление защищенных математических формул
    for idx, mb in enumerate(math_blocks):
        result = result.replace(f"XXMATHBLOCK{idx}XX", mb)

    return result

def estimate_theory_pages(theory_text: str) -> float:
    """
    Оценивает объем теории в страницах формата А4 (шрифт 14pt, интервал 1.0).
    Примерно 350-400 слов на страницу текста.
    """
    words = len(theory_text.split())
    chars = len(theory_text)
    page_by_words = words / 350.0
    page_by_chars = chars / 2400.0
    estimated = max(1.0, round((page_by_words + page_by_chars) / 2.0, 1))
    return estimated

def auto_discover_assets(source_dir: Path):
    """Автоматически находит код, скриншоты, файлы теории и задания в директории."""
    discovered = {
        "task_text": "",
        "theory_text": "",
        "code_files": [],
        "screenshots": [],
        "variant": None,
        "lab_number": None
    }

    if not source_dir.exists():
        return discovered

    for item in sorted(source_dir.glob("**/*")):
        if item.is_file():
            name_lower = item.name.lower()
            suffix = item.suffix.lower()

            match_lab = re.search(r'lab[_\-\s]*(\d+)', str(item), re.IGNORECASE)
            if match_lab and not discovered["lab_number"]:
                discovered["lab_number"] = int(match_lab.group(1))

            if "task" in name_lower or "задан" in name_lower:
                if suffix in [".txt", ".md"]:
                    try:
                        content = item.read_text(encoding="utf-8")
                        discovered["task_text"] = content
                        var_match = re.search(r'вариант[^\d]*(\d+)', content, re.IGNORECASE)
                        if var_match and not discovered["variant"]:
                            discovered["variant"] = int(var_match.group(1))
                    except Exception:
                        pass

            elif "theory" in name_lower or "теори" in name_lower:
                if suffix in [".txt", ".md"]:
                    try:
                        discovered["theory_text"] = item.read_text(encoding="utf-8")
                    except Exception:
                        pass

            elif suffix in LANGUAGE_EXTENSIONS:
                discovered["code_files"].append({
                    "path": str(item),
                    "filename": item.name,
                    "language": LANGUAGE_EXTENSIONS[suffix],
                    "caption": f"Исходный код программы ({item.name})"
                })

            elif suffix in [".png", ".jpg", ".jpeg", ".bmp"]:
                discovered["screenshots"].append({
                    "path": str(item),
                    "filename": item.name,
                    "caption": f"Результат выполнения программы ({item.stem})"
                })

    return discovered

def generate_report(config: dict, output_dir: Path, template_sty_path: Path):
    """Генерирует полный проект отчета LaTeX."""
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    code_dir = output_dir / "code"
    images_dir.mkdir(exist_ok=True)
    code_dir.mkdir(exist_ok=True)

    target_sty = output_dir / "bsuir_stp.sty"
    if template_sty_path.exists():
        shutil.copy2(template_sty_path, target_sty)
    else:
        raise FileNotFoundError(f"Не найден файл стилей: {template_sty_path}")

    tp = config.get("title_page", {})
    faculty = tp.get("faculty", "Факультет компьютерных систем и сетей")
    department = tp.get("department", "Кафедра информатики")
    subject = tp.get("subject", "Основы алгоритмизации и программирования")
    lab_number = tp.get("lab_number", 1)
    lab_topic = tp.get("lab_topic", "Исследование алгоритмических структур")
    variant = tp.get("variant")

    if variant is None or str(variant).strip() == "":
        variant = 1
        print(f"[WARN] Внимание: номер варианта не был указан. Установлен вариант по умолчанию: {variant}")
    else:
        variant = str(variant).strip()

    student = tp.get("student", "Иванов И. И.")
    group = tp.get("group", "150501")
    teacher_role = tp.get("teacher_role", "старший преподаватель")
    teacher = tp.get("teacher", "Петров П. П.")
    city = tp.get("city", "Минск")
    year = tp.get("year", 2026)

    goal_text = config.get("goal", "Изучение теоретических основ и приобретение практических навыков решения индивидуального задания.")

    theory_text = config.get("theory", "")
    theory_file = config.get("theory_file")
    if theory_file and Path(theory_file).exists():
        theory_text = Path(theory_file).read_text(encoding="utf-8")

    est_pages = estimate_theory_pages(theory_text)
    print(f"[INFO] Расчетный объем теоретического раздела: ~{est_pages} стр. (лимит СТП: не более 4 страниц)")
    if est_pages > 4.0:
        print(f"[WARNING] ВНИМАНИЕ: Раздел теории превышает 4 страницы (~{est_pages} стр.)! Рекомендуется сократить материал.")

    task_text = config.get("task", f"Выполнить разработку программы согласно варианту № {variant}.")
    task_file = config.get("task_file")
    if task_file and Path(task_file).exists():
        task_text = Path(task_file).read_text(encoding="utf-8")

    code_items = config.get("code_files", [])
    processed_code = []
    for item in code_items:
        src_path = Path(item["path"])
        if src_path.exists():
            dest_file = code_dir / src_path.name
            shutil.copy2(src_path, dest_file)
            lang = item.get("language") or LANGUAGE_EXTENSIONS.get(src_path.suffix.lower(), "Python")
            cap = item.get("caption", f"Исходный код программы ({src_path.name})")
            processed_code.append({
                "rel_path": f"code/{src_path.name}",
                "language": lang,
                "caption": cap
            })
        else:
            inline_code = item.get("code")
            if inline_code:
                filename = item.get("filename", "solution.py")
                (code_dir / filename).write_text(inline_code, encoding="utf-8")
                lang = item.get("language", "Python")
                cap = item.get("caption", f"Исходный код программы ({filename})")
                processed_code.append({
                    "rel_path": f"code/{filename}",
                    "language": lang,
                    "caption": cap
                })

    screenshots = config.get("screenshots", [])
    processed_screenshots = []
    for idx, item in enumerate(screenshots, start=1):
        img_path = Path(item["path"])
        if img_path.exists():
            dest_img = images_dir / img_path.name
            shutil.copy2(img_path, dest_img)
            cap = item.get("caption", f"Результат работы программы (тест {idx})")
            processed_screenshots.append({
                "rel_path": f"images/{img_path.name}",
                "caption": cap,
                "label": f"fig:screen{idx}",
                "num": idx
            })

    conclusions = config.get("conclusions", [])
    if isinstance(conclusions, str):
        conclusions_text = markdown_to_latex(conclusions)
    elif isinstance(conclusions, list):
        items = "\n".join([f"  \\item {markdown_to_latex(c)}" for c in conclusions])
        conclusions_text = f"\\begin{{enumerate}}\n{items}\n\\end{{enumerate}}"
    else:
        conclusions_text = f"В ходе выполнения лабораторной работы №\\,{lab_number} были успешно освоены теоретические материалы, реализован алгоритм решения задачи по варианту №\\,{variant}, проведена отладка и выполнено тестирование программы."

    tex_parts = []
    tex_parts.append(r"\documentclass[14pt,a4paper]{extarticle}")
    tex_parts.append(r"\usepackage{bsuir_stp}")
    tex_parts.append("")
    tex_parts.append("% Настройки титульного листа")
    tex_parts.append(f"\\stpFaculty{{{faculty}}}")
    tex_parts.append(f"\\stpDepartment{{{department}}}")
    tex_parts.append(f"\\stpSubject{{{subject}}}")
    tex_parts.append(f"\\stpLabNumber{{{lab_number}}}")
    tex_parts.append(f"\\stpLabTopic{{{lab_topic}}}")
    tex_parts.append(f"\\stpVariant{{{variant}}}")
    tex_parts.append(f"\\stpStudent{{{student}}}")
    tex_parts.append(f"\\stpGroup{{{group}}}")
    tex_parts.append(f"\\stpTeacherRole{{{teacher_role}}}")
    tex_parts.append(f"\\stpTeacher{{{teacher}}}")
    tex_parts.append(f"\\stpCity{{{city}}}")
    tex_parts.append(f"\\stpYear{{{year}}}")
    tex_parts.append("")
    tex_parts.append(r"\begin{document}")
    tex_parts.append("")
    tex_parts.append("% 1. Титульный лист (с обязательным номером варианта)")
    tex_parts.append(r"\makestptitlepage")
    tex_parts.append("")

    tex_parts.append(r"% 2. Цель выполнения лабораторной работы")
    tex_parts.append(r"\clearpage")
    tex_parts.append(r"\section{Цель работы}")
    tex_parts.append(markdown_to_latex(goal_text))
    tex_parts.append("")

    tex_parts.append(r"% 3. Теория по лабораторной работе (не более 4 страниц)")
    tex_parts.append(r"\clearpage")
    tex_parts.append(r"\section{Краткие теоретические сведения}")
    if theory_text.strip():
        tex_parts.append(markdown_to_latex(theory_text))
    else:
        tex_parts.append(f"В данном разделе рассматриваются базовые понятия, методы и алгоритмы, необходимые для реализации индивидуального задания по дисциплине <<{subject}>> в соответствии с вариантом №\\,{variant}.")
    tex_parts.append("")

    tex_parts.append(r"% 4. Формулировка индивидуального задания")
    tex_parts.append(r"\clearpage")
    tex_parts.append(r"\section{Формулировка индивидуального задания}")
    tex_parts.append(f"Согласно варианту №\\,{variant} сформулировано следующее задание:")
    tex_parts.append(markdown_to_latex(task_text))
    tex_parts.append("")

    tex_parts.append(r"% 5. Весь код решения индивидуального задания")
    tex_parts.append(r"\clearpage")
    tex_parts.append(r"\section{Код решения индивидуального задания}")
    if processed_code:
        tex_parts.append("Ниже приведен полный текст программы решения поставленной задачи.")
        tex_parts.append("")
        for code_item in processed_code:
            tex_parts.append(f"\\lstinputlisting[language={code_item['language']}, caption={{{code_item['caption']}}}]{{{code_item['rel_path']}}}")
            tex_parts.append("")
    else:
        tex_parts.append("% Внимание: исходный код не был добавлен в конфигурацию.")
        tex_parts.append("\\begin{lstlisting}[language=Python, caption={Реализация алгоритма}]\n# Исходный код решения задания\n\\end{lstlisting}")
        tex_parts.append("")

    tex_parts.append(r"% 6. Скриншоты выполнения индивидуального задания")
    tex_parts.append(r"\clearpage")
    tex_parts.append(r"\section{Результаты выполнения индивидуального задания}")
    if processed_screenshots:
        tex_parts.append("Корректность функционирования разработанного программного обеспечения подтверждается результатами контрольных испытаний.")
        tex_parts.append("")
        for s in processed_screenshots:
            tex_parts.append(f"На рисунке~{s['num']} представлен результат выполнения программы.")
            tex_parts.append(r"\begin{figure}[H]")
            tex_parts.append(r"  \centering")
            tex_parts.append(f"  \\includegraphics[width=0.85\\textwidth]{{{s['rel_path']}}}")
            tex_parts.append(f"  \\caption{{{s['caption']}}}")
            tex_parts.append(f"  \\label{{{s['label']}}}")
            tex_parts.append(r"\end{figure}")
            tex_parts.append("")
    else:
        tex_parts.append("Тестирование разработанного решения выполнено на контрольных примерах. Результат запуска приведен на рисунке~1.")
        tex_parts.append(r"\begin{figure}[H]")
        tex_parts.append(r"  \centering")
        tex_parts.append(r"  \framebox[\textwidth]{\rule{0pt}{65mm}Место для скриншота окна программы}")
        tex_parts.append(r"  \caption{Результат работы программы при тестировании}")
        tex_parts.append(r"  \label{fig:screen1}")
        tex_parts.append(r"\end{figure}")
        tex_parts.append("")

    tex_parts.append(r"% 7. Выводы по лабораторной работе")
    tex_parts.append(r"\clearpage")
    tex_parts.append(r"\section{Выводы}")
    tex_parts.append(conclusions_text)
    tex_parts.append("")
    tex_parts.append(r"\end{document}")

    main_tex_content = "\n".join(tex_parts)
    main_tex_file = output_dir / "main.tex"
    main_tex_file.write_text(main_tex_content, encoding="utf-8")
    print(f"[OK] Файл отчета создан: {main_tex_file}")

    zip_name = f"report_lab{lab_number}_var{variant}.zip"
    zip_path = output_dir / zip_name
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(main_tex_file, arcname="main.tex")
        zipf.write(target_sty, arcname="bsuir_stp.sty")
        for f in images_dir.glob("*"):
            if f.is_file():
                zipf.write(f, arcname=f"images/{f.name}")
        for f in code_dir.glob("*"):
            if f.is_file():
                zipf.write(f, arcname=f"code/{f.name}")
    print(f"[OK] Готовый ZIP-архив для Overleaf: {zip_path}")

    compile_pdf(output_dir)
    return main_tex_file, zip_path

def compile_pdf(project_dir: Path):
    """Компилирует или экспортирует отчет в PDF по красоте."""
    tex_path = project_dir / "main.tex"
    out_pdf = project_dir / "main.pdf"
    if not tex_path.exists():
        return

    try:
        script_dir = Path(__file__).resolve().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from latex_to_pdf import export_latex_to_pdf
        export_latex_to_pdf(tex_path, out_pdf)
    except Exception as e:
        print(f"[WARN] Ошибка автоматического экспорта PDF: {e}")


def main():
    parser = argparse.ArgumentParser(description="Автоматический генератор отчетов по лабораторным работам БГУИР (СТП 01-2017/2024)")
    parser.add_argument("--config", "-c", type=str, help="Путь к файлу конфигурации (YAML или JSON)")
    parser.add_argument("--auto", "-a", type=str, help="Путь к директории лабораторной работы для авто-обнаружения файлов")
    parser.add_argument("--out-dir", "-o", type=str, default="./results/report", help="Выходная папка для проекта LaTeX")
    parser.add_argument("--lab", type=int, help="Номер лабораторной работы")
    parser.add_argument("--variant", "-v", type=int, help="Обязательный номер варианта")
    parser.add_argument("--subject", "-s", type=str, help="Название дисциплины")
    parser.add_argument("--student", type=str, help="ФИО студента")
    parser.add_argument("--group", type=str, help="Номер группы")
    parser.add_argument("--init", type=str, help="Создать шаблон конфигурационного файла report_config.yaml")

    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    template_sty = script_dir.parent / "templates" / "bsuir_stp.sty"

    if args.init:
        init_path = Path(args.init)
        if init_path.is_dir():
            init_file = init_path / "report_config.yaml"
        else:
            init_file = init_path
        example_file = script_dir.parent / "templates" / "lab_config_example.yaml"
        shutil.copy2(example_file, init_file)
        print(f"[OK] Шаблон конфигурации создан: {init_file}")
        return

    config = {}

    if args.config:
        cfg_path = Path(args.config)
        if not cfg_path.exists():
            print(f"[ERROR] Файл конфигурации не найден: {cfg_path}")
            sys.exit(1)
        if cfg_path.suffix.lower() in [".yaml", ".yml"]:
            if not HAS_YAML:
                print("[ERROR] Библиотека PyYAML не установлена.")
                sys.exit(1)
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        else:
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = json.load(f)

    if args.auto:
        auto_dir = Path(args.auto)
        discovered = auto_discover_assets(auto_dir)
        if not config:
            config = {"title_page": {}}
        tp = config.setdefault("title_page", {})
        if discovered["lab_number"] and not tp.get("lab_number"):
            tp["lab_number"] = discovered["lab_number"]
        if discovered["variant"] and not tp.get("variant"):
            tp["variant"] = discovered["variant"]
        if discovered["task_text"] and not config.get("task"):
            config["task"] = discovered["task_text"]
        if discovered["theory_text"] and not config.get("theory"):
            config["theory"] = discovered["theory_text"]
        if discovered["code_files"] and not config.get("code_files"):
            config["code_files"] = discovered["code_files"]
        if discovered["screenshots"] and not config.get("screenshots"):
            config["screenshots"] = discovered["screenshots"]

    tp = config.setdefault("title_page", {})
    if args.lab:
        tp["lab_number"] = args.lab
    if args.variant:
        tp["variant"] = args.variant
    if args.subject:
        tp["subject"] = args.subject
    if args.student:
        tp["student"] = args.student
    if args.group:
        tp["group"] = args.group

    out_path = Path(args.out_dir)
    generate_report(config, out_path, template_sty)

if __name__ == "__main__":
    main()
