import tkinter as tk
from tkinter import ttk, messagebox


class IterationDialog:
    """Diálogo para configurar iteraciones máximas"""
    def __init__(self, parent, current_iterations):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configurar Iteraciones")
        self.dialog.geometry("360x200")
        self.dialog.minsize(320, 180)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 300) // 2
        y = parent_y + (parent_h - 160) // 2
        self.dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Número máximo de iteraciones:", font=("Arial", 10)).pack(pady=(0, 5))

        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(pady=5)

        self.entry = ttk.Entry(entry_frame, justify=tk.CENTER, width=10, font=("Arial", 11))
        self.entry.pack(side=tk.LEFT, padx=(0, 5))
        self.entry.insert(0, str(current_iterations))

        ttk.Label(entry_frame, text="iteraciones").pack(side=tk.LEFT)

        ttk.Label(main_frame, text="(mínimo: 2, recomendado: 10-100)", font=("Arial", 8), foreground="gray").pack(pady=5)

        preset_frame = ttk.LabelFrame(main_frame, text="Presets rápidos", padding="5")
        preset_frame.pack(fill=tk.X, pady=10)
        preset_buttons = ttk.Frame(preset_frame)
        preset_buttons.pack()
        for value in [10, 25, 50, 100]:
            ttk.Button(preset_buttons, text=str(value), width=6, command=lambda v=value: self.set_preset(v)).pack(side=tk.LEFT, padx=2)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        ttk.Button(button_frame, text="Aceptar", command=self.accept).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancel).pack(side=tk.RIGHT)

        self.entry.focus()
        self.entry.select_range(0, tk.END)
        self.entry.bind("<Return>", lambda e: self.accept())
        self.dialog.bind("<Escape>", lambda e: self.cancel())

    def set_preset(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(value))
        self.entry.focus()

    def accept(self):
        try:
            value = int(self.entry.get())
            if value < 2:
                raise ValueError("El valor debe ser mayor o igual a 2")
            if value > 10000:
                raise ValueError("El valor no puede ser mayor a 10000")
            self.result = value
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
            self.entry.focus()
            self.entry.select_range(0, tk.END)

    def cancel(self):
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result


