# -*- coding: utf-8 -*-
"""
pages/07_📚_Documentation.py — Platform Documentation, FAQ & Use Case Library

Sections:
  • Quick-Start Guide  — 5-step workflow walkthrough
  • Feature Reference  — tab-by-tab capability table
  • Tips & FAQ         — activation, caching, session, large files
  • FASTA Header Format— pipe-delimited field specification & examples
  • Use Case Library   — inline preview + download of usecase.md
"""

import os

import streamlit as st

from utils.minimal_i18n import T

# ─────────────────────────────────────────────────────────────────────────────
# Language-keyed long-form content blocks (avoid 100s of T() JSON keys)
# ─────────────────────────────────────────────────────────────────────────────
_lang = st.session_state.get("lang", st.session_state.get("language", "en"))

_QUICKSTART = {
    "en": """\
### Step 1 — 📁 Upload Your Data
Navigate to **Workspace** in the sidebar. Click *File Upload*, drag-and-drop
your `.fasta`, `.fa`, `.fas`, `.fna`, `.txt`, `.gz`, or `.aln-fasta` file,
then wait for the success banner. Your file is now in the session.

> **Alignment files (`.aln-fasta` / `.aln`):** Clustal Omega MSA output is
> fully supported. Gap characters (`-`) are stripped automatically before
> length and hash computation, so all downstream analytics are unaffected.

### Step 2 — ✅ Activate the Dataset
Scroll down to **Loaded Datasets**. A stats table shows each file's sequence
count, subtypes, segments and date span. Click **⚡ Activate All** to merge
all files at once, or select specific files and click **Activate Selected**.
> **Nothing works until you activate.**
> **Multiple files merged?** Sequence Refinery, Analytics and Molecular
> Timeline each show a **📁 File Scope** selector — switch to any single
> source file for focused per-file analysis without re-uploading.

### Step 3 — 🔬 Filter & Refine
Go to **Sequence Refinery**. Use the quality sliders (min/max length, N-run),
header-component filters (subtype, clade, date, host), and the HITL Smart
Sampler to get a representative phylogenetic subset.

### Step 4 — 📊 Explore & Visualize
Open **Analytics** for 10+ chart types (distribution, temporal, stacked,
epidemic curve, sunburst, treemap, violin, bubble, parallel, Gantt). Use the
**Palette Studio** to customise colours. Visit **Molecular Timeline** for
clone-persistence and overwintering analysis. All three analysis pages show
a **📁 File Scope** selector when multiple source files are active — pick
any file to narrow every chart and filter to that file only.

The **Observatory** (this page, when data is active) offers a live KPI
dashboard plus three advanced visualizations accessible via the sidebar
checkbox: **Sankey flow** (Host → Subtype → Clade), **Icicle hierarchy**
(Segment → Subtype → Clade), and a **3D Scatter** (Year × Length × Segment).

### Step 5 — 📋 Export
Go to **Export** to download the final FASTA, a CSV of metadata, a
methodology JSON, or a ZIP bundle of all three. Use *Split & Export* to
create one FASTA file per subtype / clade / host automatically.

> **Segment Folder Structure:** The Export page includes a dedicated section
> to generate a ZIP archive with segment folders (HA, NA, PB2, PB1, PA, NP,
> MP, NS, HE, P3). Choose from three content modes: *Empty folders (scaffold
> only)*, *Populate from active/filtered dataset*, or *Populate from Split &
> Export above* — the third option appears automatically when you have
> previewed a segment-level split in the Split & Export section above it,
> routing that exact data directly into the folder ZIP.
""",
    "ru": """\
### Шаг 1 — 📁 Загрузите данные
Перейдите в **Рабочее пространство** на боковой панели. Нажмите *Загрузка
файла*, перетащите `.fasta`, `.fa`, `.gz`, `.txt`, `.aln-fasta` или другой
поддерживаемый файл, дождитесь зелёного баннера успеха.

> **Файлы выравнивания (`.aln-fasta` / `.aln`):** вывод Clustal Omega
> полностью поддерживается. Символы пропусков (`-`) удаляются автоматически
> перед вычислением длины и хеша, поэтому вся аналитика остаётся корректной.

### Шаг 2 — ✅ Активируйте набор данных
Прокрутите до раздела **Загруженные наборы**. Таблица показывает для
каждого файла количество последовательностей, субтипы, сегменты и диапазон
дат. Нажмите **⚡ Активировать все** для слияния сразу, или выберите
конкретные файлы и нажмите **Активировать выбранные**.
> **Без активации ничего не работает.**
> **Объединено несколько файлов?** Очиститель, Аналитика и Молекулярная
> шкала показывают селектор **📁 Scope** — переключайтесь на любой
> исходный файл для анализа по отдельности.

### Шаг 3 — 🔬 Фильтрация и уточнение
Перейдите в **Очиститель последовательностей**. Используйте ползунки качества
(мин./макс. длина, N-серии), фильтры по полям заголовка (субтип, клад, дата,
хозяин) и интеллектуальный сэмплер HITL.

### Шаг 4 — 📊 Анализ и визуализация
Откройте **Аналитику** для 10+ типов диаграмм. Используйте **Студию палитры**
для настройки цветов. В **Молекулярной временной шкале** — анализ устойчивости
клонов и зимовки. При наличии нескольких исходных файлов все три страницы
анализа показывают селектор **📁 Scope** — выберите файл для фокусировки
всех графиков и фильтров.

**Обсерватория** (при наличии активного набора данных) предлагает дашборд
ключевых метрик и три расширенных визуализации (флажок на боковой панели):
**диаграмма Санки** (Хозяин → Субтип → Клад), **диаграмма-сосулька**
(Сегмент → Субтип → Клад) и **3D-разброс** (Год × Длина × Сегмент).

### Шаг 5 — 📋 Экспорт
Перейдите в **Экспорт** для скачивания итогового FASTA, CSV с метаданными,
JSON методологии или ZIP-архива. *Разделить и экспортировать* создаёт один
FASTA-файл на субтип / клад / хозяина автоматически.

> **Структура папок сегментов:** раздел *Структура папок сегментов* создаёт
> ZIP-архив с папками сегментов (HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3).
> Выберите один из трёх режимов: *Пустые папки (только структура)*,
> *Заполнить из активного/отфильтрованного датасета*, или *Заполнить из
> «Разделить и Экспортировать» выше* — третий вариант появляется автоматически
> при наличии предпросмотра разбивки по сегментам в разделе выше.
""",
}

