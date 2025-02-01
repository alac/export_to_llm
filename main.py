import tkinter as tk
from tkinter import filedialog, messagebox
import os
import configparser


class CodeExporterUI:
    def __init__(self, master):
        self.master = master
        master.title("Codebase Exporter for LLM")

        self.config = configparser.ConfigParser()
        self.config_file = "code_exporter_config.ini"
        self.load_settings()

        self.folder_path = tk.StringVar(value=self.config.get('Paths', 'folder_path', fallback=''))
        self.output_path = tk.StringVar(value=self.config.get('Paths', 'output_path', fallback=''))
        self.file_list_data = []
        self.file_type_dropdown_var = tk.StringVar(master, value=self.config.get('UI', 'last_filetype_filter', fallback='*'))

        # Row 0: Codebase Folder
        tk.Label(master, text="Codebase Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(master, textvariable=self.folder_path, width=50, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse Folder", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        tk.Button(master, text="Analyze", command=self.analyze_folder).grid(row=0, column=3, padx=5, pady=5)

        # File List Frame (Row 1)
        self.file_list_frame = tk.Frame(master)
        self.file_list_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        self.file_list_canvas = tk.Canvas(self.file_list_frame)
        self.file_list_scrollbar = tk.Scrollbar(self.file_list_frame,
                                                orient="vertical",
                                                command=self.file_list_canvas.yview)
        self.file_list_scrollable_frame = tk.Frame(self.file_list_canvas)

        self.file_list_scrollbar.pack(side="right", fill="y")
        self.file_list_canvas.pack(side="left", fill="both", expand=True)
        self.file_list_canvas.configure(yscrollcommand=self.file_list_scrollbar.set)
        self.file_list_canvas.bind("<Configure>",
                                   lambda e: self.file_list_canvas.configure(
                                       scrollregion=self.file_list_canvas.bbox("all")
                                   ))
        self.file_list_canvas.create_window((0, 0), window=self.file_list_scrollable_frame, anchor="nw")

        # Row 2: Quick Select and Clear All
        tk.Label(master, text="Quick Select Filetype:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.filetype_dropdown = tk.OptionMenu(master, self.file_type_dropdown_var, "*")
        self.filetype_dropdown.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(master, text="Quick Select", command=self.quick_select).grid(row=2, column=2, padx=5, pady=5)
        tk.Button(master, text="Clear All", command=self.clear_all).grid(row=2, column=3, padx=5, pady=5)

        # Row 3: Output Path and Export
        tk.Label(master, text="Output File:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(master, textvariable=self.output_path, width=50, state='readonly').grid(row=3, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse Output", command=self.browse_output_path).grid(row=3, column=2, padx=5, pady=5)
        tk.Button(master, text="Export", command=self.export_files).grid(row=3, column=3, padx=5, pady=5)

        # Configure grid layout to be responsive
        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(1, weight=1)
        self.file_list_frame.grid_columnconfigure(0, weight=1)
        self.file_list_frame.grid_rowconfigure(0, weight=1)

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['Paths'] = {}
            self.config['UI'] = {'last_filetype_filter': '*'}
            self.config['FileSelection'] = {}

    def save_settings(self):
        self.config['Paths']['folder_path'] = self.folder_path.get()
        self.config['Paths']['output_path'] = self.output_path.get()
        self.config['UI']['last_filetype_filter'] = self.file_type_dropdown_var.get()

        selected_files = [file_info['path'] for file_info in self.file_list_data if file_info['var'].get() == 1]
        self.config['FileSelection']['selected_files'] = ",".join(selected_files)

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def on_closing(self):
        self.save_settings()
        self.master.destroy()

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.folder_path.get() or ".")
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.file_list_data = []
            self.clear_file_list_ui()
            self.update_filetype_dropdown([])

    def load_blacklist(self):
        blacklist_file = "blacklisted_paths.txt"
        blacklist = []
        if os.path.exists(blacklist_file):
            with open(blacklist_file, 'r') as f:
                for line in f:
                    blacklist.append(line.strip())
        return blacklist

    def analyze_folder(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a codebase folder first.")
            return

        self.clear_file_list_ui()
        self.file_list_data = []
        file_types = set(["*"])
        blacklist = self.load_blacklist()

        for root, _, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, folder)

                is_blacklisted = False
                for blacklisted_path in blacklist:
                    if blacklisted_path in relative_path:
                        is_blacklisted = True
                        break
                if is_blacklisted:
                    continue

                var = tk.IntVar()
                self.file_list_data.append({'path': relative_path, 'var': var})
                file_type = os.path.splitext(file)[1].lstrip('.') or "*"
                if file_type:
                    file_types.add(file_type)

        if self.config.get('Paths', 'folder_path', fallback='') == folder:
            selected_files_str = self.config.get('FileSelection', 'selected_files', fallback='')
            previously_selected_files = set(selected_files_str.split(',')) if selected_files_str else set()
            for file_info in self.file_list_data:
                if file_info['path'] in previously_selected_files:
                    file_info['var'].set(1)

        for index, file_info in enumerate(self.file_list_data):
            frame = tk.Frame(self.file_list_scrollable_frame)
            frame.pack(fill='x', padx=2, pady=1)
            tk.Checkbutton(
                frame, text=file_info['path'], variable=file_info['var'], anchor="w"
            ).pack(
                side='left', fill='x', expand=True
            )

        def update_scroll_region():
            self.file_list_canvas.configure(scrollregion=self.file_list_canvas.bbox("all"))

        self.master.after(100, update_scroll_region)
        self.update_filetype_dropdown(sorted(list(file_types)))
        self.file_type_dropdown_var.set(self.config.get('UI', 'last_filetype_filter', fallback='*'))

    def clear_file_list_ui(self):
        for widget in self.file_list_scrollable_frame.winfo_children():
            widget.destroy()

    def update_filetype_dropdown(self, filetypes):
        menu = self.filetype_dropdown["menu"]
        menu.delete(0, "end")
        for filetype in filetypes:
            menu.add_command(label=filetype, command=tk._setit(self.file_type_dropdown_var, filetype))

        if filetypes:
            default_type = self.config.get('UI', 'last_filetype_filter', fallback='*')
            if default_type in filetypes or default_type == '*':
                self.file_type_dropdown_var.set(default_type)
            else:
                self.file_type_dropdown_var.set(
                    filetypes[0] if "*" in filetypes else filetypes[0] if filetypes else "*")

    def quick_select(self):
        selected_filetype = self.file_type_dropdown_var.get()
        if not self.file_list_data:
            return

        for file_info in self.file_list_data:
            if selected_filetype == "*":
                file_info['var'].set(1)
            else:
                file_extension = os.path.splitext(file_info['path'])[1].lstrip('.')
                if file_extension == selected_filetype:
                    file_info['var'].set(1)
                else:
                    file_info['var'].set(0)
        self.save_settings()

    def clear_all(self):
        for file_info in self.file_list_data:
            file_info['var'].set(0)
        self.save_settings()

    def browse_output_path(self):
        file_selected = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=self.output_path.get() or "exported_code.txt")
        if file_selected:
            self.output_path.set(file_selected)

    def export_files(self):
        output_file_path = self.output_path.get()
        if not output_file_path:
            messagebox.showerror("Error", "Please select an output file path.")
            return

        selected_files_content = ""
        folder = self.folder_path.get()

        if not folder:
            messagebox.showerror("Error", "Please select a codebase folder first.")
            return

        selected_count = 0
        for file_info in self.file_list_data:
            if file_info['var'].get() == 1:
                selected_count += 1
                full_file_path = os.path.join(folder, file_info['path'])
                try:
                    with open(full_file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    selected_files_content += f"-- BEGIN FILE: {file_info['path']} --\n"
                    selected_files_content += file_content + "\n"
                    selected_files_content += f"-- END FILE: {file_info['path']} --\n\n"
                except Exception as e:
                    messagebox.showerror("Error Reading File", f"Could not read file: {file_info['path']}. Error: {e}")
                    return # Stop export if any file read fails

        if not selected_files_content:
            messagebox.showinfo("Info", "No files selected for export.")
            return

        try:
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(selected_files_content)
            messagebox.showinfo("Success", f"Successfully exported {selected_count} files to:\n{output_file_path}")
        except Exception as e:
            messagebox.showerror("Error Writing File", f"Could not write to output file: {output_file_path}. Error: {e}")

        self.save_settings() # Save settings after export (including file selection at time of export)


if __name__ == '__main__':
    root = tk.Tk()
    app = CodeExporterUI(root)
    root.mainloop()
