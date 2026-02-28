import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from datetime import datetime
import os
from itertools import combinations

# --- Configuration ---
DATA_FILE = 'activity_links_gui.json'

class ActivityManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Activity Link Manager v2.1 GUI")
        self.root.geometry("1000x700")

        # Data storage
        self.data = {}
        # Initialize status_var
        self.status_var = tk.StringVar(value="Готов.")

        # --- Статистическая панель сверху ---
        self.stats_frame = ttk.Frame(root)
        self.stats_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        # Метки для статистики (создаём их здесь, до load_data)
        self.total_points_label = ttk.Label(self.stats_frame, text="Баллы: --", cursor="hand2")
        self.total_points_label.grid(row=0, column=0, padx=(0, 10))
        self.total_points_label.bind("<Button-1>", lambda e: self.show_detail_stats("total"))

        self.unused_links_label = ttk.Label(self.stats_frame, text="Неисп.: --", cursor="hand2")
        self.unused_links_label.grid(row=0, column=1, padx=(0, 10))
        self.unused_links_label.bind("<Button-1>", lambda e: self.show_detail_stats("unused"))

        self.used_links_label = ttk.Label(self.stats_frame, text="Исп.: --", cursor="hand2")
        self.used_links_label.grid(row=0, column=2, padx=(0, 10))
        self.used_links_label.bind("<Button-1>", lambda e: self.show_detail_stats("used"))

        # --- Create GUI Elements ---

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Add Link
        self.tab_add = ttk.Frame(self.notebook)
        # Добавляем вкладку и привязываем событие для установки фокуса
        self.notebook.add(self.tab_add, text="Добавить Ссылку")
        # Привязываем к самому notebook для отслеживания смены вкладки
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # Tab 2: Generate Report
        self.tab_report = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_report, text="Сформировать Отчёт")

        # Tab 3: Statistics
        self.tab_stats = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_stats, text="Статистика")

        self.setup_add_tab()
        self.setup_report_tab()
        self.setup_stats_tab()

        # Status Bar
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Теперь, после создания всех виджетов, загружаем данные
        self.load_data()

    # --- Методы для обработки стандартных горячих клавиш и контекстного меню ---
    def _create_context_menu(self, widget):
        """Создаёт и возвращает контекстное меню для виджета Entry или Text."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Вырезать", command=lambda: self._cut(widget))
        menu.add_command(label="Копировать", command=lambda: self._copy(widget))
        menu.add_command(label="Вставить", command=lambda: self._paste(widget))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: self._select_all(widget))
        return menu

    def _cut(self, widget):
        """Вырезает выделенный текст."""
        try:
            # Для Entry и Text
            widget.event_generate("<<Cut>>")
        except tk.TclError:
            # Нет выделения или виджет не поддерживает операцию
            pass

    def _copy(self, widget):
        """Копирует выделенный текст."""
        try:
            # Для Entry и Text
            widget.event_generate("<<Copy>>")
        except tk.TclError:
            # Нет выделения или виджет не поддерживает операцию
            pass

    def _paste(self, widget):
        """Вставляет текст из буфера обмена."""
        try:
            # Для Entry и Text
            widget.event_generate("<<Paste>>")
        except tk.TclError:
            # Буфер обмена пуст или виджет не поддерживает операцию
            pass

    def _select_all(self, widget):
        """Выделяет весь текст."""
        try:
            # Для Entry
            if isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
            # Для Text
            elif isinstance(widget, tk.Text):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, tk.END)
                widget.see(tk.INSERT)
        except tk.TclError:
            # Виджет не поддерживает операцию
            pass

    def _show_context_menu(self, event, menu):
        """Отображает контекстное меню."""
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Убедиться, что меню закрыто, если было прервано
            menu.grab_release()

    def _paste_to_entry(self, event):
        """Вставляет текст из буфера обмена в Entry."""
        try:
            clipboard_text = self.root.clipboard_get()
            self.link_entry.insert(tk.INSERT, clipboard_text)
            return "break"
        except tk.TclError:
            # Буфер обмена пуст или содержит недопустимый текст
            pass

    def _copy_from_entry(self, event):
        """Копирует выделенный текст из Entry в буфер обмена."""
        try:
            selection = self.link_entry.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
            return "break"
        except tk.TclError:
            # Нет выделения
            pass

    def _select_all_in_entry(self, event):
        """Выделяет весь текст в Entry."""
        self.link_entry.select_range(0, tk.END)
        self.link_entry.icursor(tk.END)
        return "break"

    def _paste_to_text(self, event):
        """Вставляет текст из буфера обмена в Text."""
        try:
            clipboard_text = self.root.clipboard_get()
            self.block_text1.insert(tk.INSERT, clipboard_text)
            return "break"
        except tk.TclError:
            pass

    def _copy_from_text(self, event):
        """Копирует выделенный текст из Text в буфер обмена."""
        try:
            selection = self.block_text1.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selection)
            return "break"
        except tk.TclError:
            pass

    def _select_all_in_text(self, event):
        """Выделяет весь текст в Text."""
        self.block_text1.tag_add(tk.SEL, "1.0", tk.END)
        self.block_text1.mark_set(tk.INSERT, tk.END)
        self.block_text1.see(tk.INSERT)
        return "break"
    # --- Конец методов для горячих клавиш и контекстного меню ---

    def setup_add_tab(self):
        """Sets up the 'Add Link' tab."""
        frame_main = ttk.Frame(self.tab_add, padding=(10, 10))
        frame_main.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Input field for single link
        ttk.Label(frame_main, text="Введите ссылку:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.link_entry = ttk.Entry(frame_main, width=70)
        self.link_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        self.link_entry.bind("<Return>", lambda event: self.add_single_link())

        # --- Привязки для Entry (одиночная ссылка) ---
        self.link_entry.bind("<Control-v>", self._paste_to_entry)
        self.link_entry.bind("<Control-V>", self._paste_to_entry) # Также для Shift+Ctrl+V
        self.link_entry.bind("<Control-c>", self._copy_from_entry)
        self.link_entry.bind("<Control-C>", self._copy_from_entry)
        self.link_entry.bind("<Control-a>", self._select_all_in_entry)
        self.link_entry.bind("<Control-A>", self._select_all_in_entry)

        # --- Контекстное меню для Entry ---
        self.entry_context_menu = self._create_context_menu(self.link_entry)
        self.link_entry.bind("<Button-3>", lambda e: self._show_context_menu(e, self.entry_context_menu))
        # ----------------------------------------------
        # Add button
        self.add_button = ttk.Button(frame_main, text="Добавить", command=self.add_single_link)
        self.add_button.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))

        # Separator
        ttk.Separator(frame_main, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # Input field for multiple links (block input)
        ttk.Label(frame_main, text="Или вставьте несколько ссылок (по одной в строке):").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.block_text1 = scrolledtext.ScrolledText(frame_main, height=10, width=70)
        self.block_text1.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # --- Привязки для Text (блок ссылок) ---
        self.block_text1.bind("<Control-v>", self._paste_to_text)
        self.block_text1.bind("<Control-V>", self._paste_to_text)
        self.block_text1.bind("<Control-c>", self._copy_from_text)
        self.block_text1.bind("<Control-C>", self._copy_from_text)
        self.block_text1.bind("<Control-a>", self._select_all_in_text)
        self.block_text1.bind("<Control-A>", self._select_all_in_text)

        # --- Контекстное меню для Text ---
        self.text_context_menu = self._create_context_menu(self.block_text1)
        self.block_text1.bind("<Button-3>", lambda e: self._show_context_menu(e, self.text_context_menu))
        # ----------------------------------------------
        # Process Block button
        self.process_block_button = ttk.Button(frame_main, text="Обработать Блок", command=self.process_block_input)
        self.process_block_button.grid(row=6, column=0, sticky=tk.W, pady=(5, 0))

        # Configure grid weights for resizing
        self.tab_add.columnconfigure(0, weight=1)
        self.tab_add.rowconfigure(0, weight=1)
        frame_main.columnconfigure(0, weight=1)
        frame_main.rowconfigure(5, weight=1)

    def setup_report_tab(self):
        """Sets up the 'Generate Report' tab."""
        frame_main = ttk.Frame(self.tab_report, padding=(10, 10))
        frame_main.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Target points input
        ttk.Label(frame_main, text="Требуемое количество баллов:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.target_points_entry = ttk.Entry(frame_main, width=20)
        self.target_points_entry.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.target_points_entry.bind("<Return>", lambda event: self.generate_report())

        # --- Контекстное меню для Entry цели ---
        target_menu = self._create_context_menu(self.target_points_entry)
        self.target_points_entry.bind("<Button-3>", lambda e: self._show_context_menu(e, target_menu))
        # ----------------------------------------------


        # Generate button
        self.generate_button = ttk.Button(frame_main, text="Сформировать Отчёт", command=self.generate_report)
        self.generate_button.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 10))

        # Results display
        ttk.Label(frame_main, text="Результат отчёта:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.report_results = scrolledtext.ScrolledText(frame_main, height=20, width=80, state=tk.DISABLED)
        self.report_results.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # Configure grid weights for resizing
        self.tab_report.columnconfigure(0, weight=1)
        self.tab_report.rowconfigure(0, weight=1)
        frame_main.columnconfigure(0, weight=1)
        frame_main.rowconfigure(3, weight=1)

    def setup_stats_tab(self):
        """Sets up the 'Statistics' tab."""
        frame_main = ttk.Frame(self.tab_stats, padding=(10, 10))
        frame_main.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Refresh button
        self.refresh_stats_button = ttk.Button(frame_main, text="Обновить", command=self.update_statistics)
        self.refresh_stats_button.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Statistics display
        ttk.Label(frame_main, text="Статистика:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.stats_display = scrolledtext.ScrolledText(frame_main, height=25, width=80, state=tk.DISABLED)
        self.stats_display.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # --- Контекстное меню для Text статистики ---
        stats_menu = self._create_context_menu(self.stats_display)
        self.stats_display.bind("<Button-3>", lambda e: self._show_context_menu(e, stats_menu))
        # ----------------------------------------------

        # Configure grid weights for resizing
        self.tab_stats.columnconfigure(0, weight=1)
        self.tab_stats.rowconfigure(0, weight=1)
        frame_main.columnconfigure(0, weight=1)
        frame_main.rowconfigure(2, weight=1)

        # Initial update
        self.update_statistics()

    def on_tab_change(self, event):
        """Устанавливает фокус на соответствующее поле ввода при переключении вкладок."""
        selected_tab_id = self.notebook.select()
        selected_tab_index = self.notebook.index(selected_tab_id)

        if selected_tab_index == 0:  # Вкладка "Добавить Ссылку"
            # Попробуем установить фокус на Entry
            self.link_entry.focus_set()
        elif selected_tab_index == 1: # Вкладка "Сформировать Отчёт"
            # Установим фокус на поле ввода цели
            self.target_points_entry.focus_set()
        # Для вкладки статистики фокус не нужен

    def show_status(self, message):
        """Updates the status bar."""
        self.status_var.set(message)
        self.root.after(3000, lambda: self.status_var.set("Готов.")) # Reset after 3 seconds

    def load_data(self):
        """Loads data from file."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                # Ensure structure
                for link_info in self.data.values():
                    if 'is_news' not in link_info:
                        link_info['is_news'] = False
                    for link_obj in link_info.get('links', []):
                        if 'used' not in link_obj:
                            link_obj['used'] = False
                self.show_status(f"Данные загружены из {DATA_FILE}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить данные из файла.\n{e}")
                self.data = {}
        else:
            # Set initial status message after status_var is initialized
            self.show_status(f"Файл данных {DATA_FILE} не найден. Будет создан при сохранении.")
        self.update_top_stats() # Now it's safe to call

    def save_data(self):
        """Saves data to file."""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            self.show_status(f"Данные сохранены в {DATA_FILE}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить данные в файл.\n{e}")

    def extract_ncs(self, link):
        """Extracts NCS from a link."""
        try:
            parts = link.strip().split('/')
            if len(parts) >= 6 and parts[3] == 'channels':
                ncs = parts[5]
                return ncs
            else:
                self.show_status("Ошибка: Неверный формат ссылки.")
                return None
        except Exception as e:
            self.show_status(f"Ошибка при извлечении НЧС: {e}")
            return None

    def get_or_create_ncs_info(self, ncs):
        """Prompts user for info if NCS is new."""
        if ncs not in self.data:
            dialog = tk.Toplevel(self.root)
            dialog.title("Новый тип активности")
            dialog.geometry("400x200")
            dialog.transient(self.root)
            dialog.grab_set()

            ttk.Label(dialog, text=f"НЧС '{ncs}' неизвестна. Укажите параметры:").pack(pady=5)

            frame_inputs = ttk.Frame(dialog)
            frame_inputs.pack(pady=5, padx=10, fill=tk.X)

            ttk.Label(frame_inputs, text="Баллы:").grid(row=0, column=0, sticky=tk.W)
            points_var = tk.StringVar()
            points_entry = ttk.Entry(frame_inputs, textvariable=points_var)
            points_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
            frame_inputs.columnconfigure(1, weight=1)

            # --- Контекстное меню для Entry баллов ---
            points_menu = self._create_context_menu(points_entry)
            points_entry.bind("<Button-3>", lambda e: self._show_context_menu(e, points_menu))
            # ----------------------------------------------

            ttk.Label(frame_inputs, text="Описание:").grid(row=1, column=0, sticky=tk.W)
            desc_var = tk.StringVar()
            desc_entry = ttk.Entry(frame_inputs, textvariable=desc_var)
            desc_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

            # --- Контекстное меню для Entry описания ---
            desc_menu = self._create_context_menu(desc_entry)
            desc_entry.bind("<Button-3>", lambda e: self._show_context_menu(e, desc_menu))
            # ----------------------------------------------

            news_var = tk.BooleanVar()
            news_check = ttk.Checkbutton(frame_inputs, text="Новостная активность?", variable=news_var)
            news_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

            def on_ok():
                try:
                    points = int(points_var.get())
                    if points < 0:
                        raise ValueError("Баллы не могут быть отрицательными.")
                    description = desc_var.get().strip()
                    if not description:
                        description = f"НЧС: {ncs}"
                    is_news = news_var.get()

                    self.data[ncs] = {
                        "points": points,
                        "description": description,
                        "is_news": is_news,
                        "links": [],
                    }
                    self.save_data()
                    self.show_status(f"Добавлен новый тип: {description} ({points} б., {'новость' if is_news else 'обычная'})")
                    dialog.destroy()
                except ValueError as e:
                    messagebox.showerror("Ошибка ввода", str(e))

            ok_button = ttk.Button(dialog, text="OK", command=on_ok)
            ok_button.pack(pady=10)

            dialog.wait_window()

    def add_single_link(self):
        """Adds a single link from the entry field."""
        link = self.link_entry.get().strip()
        if not link:
            messagebox.showwarning("Предупреждение", "Пожалуйста, введите ссылку.")
            return

        ncs = self.extract_ncs(link)
        if not ncs:
            return

        self.get_or_create_ncs_info(ncs)

        now_str = datetime.now().isoformat()
        self.data[ncs]["links"].append({
            "url": link,
            "date_added": now_str,
            "used": False
        })
        self.save_data()
        self.show_status(f"Ссылка добавлена: {link}")
        self.update_top_stats()
        self.link_entry.delete(0, tk.END)

    def process_block_input(self):
        """Processes multiple links pasted into the text area."""
        block_content = self.block_text1.get("1.0", tk.END).strip()
        if not block_content:
            messagebox.showwarning("Предупреждение", "Пожалуйста, вставьте ссылки в поле.")
            return

        links = [line.strip() for line in block_content.splitlines() if line.strip()]
        added_count = 0
        for link in links:
            ncs = self.extract_ncs(link)
            if ncs:
                self.get_or_create_ncs_info(ncs)
                now_str = datetime.now().isoformat()
                self.data[ncs]["links"].append({
                    "url": link,
                    "date_added": now_str,
                    "used": False
                })
                added_count += 1

        if added_count > 0:
            self.save_data()
            self.show_status(f"Обработан блок. Добавлено {added_count} ссылок.")
            self.update_top_stats()
            self.block_text1.delete("1.0", tk.END)
        else:
            self.show_status("Блок обработан, но не найдено корректных ссылок.")

    def calculate_combination_value(self, combo_links):
        """Calculates total value applying 50% to news."""
        total = 0
        news_sum = 0
        regular_sum = 0
        for link_info in combo_links:
            if link_info['is_news']:
                contribution = link_info['points'] // 2
                total += contribution
                news_sum += contribution
            else:
                contribution = link_info['points']
                total += contribution
                regular_sum += contribution
        return total, news_sum, regular_sum

    def generate_report(self):
        """Generates the report based on target points."""
        try:
            target_points = int(self.target_points_entry.get())
            if target_points <= 0:
                raise ValueError("Цель должна быть положительной.")
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", str(e))
            return

        unused_links = []
        for ncs_info in self.data.values():
            for link_obj in ncs_info["links"]:
                if not link_obj["used"]:
                    unused_links.append({
                        "url": link_obj["url"],
                        "points": ncs_info["points"],
                        "date_added": link_obj["date_added"],
                        "is_news": ncs_info["is_news"],
                        "ncs": list(self.data.keys())[list(self.data.values()).index(ncs_info)]
                    })

        if not unused_links:
            self.report_results.config(state=tk.NORMAL)
            self.report_results.delete("1.0", tk.END)
            self.report_results.insert(tk.END, "Нет доступных неиспользованных ссылок.")
            self.report_results.config(state=tk.DISABLED)
            self.show_status("Нет доступных ссылок для отчёта.")
            return

        unused_links.sort(key=lambda x: x["date_added"])

        best_combo = None
        min_length = float('inf')
        found_sufficient = False

        for r in range(1, len(unused_links) + 1):
            for combo in combinations(unused_links, r):
                if any(link['points'] == target_points and not link['is_news'] for link in combo) or \
                   any((link['points'] // 2) == target_points and link['is_news'] for link in combo):
                       continue

                total_val, news_val, reg_val = self.calculate_combination_value(combo)

                if total_val >= target_points:
                    total_req = news_val + reg_val
                    if total_req > 0:
                        news_ratio = (news_val / total_val) if total_val > 0 else 0
                        if 0.4 <= news_ratio <= 0.6:
                             if len(combo) < min_length:
                                 min_length = len(combo)
                                 best_combo = combo
                                 found_sufficient = True
                    else:
                         if len(combo) < min_length:
                                 min_length = len(combo)
                                 best_combo = combo
                                 found_sufficient = True

            if found_sufficient:
                break

        if best_combo is None:
            for r in range(1, len(unused_links) + 1):
                for combo in combinations(unused_links, r):
                     if any(link['points'] == target_points and not link['is_news'] for link in combo) or \
                        any((link['points'] // 2) == target_points and link['is_news'] for link in combo):
                            continue

                     total_val, news_val, reg_val = self.calculate_combination_value(combo)
                     if total_val >= target_points:
                          best_combo = combo
                          break
                if best_combo:
                     break

        if best_combo is None:
             self.report_results.config(state=tk.NORMAL)
             self.report_results.delete("1.0", tk.END)
             self.report_results.insert(tk.END, "Не удалось сформировать отчёт с текущими ограничениями и доступными ссылками.")
             self.report_results.config(state=tk.DISABLED)
             self.show_status("Не удалось сформировать отчёт.")
             return

        selected_urls = [link_info["url"] for link_info in best_combo]
        final_total_points, final_news_points, final_regular_points = self.calculate_combination_value(best_combo)

        for link_info in best_combo:
            ncs_key = link_info["ncs"]
            url_to_mark = link_info["url"]
            for link_obj in self.data[ncs_key]["links"]:
                if link_obj["url"] == url_to_mark:
                    link_obj["used"] = True
                    break
        self.save_data()
        self.update_top_stats()

        self.report_results.config(state=tk.NORMAL)
        self.report_results.delete("1.0", tk.END)
        result_text = f"--- Отчёт на {final_total_points} баллов (требовалось >= {target_points}) ---\n"
        result_text += f"Использовано {len(selected_urls)} ссылок.\n"
        result_text += f"Вклад от 'новостных' активностей (50%): {final_news_points} баллов.\n"
        result_text += f"Вклад от 'обычных' активностей: {final_regular_points} баллов.\n"
        result_text += "- Ссылки:\n"
        for url in selected_urls:
            result_text += f"  - {url}\n"
        result_text += "--- Конец отчёта ---"
        self.report_results.insert(tk.END, result_text)
        self.report_results.config(state=tk.DISABLED)
        self.show_status(f"Отчёт на {final_total_points} баллов сформирован и сохранён.")

    def update_statistics(self):
        """Updates the statistics tab."""
        self.update_top_stats()
        total_links = sum(len(info["links"]) for info in self.data.values())
        used_links = sum(1 for info in self.data.values() for link_obj in info["links"] if link_obj["used"])
        unused_links = total_links - used_links
        news_types = sum(1 for info in self.data.values() if info.get("is_news"))
        reg_types = len(self.data) - news_types
        active_types = sum(1 for info in self.data.values() if any(not link_obj["used"] for link_obj in info["links"]))

        stats_text = f"--- Статистика ---\n"
        stats_text += f"Всего типов активности: {len(self.data)} (Новостные: {news_types}, Обычные: {reg_types})\n"
        stats_text += f"Всего ссылок в базе: {total_links}\n"
        stats_text += f"Использовано ссылок: {used_links}\n"
        stats_text += f"Осталось неиспользованных ссылок: {unused_links}\n"
        stats_text += f"Количество типов с неиспользованными ссылками: {active_types}\n\n"
        stats_text += "Детализация по типам (баллы | тип | описание | всего_ссылок | неисп_ссылок):\n"

        for ncs_key, ncs_info in self.data.items():
            total_of_type = len(ncs_info["links"])
            unused_of_type = sum(1 for link_obj in ncs_info["links"] if not link_obj["used"])
            type_str = "Новость" if ncs_info.get("is_news") else "Обычная"
            stats_text += f"  [{ncs_info['points']:2d}] {type_str:8s} - {ncs_info['description']} | Всего: {total_of_type:2d}, Неисп.: {unused_of_type:2d}\n"

        self.stats_display.config(state=tk.NORMAL)
        self.stats_display.delete("1.0", tk.END)
        self.stats_display.insert(tk.END, stats_text)
        self.stats_display.config(state=tk.DISABLED)

    def update_top_stats(self):
        """Обновляет метки в верхней панели статистики."""
        total_points = 0
        total_links = 0
        used_links = 0

        for ncs_info in self.data.values():
            points_per_link = ncs_info["points"]
            links_count = len(ncs_info["links"])
            total_points += points_per_link * links_count
            total_links += links_count
            used_links += sum(1 for link_obj in ncs_info["links"] if link_obj["used"])

        unused_links = total_links - used_links

        self.total_points_label.config(text=f"Баллы: {total_points}")
        self.unused_links_label.config(text=f"Неисп.: {unused_links}")
        self.used_links_label.config(text=f"Исп.: {used_links}")

    def show_detail_stats(self, mode):
        """Показывает всплывающее окно с детализацией по типам."""
        details = []
        total_points = 0
        total_links = 0

        for ncs_key, ncs_info in self.data.items():
            points = ncs_info["points"]
            links = ncs_info["links"]
            count = len(links)
            used_count = sum(1 for l in links if l["used"])
            unused_count = count - used_count

            if mode == "total":
                details.append((ncs_info["description"], count, points * count))
                total_points += points * count
                total_links += count
            elif mode == "unused" and unused_count > 0:
                details.append((ncs_info["description"], unused_count, points * unused_count))
                total_points += points * unused_count
                total_links += unused_count
            elif mode == "used" and used_count > 0:
                details.append((ncs_info["description"], used_count, points * used_count))
                total_points += points * used_count
                total_links += used_count

        details.sort(key=lambda x: x[2], reverse=True)

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Детали: {mode}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        header = f"Всего: {total_links} ссылок | {total_points} баллов"
        ttk.Label(dialog, text=header, font=("TkDefaultFont", 10, "bold")).pack(pady=(5, 10))

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for desc, cnt, pts in details:
            row = ttk.Frame(scrollable_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=f"{desc[:30]}...", width=30).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{cnt:2d} шт.", width=8).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{pts:4d} б.", width=8).pack(side=tk.RIGHT)

        ttk.Button(dialog, text="Закрыть", command=dialog.destroy).pack(pady=10)


def main():
    root = tk.Tk()
    app = ActivityManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