_FEATURE_TABLE = {
    "en": """\
| Page | Key Actions | Notes |
|------|-------------|-------|
| **🌍 Observatory** | Live KPI dashboard (sequence count, avg length, subtypes, date span); epidemic curve; top subtypes/hosts/segments/locations/clades; Sankey flow, Icicle hierarchy, 3D Scatter (via sidebar checkbox) | Landing page when no data loaded; auto-switches to dashboard when dataset is active |
| **📁 Workspace** | File upload (`.fasta` `.fa` `.gz` `.zip` `.aln-fasta`); per-file stats table (subtypes, segments, date span); Select All / ⚡ Activate All; merge; **2×2 Top Metrics grid** (subtypes, segments, locations, host species) after activation | Activate before any other step; multiple files merged at once |
| **🔬 Sequence Refinery** | Min/max length, N-run filter, dedup, subtype/clade/date/host/location filters, HITL Smart Sampler; **📁 per-file scope**; dataset-aware strategy recommendation box; per-strategy sensitivity guide | Scope selector focuses all filters on one source file |
| **🧬 Molecular Timeline** | Clone persistence matrix, per-month representative selection, diagnostics, methodology snapshot; **📁 per-file scope**; **🔍 6-dimensional scope filter** (segment, subtype, host, host species, location, clade) | Needs `sequence_hash`; scope analyses each file's clusters independently |
| **📊 Analytics** | 10+ chart types, custom palettes, dataset-overview gauges (count, avg length, completeness); **📁 per-file scope**; **🔍 6-dimensional scope filter** (segment, subtype, host, host species, location, clade) | Scope filters AND-combined; only non-trivial dimensions shown |
| **📋 Export** | FASTA, CSV, JSON, ZIP bundle, accession list (.txt), session log, split-by-group export; Segment Folder Structure ZIP with **preset buttons** (Surface, Polymerase, Internal), sequence counts on labels, optional README per folder, optional summary CSV, live folder-structure preview, **3-mode data source** (empty / from dataset / from Split & Export); per-source-file downloads | Always export before closing the browser |
""",
    "ru": """\
| Страница | Ключевые действия | Примечания |
|----------|-------------------|-----------|
| **🌍 Обсерватория** | Дашборд КПЭ (количество, средняя длина, субтипы, диапазон дат); эпидемическая кривая; топ субтипов/хозяев/сегментов/местоположений/кладов; диаграмма Санки, иерархия-сосулька, 3D-разброс (флажок в боковой панели) | Целевая страница без данных; автопереключается в дашборд при активном наборе |
| **📁 Рабочее пространство** | Загрузка файла (`.fasta` `.fa` `.gz` `.zip` `.aln-fasta`); таблица статистики; Выбрать всё / ⚡ Активировать всё; слияние; **сетка 2×2** (субтипы, сегменты, местоположения, виды-хозяева) после активации | Сначала активируйте; несколько файлов объединяются сразу |
| **🔬 Очиститель последовательностей** | Мин./макс. длина, N-серии, дедупликация, фильтры по субтипу/кладу/дате/хозяину, сэмплер HITL; **📁 scope по файлу**; рекомендательный блок стратегии; руководство по чувствительности | Scope фокусирует все фильтры на одном исходном файле |
| **🧬 Молекулярная временная шкала** | Матрица устойчивости клонов, представители по месяцам, диагностика; **📁 scope по файлу**; **🔍 6-мерный фильтр** (сегмент, субтип, хозяин, вид-хозяин, местоположение, клад) | Нужен `sequence_hash`; scope анализирует кластеры каждого файла отдельно |
| **📊 Аналитика** | 10+ типов диаграмм, палитры, датасет-метрики; **📁 scope по файлу**; **🔍 6-мерный фильтр** (сегмент, субтип, хозяин, вид-хозяин, местоположение, клад) | Фильтры объединяются через И; показываются только нетривиальные измерения |
| **📋 Экспорт** | FASTA, CSV, JSON, ZIP, список аккессий (.txt), журнал сессии, экспорт по группам; структура папок сегментов с **кнопками быстрого выбора** (Поверхностные, Полимераза, Внутренние), счётчики, README, сводный CSV, превью; **3 режима содержимого** (пустые / из датасета / из «Разделить и Экспортировать»); загрузка по исходным файлам | Обязательно экспортируйте перед закрытием браузера |
""",
}

