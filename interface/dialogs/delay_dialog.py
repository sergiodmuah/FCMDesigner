import tkinter as tk
from tkinter import ttk, messagebox


class DelayDialog:
    """Diálogo para configurar retardo"""
    def __init__(self, parent, current_delay):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configurar Retardo")
        self.dialog.geometry("340x180")
        self.dialog.minsize(320, 160)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 280) // 2
        y = parent_y + (parent_h - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Retardo entre iteraciones:", font=("Arial", 10)).pack(pady=(0, 5))

        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(pady=5)

        self.entry = ttk.Entry(entry_frame, justify=tk.CENTER, width=10, font=("Arial", 11))
        self.entry.pack(side=tk.LEFT, padx=(0, 5))
        self.entry.insert(0, str(current_delay))

        ttk.Label(entry_frame, text="milisegundos").pack(side=tk.LEFT)

        ttk.Label(main_frame, text="(0 = sin retardo, recomendado: 100-500)", font=("Arial", 8), foreground="gray").pack(pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))

        ttk.Button(button_frame, text="Aceptar", command=self.accept).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancel).pack(side=tk.RIGHT)

        self.entry.focus()
        self.entry.select_range(0, tk.END)
        self.entry.bind("<Return>", lambda e: self.accept())
        self.dialog.bind("<Escape>", lambda e: self.cancel())

    def accept(self):
        try:
            value = int(self.entry.get())
            if value < 0:
                raise ValueError("El valor debe ser mayor o igual a 0")
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


