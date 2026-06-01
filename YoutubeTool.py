import tkinter as tk
from tkinter import messagebox

root = tk.Tk()
root.withdraw()  # Ẩn cửa sổ chính

messagebox.showinfo("Thông báo", "Vui lòng không Reup")

root.destroy()