_TIPS_FAQ = {
    "en": """\
### 💡 Tips

| Tip | Detail |
|-----|--------|
| **Activation is Key** | Only sequences from *activated* datasets are used for analysis. Think of it as "loading the experiment." |
| **Large Files** | Processing large files can take time. Watch the progress bar spinners as indicators. The default row limit is 5,000 for some charts — increase via the slider. |
| **Caching** | Parsing is cached per file content hash. Re-uploading the same file is faster on re-run. Clear the cache by resetting the session. |
| **Session Data** | All work lives in your browser session and is lost on tab close or refresh. Use the Export page to save your results *before* closing. |
| **Filtered vs Active** | Most pages prefer the *filtered* dataset if one exists, falling back to the full *active* dataset. The source label shows which is in use. |
| **Language Toggle** | Switch between English and Russian at any time from the sidebar — all labels, buttons, and charts update immediately. |
| **Batch Multi-File** | Upload several FASTA files and click **⚡ Activate All** to merge them instantly. Once merged, Sequence Refinery, Analytics and Molecular Timeline all display a **📁 File Scope** radio at the top — switch to any source file to analyse it independently, then back to *All files (merged)* for the full view. |
| **Multi-Dimensional Scope** | After selecting a source file, open the **🔍 Scope Filters** expander in Analytics or Timeline to add up to 6 independent dimension filters (segment, subtype, host, **host species**, location, clade). Use *Host* to filter broadly (Avian / Human) and *Host Species* to zoom into specific birds (common_teal, Anas_platyrhynchos, duck, etc.). |
| **Host Inference** | Host class is inferred from the isolate name using the **GISAID structural rule**: avian/animal isolates always have 5 slash-parts (`A/HOST/Location/ID/Year`); human isolates always have 4 (`A/Location/ID/Year`). The parser therefore never confuses `A/common_teal/Chany/892/2018` (avian H3N6) with `A/Novosibirsk/RII-7.414/2024` (human H3N2) even though both are H3Nx. For the specific host class (Avian vs Mammalian), keyword lookup covers Latin genera (`Anas_platyrhynchos` → Avian) and compound names (`common_teal` → Avian). Any 5-part A/B isolate with an **unrecognised** host token still defaults to Avian — not Human — because the structural guarantee is authoritative. A `host_species` column stores the exact species token from slot 1. |

---

### ❓ Frequently Asked Questions

**Q: My sequences show "Unknown" subtype after upload. Why?**
> The header parser expects pipe-delimited fields matching GISAID's export format. If your headers use a different separator or order, use the *Header Converter* in Sequence Refinery to normalise them first.

**Q: Why is the Molecular Timeline matrix empty?**
> The timeline requires a `sequence_hash` column (added during deduplication in Sequence Refinery) and at least one sequence present in two or more months. Run *Deduplicate* first.

**Q: Analytics charts show "No data." after filtering.**
> The filter may have reduced the dataset to zero sequences. Check the sidebar *Active Sequences* count. Reset filters in Sequence Refinery if needed.

**Q: I uploaded the same file twice — why does it still show two entries?**
> VirSift detects duplicate filenames and skips re-parsing, but the entry persists in the loaded files list until you remove it. Click *Remove* next to the duplicate in Workspace.

**Q: How do I export per-subtype FASTA files?**
> In the Export page, open *Split & Export*, select **Subtype** as the split field, click *Preview Groups*, then download the ZIP of all sub-FASTAs.

**Q: I merged 3 files but want to see each file's clusters / charts separately.**
> In **Molecular Timeline**, **Analytics**, or **Sequence Refinery**, look for the
> **📁 File Scope** radio selector near the top of the page (only shown when
> multiple source files are active). Select any source file to narrow all charts,
> filters, and matrices to that file's sequences. Choose *All files (merged)* to
> restore the combined dataset view.

**Q: Can I use VirSift offline?**
> Yes — run `streamlit run app.py` locally after installing requirements. All processing is local; no sequences are ever uploaded to external servers.

**Q: My avian FASTA shows segments in the Subtype column and subtypes in the Segment column — why?**
> GISAID avian batch downloads use **segment-first** field order: `Isolate|SEGMENT|SUBTYPE|Date|Accession|Clade`. Human/B downloads use **subtype-first** order. VirSift auto-detects the order by checking whether field 2 matches a known segment name (HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3). If you see swapped columns, it may indicate a non-standard export — try normalising with the Header Converter.

**Q: Why is `Anas_platyrhynchos` (or another Latin species name) showing as "Unknown" host?**
> The parser's host classifier recognises Latin binomials by genus name. Ensure your headers use the standard GISAID format with underscores (`Anas_platyrhynchos`, not `Anas platyrhynchos`). Common genera like Anas, Gallus, Anser, Cygnus, Sus, Bos, Equus are all covered. If a genus is missing, open an issue so it can be added to `_AVIAN_GENERA` or `_MAMMAL_GENERA` in `utils/gisaid_parser.py`.

**Q: The 🔍 Scope Filters expander doesn't appear in Analytics — why?**
> The expander is only shown when the active dataset contains **at least one column** with 2 or more unique, non-"Unknown" values. A single-segment, single-host file with no meaningful diversity in any dimension will not show the expander — filter the full dataset in Sequence Refinery first.
""",
    "ru": """\
### 💡 Советы

| Совет | Подробности |
|-------|-------------|
| **Активация — ключ** | Только последовательности из *активированных* наборов участвуют в анализе. |
| **Большие файлы** | Обработка больших файлов занимает время. Следите за полосой прогресса. |
| **Кеширование** | Разбор файла кешируется по хешу содержимого. Повторная загрузка одного файла выполняется быстрее. |
| **Данные сессии** | Все данные хранятся в сессии браузера. Экспортируйте результаты *перед* закрытием вкладки. |
| **Фильтрованный vs активный** | Большинство страниц используют фильтрованный датасет, если он существует, иначе — полный активный. |
| **Переключение языка** | Переключайтесь между English и Русским в любое время из боковой панели. |
| **Пакетная обработка файлов** | Загрузите несколько FASTA-файлов и нажмите **⚡ Активировать все** для мгновенного слияния. После слияния Очиститель, Аналитика и Молекулярная шкала показывают **📁 Scope** — выберите файл для анализа по отдельности. |
| **Многомерный Scope** | После выбора исходного файла откройте **🔍 Фильтры Scope** в Аналитике или Шкале — до 6 независимых измерений (сегмент, субтип, хозяин, **вид-хозяин**, местоположение, клад). Используйте *Хозяин* для широкой фильтрации (Птицы / Человек), а *Вид-хозяин* — для конкретных птиц (common_teal, Anas_platyrhynchos, duck и т.д.). |
| **Определение хозяина** | Класс хозяина определяется по **структурному правилу GISAID**: птичьи/животные изоляты всегда имеют 5 частей через косую (`A/ХОЗЯИН/Место/ID/Год`); человеческие — 4 (`A/Место/ID/Год`). Благодаря этому `A/common_teal/Chany/892/2018` (H3N6 птица) никогда не путается с `A/Novosibirsk/RII-7.414/2024` (H3N2 человек). Ключевые слова уточняют класс (Птица/Млекопитающее) по роду и виду. Нераспознанный токен хозяина при ≥5 частях всё равно → Птицы. Столбец `host_species` хранит точный токен вида (слот 1). |

---

### ❓ Часто задаваемые вопросы

**В: Субтипы показываются как "Unknown". Почему?**
> Парсер ожидает поля в формате GISAID с вертикальной чертой. Если заголовки другого формата — используйте *Конвертер заголовков* в Очистителе.

**В: Матрица Молекулярной временной шкалы пустая.**
> Требуется столбец `sequence_hash` (добавляется при дедупликации) и хотя бы одна последовательность, встречающаяся в двух и более месяцах. Сначала запустите дедупликацию.

**В: Аналитика показывает "Нет данных" после фильтрации.**
> Фильтрация могла обнулить датасет. Проверьте счётчик *Активных последовательностей* в боковой панели.

**В: Как экспортировать FASTA-файлы по субтипу?**
> В Экспорте откройте *Разделить и экспортировать*, выберите **Субтип**, нажмите *Предпросмотр групп*, затем скачайте ZIP.

**В: Я объединил 3 файла, но хочу видеть кластеры/графики каждого файла отдельно.**
> В **Молекулярной шкале**, **Аналитике** или **Очистителе** найдите селектор
> **📁 File Scope** в верхней части страницы (отображается только при нескольких
> исходных файлах). Выберите нужный файл — все графики и фильтры сузятся до его
> последовательностей. Вернитесь к *All files (merged)* для общего вида.

**В: Как запустить VirSift локально?**
> Установите зависимости (`pip install -r requirements.txt`) и запустите `streamlit run app.py`. Никакие данные не отправляются на внешние серверы.

**В: В птичьем FASTA сегменты показаны в столбце Субтип, и наоборот — почему?**
> Выгрузки GISAID для птичьего гриппа используют порядок **сегмент—первый**: `Изолят|СЕГМЕНТ|СУБТИП|Дата|Аккессия|Клад`. Выгрузки для человеческого/B гриппа — порядок субтип—первый. VirSift автоматически определяет порядок по наличию поля 2 в списке известных сегментов.

**В: Почему `Anas_platyrhynchos` (или другое латинское название) показывается как "Unknown"?**
> Классификатор хозяев распознаёт латинские биномы по роду (первое слово). Убедитесь, что заголовки используют стандартный формат GISAID с подчёркиваниями. Если род отсутствует в базе — сообщите об этом через Issues.

**В: Развёртка 🔍 Scope Filters не отображается в Аналитике — почему?**
> Развёртка показывается только при наличии хотя бы одного столбца с 2 и более уникальными значениями (исключая "Unknown"). При однородном датасете сначала примените фильтры в Очистителе.
""",
}

