---
name: docx-toolkit
description: >-
  Inspects, extracts text from, and creates or formats Microsoft Word (.docx) documents conforming to BSUIR STP 01-2017/2024.
  Use this skill whenever the user asks to read, analyze, extract text from, create, or format Word .docx documents, or generate a lab report in DOCX format.
---

# DOCX Toolkit

Инструмент для работы с документами Microsoft Word (`.docx`) на базе библиотеки `python-docx`.

---

## 1. Возможности и команды

Все операции выполняются через скрипт `scripts/docx_tools.py`:

### Получение информации о документе
Выводит количество параграфов, таблиц, примерное число слов и параметры полей:
```powershell
python <path_to_skill>/scripts/docx_tools.py info document.docx
```

### Извлечение текста и таблиц
Извлекает весь текст и содержимое таблиц в текстовый файл или консоль:
```powershell
python <path_to_skill>/scripts/docx_tools.py extract document.docx -o extracted_text.txt
```

### Генерация отчета по стандарту БГУИР СТП в формате DOCX
Создает полностью оформленный отчет по лабораторной работе (все 7 обязательных разделов, титульный лист, поля 30/15/20/20, шрифт Times New Roman 14 pt, одинарный интервал, отступ 1.25 см, рамки с кодом и скриншоты с подписями по СТП):
```powershell
python <path_to_skill>/scripts/docx_tools.py create-stp -c lab_config.yaml -o report.docx
```
