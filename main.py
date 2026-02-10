#!/usr/bin/env python3
"""
FCM Designer Python
Punto de entrada principal de la aplicación
Migrado desde FCM.java
"""

import tkinter as tk
from tkinter import messagebox
from interface.map_window import MapWindow


class FCMDesignerApp:
    """Aplicación principal FCM Designer"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FCM Designer - Python Version")
        self.root.geometry("300x200")
        self.root.resizable(False, False)
        
        # Centrar ventana
        self.root.eval('tk::PlaceWindow . center')
        
        self.setup_interface()
    
    def setup_interface(self):
        """Configura la interfaz inicial"""
        # Título
        title_label = tk.Label(
            self.root, 
            text="FCM Designer", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)
        
        # Subtítulo
        subtitle_label = tk.Label(
            self.root, 
            text="Seleccione el tipo de mapa a crear:",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Botones
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        fcm_btn = tk.Button(
            btn_frame,
            text="Nuevo FCM\n(Estático)",
            width=15,
            height=2,
            command=lambda: self.create_window(False)
        )
        fcm_btn.pack(side=tk.LEFT, padx=10)
        
        dfcm_btn = tk.Button(
            btn_frame,
            text="Nuevo DFCM\n(Dinámico)", 
            width=15,
            height=2,
            command=lambda: self.create_window(True)
        )
        dfcm_btn.pack(side=tk.LEFT, padx=10)
        
        # Botón salir
        exit_btn = tk.Button(
            self.root,
            text="Salir",
            width=10,
            command=self.root.quit
        )
        exit_btn.pack(pady=20)
    
    def create_window(self, dynamic: bool):
        """Crea una nueva ventana de mapa"""
        try:
            window = MapWindow(dynamic)
            window.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear ventana: {e}")
    
    def run(self):
        """Ejecuta la aplicación"""
        self.root.mainloop()


if __name__ == "__main__":
    app = FCMDesignerApp()
    app.run()

    