# ─────────────────────────────────────────────────────────────────────────────
# Header format — three-virus reference (hRSV | Avian Flu | Human Flu)
# ─────────────────────────────────────────────────────────────────────────────
_HEADER_FORMAT = {
    "en": """\
VirSift supports **GISAID pipe-delimited** headers for three virus groups.
Each group uses a different field count and ordering — choose the one that matches
your GISAID download.

---

## 🫁 Human Respiratory Syncytial Virus (hRSV)

**Header structure:**
```
>Isolate_Name|GISAID_Accession|Collection_Date
```

| # | Field | Example | Format |
|---|-------|---------|--------|
| 1 | **Isolate Name** | `hRSV/B/Argentina/BA-HNRG-206/2016` | hRSV/Subtype/Location/ID/Year |
| 2 | **Accession** | `EPI_ISL_1074181` | EPI_ISL_XXXXXXX |
| 3 | **Collection Date** | `2016-04-18` | YYYY-MM-DD, YYYY-MM, YYYY, or `unknown` |

**Valid hRSV examples:**
```fasta
>hRSV/B/South_Korea/YSU-96B19/un|EPI_ISL_19159645|unknown
>hRSV/A/Argentina/BA-HNRG-206/2016|EPI_ISL_1074181|2016-04-18
>RSV/Human/GBR/2023-001|RSV_A|G|2023-11-04|EPI_ISL_17000001|ON1
```

**GISAID download settings for RSV:**
- FASTA Header field: **Isolate name | Isolate ID | Collection date**
- Date format: YYYY-MM-DD (2009-02-28)
- ☑ Replace spaces with underscores in FASTA header
- ☑ Remove spaces before and after values in FASTA header

---

## 🐦 Avian Influenza

> **⚠️ Field Order Auto-Detection:** GISAID avian batch downloads place the **segment BEFORE the subtype** (field order: `Isolate|SEGMENT|SUBTYPE|Date|Accession|Clade`), which is the **reverse** of human influenza downloads. VirSift automatically detects this by checking whether field 2 is a known segment name (HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3). No manual configuration is needed — just upload and activate.

**Header structure (avian GISAID batch download):**
```
>Isolate_Name|Gene_Segment|Virus_Type/Subtype|Collection_Date|GISAID_Accession|Clade_Assignment
```

| # | Field | Example | Format |
|---|-------|---------|--------|
| 1 | **Isolate Name** | `A/duck/Bangladesh/33676/2017` | A/Host/Location/ID/Year |
| 2 | **Segment** *(avian batch: segment-first)* | `PA` | HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3 |
| 3 | **Type / Subtype** | `A_/_H4N6` | `A_/_HxNy` or `A/HxNy` |
| 4 | **Date** | `2017-09-28` | YYYY-MM-DD, YYYY-MM, YYYY, or unknown |
| 5 | **Accession** | `EPI_ISL_329573` | EPI_ISL_XXXXXXX |
| 6 | **Clade** | `6B.1A.5a.2a.1` | Any format, empty, or `unassigned` |

**Valid avian influenza examples:**
```fasta
>A/duck/Bangladesh/33676/2017|PA|A_/_H4N6|2017-09-28|EPI_ISL_329573|6B.1A.5a.2a.1
>A/duck/Tottori/311018/2015|PA|A_/_H3N6|2015-10-01|EPI_ISL_237156|unassigned
>A/mallard/Republic_of_Georgia/13/2011|PA|A_/_H6N2|2011-11-26|EPI_ISL_189700|
>A/goose/China/1234/2020|HA|A/H5N1|2020-03|EPI_ISL_400001|2.3.4.4h
>A/Anas_platyrhynchos/Siberia/42/2023|HA|A_/_H5N1|2023-06-01|EPI_ISL_500123|2.3.4.4b
>A/common_teal/Italy/1494/2006|HA|A_/_H5N1|2006-11-05|EPI_ISL_100456|2.3.4.4
```

**Host inference from isolate names:**
VirSift infers host from the isolate name — no separate header field required:
- **Latin binomials** (`Anas_platyrhynchos`, `Gallus_gallus`, `Anser_anser`) → matched against `_AVIAN_GENERA` (140+ genera)
- **Compound English names** (`common_teal`, `mallard_duck`, `domestic_chicken`) → each word matched against `_AVIAN_KW`
- **Mammalian** (`Sus_scrofa` → Mammalian, `domestic_pig` → Mammalian)
- **Human influenza** names (`A/Novosibirsk/...`, `A/California/...`) → inferred as Human

**GISAID download settings for Avian Influenza:**
- Proteins: select segment (e.g., HA, PA, NP)
- FASTA Header field: **Isolate name | Type | Collection date | Isolate ID | Lineage**
- Date format: YYYY-MM-DD (2009-02-28)
- ☑ Replace spaces with underscores in FASTA header
- ☑ Remove spaces before and after values in FASTA header
- *Note: Add segment name manually or download each segment separately.*

---

## 🦠 Human Influenza

**Header structure:**
```
>Isolate_Name|Virus_Type/Subtype|Gene_Segment|Collection_Date|GISAID_Accession|Clade_Assignment
```

| # | Field | Examples | Notes |
|---|-------|----------|-------|
| 1 | **Strain name** | `A/Novosibirsk/RII-7.429/2024` · `B/Victoria/2/1987` | Full GISAID-style isolate name |
| 2 | **Type / Subtype** | `A/_H3N2` · `A/_H1N1` · `B` | Flu A uses `A/_HxNx`; Flu B has no subtype — write `B` |
| 3 | **Segment** | `HA` · `NA` · `PB2` · `PB1` · `PA` · `NP` · `MP` · `NS` · `HE` · `P3` | Any of the 10 influenza gene segments |
| 4 | **Collection date** | `2024-01-17` · `2009-04-09` · `1987` | ISO 8601 preferred; year-only (`YYYY`) also accepted |
| 5 | **Accession** | `EPI_ISL_19324838` · `EPI_ISL19324838` | With or without underscore between ISL and digits — both parsed |
| 6 | **Clade** | `3C.2a1b.2a.2a.3a.1` · `V1A.3a.2` · `6B.1A` | Nextclade / GISAID phylogenetic label |

**Valid human influenza examples:**
```fasta
>A/Novosibirsk/RII-7.429/2024|A/_H3N2|NP|2024-01-17|EPI_ISL19324838|3C.2a1b.2a.2a.3a.1
>B/Novosibirsk/RII-7.893S/2025|B|MP|2025-04-09|EPI_ISL_20154061|V1A.3a.2
>A/California/07/2009|A/_H1N1|HA|2009-04-09|EPI_ISL_29553|6B.1A
>B/Victoria/2/1987|B|NA|1987|EPI_ISL_100123|V1A.3a.2
>A/Hong_Kong/4801/2014|A/_H3N2|PA|2014-03-15|EPI_ISL_200456|3C.2a
```

**What these examples demonstrate:**

| Observation | Detail |
|-------------|--------|
| **Multi-subtype surveillance** | H3N2 (NP, PA), H1N1 (HA), and Flu B (MP, NA) coexist — use Subtype filter to isolate any one |
| **Multi-segment dataset** | NP, MP, HA, NA, PA all present — use Segment filter before phylogenetic analysis. All 10 segments (HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3) are supported |
| **Year-only date** | `B/Victoria/2/1987` has just `1987` — parsed as Jan 1st 1987; appears correctly in temporal charts |
| **Accession without underscore** | `EPI_ISL19324838` (no `_` between ISL and digits) — the parser normalises both formats |
| **Flu B without subtype** | Second field is simply `B` — no H/N designation needed for influenza B |
| **Multi-decade span** | 1987 → 2025 = 38-year dataset — ideal for Gantt Range chart in Analytics |

**GISAID download settings for Human Influenza:**
- FASTA Header field: **Isolate name | Type | Collection date | Isolate ID | Lineage**
- Date format: YYYY-MM-DD (2009-02-28)
- ☑ Replace spaces with underscores in FASTA header
- ☑ Remove spaces before and after values in FASTA header

---

---

## 🧬 Alignment Format (.aln-fasta)

VirSift natively accepts **Clustal Omega MSA output** in `.aln-fasta` format.
These files use the same GISAID pipe-delimited headers, but sequences contain
alignment gap characters (`-`).

**How VirSift handles alignment files:**
- Gap characters (`-`) are stripped from every sequence before parsing
- `sequence_length` and `sequence_hash` are computed on the gap-free sequence
- All downstream filters, deduplication and analytics work identically to standard FASTA

**Example valid `.aln-fasta` record:**
```fasta
>A/California/07/2009|A/_H1N1|HA|2009-04-09|EPI_ISL_29553|6B.1A
ATGAAAGC----AATTTTTAGT--CTAATTTTG-CTGGTTCTAACATGGCCTCAGAC
```

**Supported segments in alignment files:** HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3

---

## ⚠️ Common Issues

- **Missing pipes**: If headers use spaces or commas, run the *Header Converter* in Sequence Refinery.
- **Year-only dates in temporal charts**: Sequences with only `YYYY` dates will cluster at month 1 — expected behaviour.
- **Blank segments**: Write `||` (empty field) rather than `N/A` — the parser treats "N/A" as a segment name.
- **Mixed accession formats**: Both `EPI_ISL_12345` and `EPI_ISL12345` are valid; the accession extractor handles both.
- **HE and P3 segments**: These segments are less common (influenza C/D). VirSift parses them from the header field — no special configuration needed.

> 📄 For the complete format specification, see **1 FASTA Header Format Guide - Complete Reference.pdf** (included in the project download).
""",
    "ru": """\
VirSift поддерживает **формат GISAID с вертикальной чертой** для трёх групп вирусов.
Каждая группа имеет различное количество и порядок полей — выберите тот, который
соответствует вашей выгрузке из GISAID.

---

## 🫁 РСВ человека (hRSV)

**Структура заголовка:**
```
>Isolate_Name|GISAID_Accession|Collection_Date
```

| № | Поле | Пример | Формат |
|---|------|--------|--------|
| 1 | **Название изолята** | `hRSV/B/Argentina/BA-HNRG-206/2016` | hRSV/Субтип/Место/ID/Год |
| 2 | **Аккессия** | `EPI_ISL_1074181` | EPI_ISL_XXXXXXX |
| 3 | **Дата сбора** | `2016-04-18` | ГГГГ-ММ-ДД, ГГГГ-ММ, ГГГГ или `unknown` |

**Допустимые примеры hRSV:**
```fasta
>hRSV/B/South_Korea/YSU-96B19/un|EPI_ISL_19159645|unknown
>hRSV/A/Argentina/BA-HNRG-206/2016|EPI_ISL_1074181|2016-04-18
>RSV/Human/GBR/2023-001|RSV_A|G|2023-11-04|EPI_ISL_17000001|ON1
```

**Настройки загрузки GISAID для RSV:**
- Поля заголовка FASTA: **Isolate name | Isolate ID | Collection date**
- Формат даты: ГГГГ-ММ-ДД
- ☑ Заменить пробелы на подчёркивания в заголовке FASTA
- ☑ Удалить пробелы до и после значений

---

## 🐦 Птичий грипп

> **⚠️ Автоопределение порядка полей:** Пакетные выгрузки GISAID для птичьего гриппа ставят **сегмент ДО субтипа** (порядок: `Изолят|СЕГМЕНТ|СУБТИП|Дата|Аккессия|Клад`), что **противоположно** выгрузкам для человеческого гриппа. VirSift автоматически определяет порядок, проверяя, является ли поле 2 известным названием сегмента (HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3). Ручная настройка не требуется.

**Структура заголовка (пакетная выгрузка GISAID для птичьего гриппа):**
```
>Isolate_Name|Gene_Segment|Virus_Type/Subtype|Collection_Date|GISAID_Accession|Clade_Assignment
```

| № | Поле | Пример | Формат |
|---|------|--------|--------|
| 1 | **Название изолята** | `A/duck/Bangladesh/33676/2017` | A/Хозяин/Место/ID/Год |
| 2 | **Сегмент** *(птичий: сегмент первый)* | `PA` | HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3 |
| 3 | **Тип / Субтип** | `A_/_H4N6` | `A_/_HxNy` или `A/HxNy` |
| 4 | **Дата** | `2017-09-28` | ГГГГ-ММ-ДД, ГГГГ-ММ, ГГГГ или unknown |
| 5 | **Аккессия** | `EPI_ISL_329573` | EPI_ISL_XXXXXXX |
| 6 | **Клад** | `6B.1A.5a.2a.1` | Любой формат, пустое или `unassigned` |

**Допустимые примеры птичьего гриппа:**
```fasta
>A/duck/Bangladesh/33676/2017|PA|A_/_H4N6|2017-09-28|EPI_ISL_329573|6B.1A.5a.2a.1
>A/duck/Tottori/311018/2015|PA|A_/_H3N6|2015-10-01|EPI_ISL_237156|unassigned
>A/mallard/Republic_of_Georgia/13/2011|PA|A_/_H6N2|2011-11-26|EPI_ISL_189700|
>A/Anas_platyrhynchos/Siberia/42/2023|HA|A_/_H5N1|2023-06-01|EPI_ISL_500123|2.3.4.4b
>A/common_teal/Italy/1494/2006|HA|A_/_H5N1|2006-11-05|EPI_ISL_100456|2.3.4.4
```

**Определение хозяина из имени изолята:**
VirSift определяет хозяина из имени изолята — отдельное поле не нужно:
- **Латинские биномы** (`Anas_platyrhynchos`, `Gallus_gallus`, `Anser_anser`) → соответствие в `_AVIAN_GENERA` (140+ родов)
- **Составные английские названия** (`common_teal`, `mallard_duck`, `domestic_chicken`) → каждое слово проверяется по `_AVIAN_KW`
- **Млекопитающие** (`Sus_scrofa` → Млекопитающее, `domestic_pig` → Млекопитающее)

**Настройки загрузки GISAID для птичьего гриппа:**
- Белки: выберите сегмент (например, HA, PA, NP)
- Поля заголовка FASTA: **Isolate name | Type | Collection date | Isolate ID | Lineage**
- Формат даты: ГГГГ-ММ-ДД
- ☑ Заменить пробелы на подчёркивания
- ☑ Удалить пробелы до и после значений
- *Примечание: добавьте название сегмента вручную или скачивайте каждый сегмент отдельно.*

---

## 🦠 Человеческий грипп

**Структура заголовка:**
```
>Isolate_Name|Virus_Type/Subtype|Gene_Segment|Collection_Date|GISAID_Accession|Clade_Assignment
```

| № | Поле | Примеры | Примечания |
|---|------|---------|-----------|
| 1 | **Название штамма** | `A/Novosibirsk/RII-7.429/2024` · `B/Victoria/2/1987` | Полное название изолята в стиле GISAID |
| 2 | **Тип / Субтип** | `A/_H3N2` · `A/_H1N1` · `B` | Для гриппа А — `A/_HxNx`; для гриппа В — просто `B` |
| 3 | **Сегмент** | `HA` · `NA` · `PB2` · `PB1` · `PA` · `NP` · `MP` · `NS` · `HE` · `P3` | Любой из 10 генных сегментов гриппа |
| 4 | **Дата сбора** | `2024-01-17` · `2009-04-09` · `1987` | ISO 8601; только год (`ГГГГ`) тоже принимается |
| 5 | **Аккессия** | `EPI_ISL_19324838` · `EPI_ISL19324838` | С подчёркиванием и без — оба варианта поддерживаются |
| 6 | **Клад** | `3C.2a1b.2a.2a.3a.1` · `V1A.3a.2` · `6B.1A` | Метка клада от Nextclade / GISAID |

**Допустимые примеры человеческого гриппа:**
```fasta
>A/Novosibirsk/RII-7.429/2024|A/_H3N2|NP|2024-01-17|EPI_ISL19324838|3C.2a1b.2a.2a.3a.1
>B/Novosibirsk/RII-7.893S/2025|B|MP|2025-04-09|EPI_ISL_20154061|V1A.3a.2
>A/California/07/2009|A/_H1N1|HA|2009-04-09|EPI_ISL_29553|6B.1A
>B/Victoria/2/1987|B|NA|1987|EPI_ISL_100123|V1A.3a.2
>A/Hong_Kong/4801/2014|A/_H3N2|PA|2014-03-15|EPI_ISL_200456|3C.2a
```

**Что демонстрируют эти примеры:**

| Наблюдение | Подробности |
|------------|-------------|
| **Мультисубтипный надзор** | H3N2, H1N1 и грипп B сосуществуют — используйте фильтр Субтип |
| **Многосегментный датасет** | NP, MP, HA, NA, PA — используйте фильтр Сегмент перед анализом. Все 10 сегментов (HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3) поддерживаются |
| **Дата только год** | `B/Victoria/2/1987` содержит лишь `1987` — разбирается как 1 января 1987 |
| **Аккессия без подчёркивания** | `EPI_ISL19324838` — парсер нормализует оба варианта |
| **Грипп B без субтипа** | Второе поле — просто `B`, без обозначения H/N |
| **Многодесятилетний охват** | 1987–2025 = 38 лет — идеально для диаграммы Ганта в Аналитике |

**Настройки загрузки GISAID для человеческого гриппа:**
- Поля заголовка FASTA: **Isolate name | Type | Collection date | Isolate ID | Lineage**
- Формат даты: ГГГГ-ММ-ДД
- ☑ Заменить пробелы на подчёркивания
- ☑ Удалить пробелы до и после значений

---

---

## 🧬 Формат выравнивания (.aln-fasta)

VirSift поддерживает **вывод Clustal Omega MSA** в формате `.aln-fasta`.
Файлы используют те же заголовки в стиле GISAID с вертикальной чертой, но
последовательности содержат символы выравнивания (`-`).

**Как VirSift обрабатывает файлы выравнивания:**
- Символы пропусков (`-`) удаляются из каждой последовательности перед разбором
- `sequence_length` и `sequence_hash` вычисляются по последовательности без пропусков
- Все последующие фильтры, дедупликация и аналитика работают идентично стандартному FASTA

**Пример допустимой записи `.aln-fasta`:**
```fasta
>A/California/07/2009|A/_H1N1|HA|2009-04-09|EPI_ISL_29553|6B.1A
ATGAAAGC----AATTTTTAGT--CTAATTTTG-CTGGTTCTAACATGGCCTCAGAC
```

**Поддерживаемые сегменты в файлах выравнивания:** HA, NA, PB2, PB1, PA, NP, MP, NS, HE, P3

---

## ⚠️ Типичные проблемы

- **Отсутствующие вертикальные черты**: Используйте *Конвертер заголовков* в Очистителе.
- **Только год в дате**: Последовательности с `ГГГГ` будут кластеризованы в месяце 1 — ожидаемое поведение.
- **Пустые сегменты**: Пишите `||`, а не "N/A" — парсер воспримет "N/A" как название сегмента.
- **Смешанные форматы аккессий**: Оба варианта `EPI_ISL_12345` и `EPI_ISL12345` допустимы.
- **Сегменты HE и P3**: Менее распространены (грипп C/D). VirSift разбирает их из заголовка — специальной настройки не требуется.

> 📄 Полная спецификация — **1 FASTA Header Format Guide - Complete Reference.pdf** (включён в загрузку проекта).
""",
}

