import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import threading
import datetime

#  Настройки приложения
API_URL = "https://api.exchangerate.host/latest?base=USD"  # Стабильный и бесплатный API
HISTORY_VAL_FILE = "history_val.json"


class CurrencyConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Конвертер валют")
        self.root.geometry("650x500")
        self.root.resizable(False, False)

        # Данные приложения
        self.rates = {}
        self.currencies = ["USD", "EUR", "GBP", "JPY", "CNY", "RUB", "CHF"]
        self.history_val = self.load_history_val()

        # Создаем интерфейс
        self.create_widgets()

        # Загружаем курсы валют при запуске в отдельном потоке
        self.fetch_rates()

    def create_widgets(self):
        #  Рамка для ввода данных
        input_frame = ttk.LabelFrame(self.root, text="Конвертация", padding=(10, 5))
        input_frame.pack(pady=10, padx=10, fill="x")

        # Валюта "Из"
        ttk.Label(input_frame, text="Из:").grid(row=0, column=0, sticky="e", padx=5)
        self.from_var = tk.StringVar(value="USD")
        self.from_combo = ttk.Combobox(input_frame, textvariable=self.from_var,
                                       values=self.currencies, state="readonly", width=6)
        self.from_combo.grid(row=0, column=1, sticky="w")

        # Валюта "В"
        ttk.Label(input_frame, text="В:").grid(row=0, column=2, sticky="e", padx=(20, 5))
        self.to_var = tk.StringVar(value="RUB")
        self.to_combo = ttk.Combobox(input_frame, textvariable=self.to_var,
                                     values=self.currencies, state="readonly", width=6)
        self.to_combo.grid(row=0, column=3, sticky="w")

        # Поле для суммы
        ttk.Label(input_frame, text="Сумма:").grid(row=1, column=0, sticky="e", padx=5)
        self.amount_entry = ttk.Entry(input_frame)
        self.amount_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5)

        # Кнопка конвертации (изначально заблокирована до загрузки курсов)
        self.convert_btn = ttk.Button(input_frame, text="Конвертировать", command=self.start_conversion_thread)
        self.convert_btn.grid(row=2, column=0, columnspan=4, pady=10)

        #  Таблица истории
        history_val_frame = ttk.Frame(self.root)
        history_val_frame.pack(pady=(0, 10), padx=10, fill="both", expand=True)

        columns = ("date_time", "from_cur", "to_cur", "amount", "result")
        self.tree = ttk.Treeview(history_val_frame, columns=columns, show="headings")

        self.tree.heading("date_time", text="Время")
        self.tree.heading("from_cur", text="Из")
        self.tree.heading("to_cur", text="В")
        self.tree.heading("amount", text="Сумма")
        self.tree.heading("result", text="Результат")

        self.tree.column("date_time", width=150)
        self.tree.column("from_cur", width=70)
        self.tree.column("to_cur", width=70)
        self.tree.column("amount", width=80)
        self.tree.column("result", width=80)

        self.tree.pack(fill="both", expand=True)

    def fetch_rates(self):
        """Получает актуальные курсы валют с API."""

        def on_success():
            # Разблокируем кнопку после успешной загрузки данных
            self.convert_btn.config(state="normal")
            # Загружаем историю в таблицу после получения курсов (если она есть)
            if self.history_val:
                for entry in reversed(self.history_val):
                    self.update_history_val_table(entry)

        def on_error(error_msg):
            messagebox.showerror("Ошибка сети", error_msg)
            # Оставляем кнопку заблокированной при ошибке загрузки курсов

        try:
            response = requests.get(API_URL)
            response.raise_for_status()
            data = response.json()

            if 'rates' in data:
                self.rates = data['rates']
                # Обновляем список валют (на случай изменений в API)
                self.currencies = sorted(list(self.rates.keys()))

                # Обновляем виджеты в главном потоке Tkinter
                self.root.after(0, lambda: [self.from_combo.config(values=self.currencies),
                                            self.to_combo.config(values=self.currencies)])
                # Вызываем функцию успеха (разблокировка) в главном потоке
                self.root.after(0, on_success)
            else:
                raise Exception("Неверный формат данных от сервера.")

        except requests.RequestException as e:
            on_error(f"Проверьте подключение к интернету.\n{str(e)}")
        except Exception as e:
            on_error(f"Не удалось обработать данные.\n{str(e)}")

    def is_valid_amount(self):
        """Проверяет, является ли введенная сумма положительным числом."""
        value = self.amount_entry.get()
        try:
            amount = float(value)
            return amount > 0
        except ValueError:
            return False

    def start_conversion_thread(self):
        """Запускает процесс конвертации в отдельном потоке."""
        if not self.is_valid_amount():
            messagebox.showwarning("Ошибка ввода", "Пожалуйста, введите положительное число.")
            return

        if not self.rates:
            messagebox.showwarning("Нет данных", "Курсы валют еще не загружены. Пожалуйста, подождите.")
            return

        # Блокируем кнопку во время вычислений
        self.convert_btn.config(state="disabled")

        threading.Thread(target=self.perform_conversion).start()

    def perform_conversion(self):
        """Выполняет расчет конвертации и сохраняет результат."""

        from_cur = self.from_var.get()
        to_cur = self.to_var.get()
        amount = float(self.amount_entry.get())

        #  ИСПРАВЛЕННАЯ ЛОГИКА ПЕРЕСЧЕТА
        # 1. Переводим исходную валюту в USD (базу API)
        if from_cur == 'USD':
            amount_in_usd = amount
        else:
            amount_in_usd = amount / self.rates[from_cur]

        # 2. Переводим USD в целевую валюту
        if to_cur == 'USD':
            result = amount_in_usd
        else:
            result = amount_in_usd * self.rates[to_cur]

        result = round(result, 2)

        entry = {
            "date_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from": from_cur,
            "to": to_cur,
            "amount": amount,
            "result": result,
        }

        # Добавляем в историю и сохраняем в файл
        self.history_val.append(entry)
        self.save_history_val()

        # Обновляем таблицу в главном потоке Tkinter (это безопасно)
        self.root.after(0, lambda: self.update_history_val_table(entry))

        # Разблокируем кнопку после завершения операции
        self.root.after(0, lambda: self.convert_btn.config(state="normal"))

    def update_history_val_table(self, entry):
        """Добавляет новую строку в таблицу истории."""
        self.tree.insert("", tk.END, values=(
            entry["date_time"],
            entry["from"],
            entry["to"],
            entry["amount"],
            entry["result"]
        ))
        # Прокручиваем таблицу вниз к последней записи
        self.tree.yview_moveto(1.0)

    def load_history_val(self):
        """Загружает историю из файла JSON при запуске программы."""
        try:
            with open(HISTORY_VAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_history_val(self):
        """Сохраняет историю в файл JSON."""
        with open(HISTORY_VAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history_val, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    root = tk.Tk()
    app = CurrencyConverterApp(root)
    root.mainloop()