# ─────────────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────────────
st.title(f"📚 {T('docs_page_header')}")
st.caption(T("docs_page_caption"))

tab_qs, tab_feat, tab_tips, tab_hdr, tab_uc = st.tabs([
    f"🚀 {T('docs_tab_quickstart')}",
    f"🔧 {T('docs_tab_features')}",
    f"💡 {T('docs_tab_tips')}",
    f"🧬 {T('docs_tab_header_format')}",
    f"📚 {T('docs_tab_usecases')}",
])

# ── Tab 1: Quick-Start Guide ──────────────────────────────────────────────────
with tab_qs:
    st.markdown(_QUICKSTART.get(_lang, _QUICKSTART["en"]))

    st.divider()
    st.markdown(f"### 🗺️ {T('docs_nav_map_header')}")
    col_pages = st.columns(5)
    _pages_info = [
        ("📁", T("nav_workspace"),  T("docs_nav_workspace_desc"),  "pages/02_📁_Workspace.py"),
        ("🔬", T("nav_refinery"),   T("docs_nav_refinery_desc"),   "pages/03_🔬_Sequence_Refinery.py"),
        ("🧬", T("nav_timeline"),   T("docs_nav_timeline_desc"),   "pages/04_🧬_Molecular_Timeline.py"),
        ("📊", T("nav_analytics"),  T("docs_nav_analytics_desc"),  "pages/05_📊_Analytics.py"),
        ("📋", T("nav_export"),     T("docs_nav_export_desc"),     "pages/06_📋_Export.py"),
    ]
    for col, (icon, name, desc, path) in zip(col_pages, _pages_info):
        with col:
            st.markdown(f"**{icon} {name}**")
            st.caption(desc)
            try:
                st.page_link(path, label=f"→ {name}", use_container_width=True)
            except Exception:
                st.markdown(f"[→ {name}]({path})")

# ── Tab 2: Feature Reference ──────────────────────────────────────────────────
with tab_feat:
    st.markdown(f"### {T('docs_feature_ref_header')}")
    st.markdown(_FEATURE_TABLE.get(_lang, _FEATURE_TABLE["en"]))

# ── Tab 3: Tips & FAQ ─────────────────────────────────────────────────────────
with tab_tips:
    st.markdown(_TIPS_FAQ.get(_lang, _TIPS_FAQ["en"]))

# ── Tab 4: FASTA Header Format ────────────────────────────────────────────────
with tab_hdr:
    st.markdown(_HEADER_FORMAT.get(_lang, _HEADER_FORMAT["en"]))

    _pdf_path = os.path.join("cases", "1 FASTA Header Format Guide - Complete Reference.pdf")
    if os.path.exists(_pdf_path):
        with open(_pdf_path, "rb") as _pdf_f:
            st.download_button(
                label=f"📄 {T('docs_download_pdf')}",
                data=_pdf_f.read(),
                file_name="FASTA_Header_Format_Guide.pdf",
                mime="application/pdf",
                use_container_width=False,
            )
    else:
        st.caption(T("docs_download_pdf_missing"))

    # ── Test datasets section ────────────────────────────────────────────────
    st.divider()
    st.markdown(f"### 🧪 {T('docs_test_data_header')}")
    st.warning(T("docs_test_data_disclaimer"))

    _cases_dir = "cases"
    _test_files = [
        (
            "RSV-B_for_filtration.fasta",
            "docs_dl_rsv_fasta",
            "RSV-B — 3-field GISAID format: `>Isolate_Name|EPI_ISL|Date`",
            "RSV-B_for_filtration.fasta",
        ),
        (
            "All H3N2_20250918_070704.fasta",
            "docs_dl_h3n2_fasta",
            "H3N2 — 6-field GISAID format: `>Name|Type|Segment|Date|Accession|Clade`",
            "All_H3N2_test.fasta",
        ),
        (
            "HA_test_copy1.fasta",
            "docs_dl_ha_fasta",
            "HA segment — mixed Influenza A subtypes, multi-clade",
            "HA_test_copy1.fasta",
        ),
    ]

    _dl_cols = st.columns(3)
    for _col, (_fname, _key, _desc, _dl_name) in zip(_dl_cols, _test_files):
        _fpath = os.path.join(_cases_dir, _fname)
        with _col:
            st.caption(_desc)
            if os.path.exists(_fpath):
                with open(_fpath, "rb") as _ff:
                    st.download_button(
                        label=T(_key),
                        data=_ff.read(),
                        file_name=_dl_name,
                        mime="text/plain",
                        use_container_width=True,
                        key=f"dl_test_{_fname[:8]}",
                    )
            else:
                st.caption(f"_(file not found: `{_fname}`)_")

# ── Tab 5: Use Case Library ───────────────────────────────────────────────────
with tab_uc:
    st.markdown(f"### {T('docs_usecase_header')}")
    st.caption(T("docs_usecase_caption"))

    _uc_file = "usecase_ru.md" if _lang == "ru" else "usecase.md"
    _uc_path = os.path.join("cases", _uc_file)
    if not os.path.exists(_uc_path):  # Fallback to English if Russian not present
        _uc_path = os.path.join("cases", "usecase.md")
    if os.path.exists(_uc_path):
        with open(_uc_path, encoding="utf-8") as _uc_f:
            _uc_content = _uc_f.read()

        # Download button
        st.download_button(
            label=f"📥 {T('docs_download_guide')}",
            data=_uc_content.encode("utf-8"),
            file_name="virsift_usecase_guide.md",
            mime="text/markdown",
            type="primary",
            use_container_width=False,
        )

        st.divider()

        # Inline preview — first 5 use cases with search
        _search = st.text_input(T("docs_uc_search"), placeholder="H3N2, RSV, timeline …")

        # Parse use-cases by "## Use Case" headings
        import re as _re
        _uc_blocks = _re.split(r"(?=^## Use Case \d+)", _uc_content, flags=_re.MULTILINE)
        _uc_blocks = [b for b in _uc_blocks if b.strip().startswith("## Use Case")]

        if _search:
            _uc_blocks = [b for b in _uc_blocks if _search.lower() in b.lower()]
            st.caption(f"{T('docs_uc_results', n=len(_uc_blocks))}")

        if _uc_blocks:
            for _block in _uc_blocks[:20]:
                _title_line = _block.split("\n", 1)[0].strip("# ").strip()
                with st.expander(_title_line, expanded=False):
                    st.markdown(_block)
            if len(_uc_blocks) > 20:
                st.caption(T("export_more_items", n=len(_uc_blocks) - 20))
        else:
            st.info(T("docs_uc_no_results"))
    else:
        st.warning(T("docs_usecase_missing"))

    # Download documentation as Markdown (combined guide + feature reference)
    st.divider()
    _doc_bundle = (
        f"# VirSift v1.0.0 — {T('docs_page_header')}\n\n"
        f"## {T('docs_tab_quickstart')}\n\n{_QUICKSTART.get(_lang, _QUICKSTART['en'])}\n\n"
        f"## {T('docs_tab_features')}\n\n{_FEATURE_TABLE.get(_lang, _FEATURE_TABLE['en'])}\n\n"
        f"## {T('docs_tab_tips')}\n\n{_TIPS_FAQ.get(_lang, _TIPS_FAQ['en'])}\n\n"
        f"## {T('docs_tab_header_format')}\n\n{_HEADER_FORMAT.get(_lang, _HEADER_FORMAT['en'])}\n"
    )
    st.download_button(
        label=f"📥 {T('docs_download_docs')}",
        data=_doc_bundle.encode("utf-8"),
        file_name="virsift_documentation.md",
        mime="text/markdown",
        use_container_width=False,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Inter-page navigation
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
_doc_n1, _doc_n2 = st.columns(2)
try:
    _doc_n1.page_link("pages/06_📋_Export.py",
                      label=f"← 📋 {T('nav_export')}",
                      use_container_width=True)
    _doc_n2.page_link("pages/01_🌍_Observatory.py",
                      label=f"🌍 {T('nav_observatory')} →",
                      use_container_width=True)
except AttributeError:
    _doc_n1.markdown(f"[← 📋 {T('nav_export')}](pages/06_📋_Export.py)")
    _doc_n2.markdown(f"[🌍 {T('nav_observatory')} →](pages/01_🌍_Observatory.py)")
