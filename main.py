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

        # --- Variables ---
        self.folder_path = tk.StringVar(value=self.config.get('Paths', 'folder_path', fallback=''))
        self.output_path = tk.StringVar(value=self.config.get('Paths', 'output_path', fallback=''))
        self.exclude_strings_var = tk.StringVar(value=self.config.get('Exclusions', 'exclude_strings', fallback=''))
        self.exclude_extensions_var = tk.StringVar(value=self.config.get('Exclusions', 'exclude_extensions', fallback=''))
        self.file_list_data = []
        self.file_type_dropdown_var = tk.StringVar(master, value=self.config.get('UI', 'last_filetype_filter', fallback='*'))

        # --- UI Layout ---

        # Row 0: Codebase Folder
        tk.Label(master, text="Codebase Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(master, textvariable=self.folder_path, width=50, state='readonly').grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        tk.Button(master, text="Browse Folder", command=self.browse_folder).grid(row=0, column=3, padx=5, pady=2)
        tk.Button(master, text="Analyze", command=self.analyze_folder).grid(row=0, column=4, padx=5, pady=2)

        # Row 1: Exclude Strings
        tk.Label(master, text="Exclude Strings (, separated):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(master, textvariable=self.exclude_strings_var, width=50).grid(row=1, column=1, columnspan=4, padx=5, pady=2, sticky="ew")

        # Row 2: Exclude Extensions
        tk.Label(master, text="Exclude Extensions (, separated):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(master, textvariable=self.exclude_extensions_var, width=50).grid(row=2, column=1, columnspan=4, padx=5, pady=2, sticky="ew")

        # File List Frame (Row 3)
        self.file_list_frame = tk.Frame(master)
        # Increased columnspan to 5 to account for the extra button column
        self.file_list_frame.grid(row=3, column=0, columnspan=5, sticky="nsew", padx=5, pady=5)
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

        # Row 4: Quick Select and Clear All
        tk.Label(master, text="Quick Select Filetype:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.filetype_dropdown = tk.OptionMenu(master, self.file_type_dropdown_var, "*")
        self.filetype_dropdown.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        tk.Button(master, text="Quick Select", command=self.quick_select).grid(row=4, column=2, padx=5, pady=2) # Moved Quick Select button
        tk.Button(master, text="Clear All", command=self.clear_all).grid(row=4, column=3, padx=5, pady=2) # Moved Clear All button

        # Row 5: Output Path and Export
        tk.Label(master, text="Output File:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(master, textvariable=self.output_path, width=50, state='readonly').grid(row=5, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        tk.Button(master, text="Browse Output", command=self.browse_output_path).grid(row=5, column=3, padx=5, pady=2)
        tk.Button(master, text="Export", command=self.export_files).grid(row=5, column=4, padx=5, pady=2)

        # Configure grid layout to be responsive
        master.grid_columnconfigure(1, weight=1) # Allow the main entry column to expand
        master.grid_rowconfigure(3, weight=1)    # Allow the file list row to expand
        self.file_list_frame.grid_columnconfigure(0, weight=1)
        # Removed row configure for frame as it contains the canvas which handles expansion

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Ensure default sections exist
            if 'Paths' not in self.config: self.config['Paths'] = {}
            if 'UI' not in self.config: self.config['UI'] = {'last_filetype_filter': '*'}
            if 'FileSelection' not in self.config: self.config['FileSelection'] = {}
            if 'Exclusions' not in self.config: self.config['Exclusions'] = {} # Add Exclusions section

    def save_settings(self):
        if 'Paths' not in self.config: self.config['Paths'] = {}
        if 'UI' not in self.config: self.config['UI'] = {}
        if 'FileSelection' not in self.config: self.config['FileSelection'] = {}
        if 'Exclusions' not in self.config: self.config['Exclusions'] = {} # Ensure section exists

        self.config['Paths']['folder_path'] = self.folder_path.get()
        self.config['Paths']['output_path'] = self.output_path.get()
        self.config['UI']['last_filetype_filter'] = self.file_type_dropdown_var.get()
        self.config['Exclusions']['exclude_strings'] = self.exclude_strings_var.get()
        self.config['Exclusions']['exclude_extensions'] = self.exclude_extensions_var.get()


        selected_files = [file_info['path'] for file_info in self.file_list_data if file_info['var'].get() == 1]
        # Only save selected files if the folder hasn't changed since last analysis that produced the current file_list_data
        # This prevents saving selections for a different folder if analyze wasn't run after changing folder
        # A more robust check might involve storing the analyzed folder path in config too.
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
            # Optionally clear selections when folder changes, or rely on Analyze to repopulate/reselect
            self.file_list_data = []
            self.clear_file_list_ui()
            self.update_filetype_dropdown([])
            # Clear previous selections in config if folder changes? Maybe not, user might want them if they switch back.
            # Let's clear the UI selection state only.
            self.clear_all() # Clears the Checkbutton variables


    def load_blacklist(self):
        blacklist_file = "blacklisted_paths.txt"
        blacklist = []
        if os.path.exists(blacklist_file):
            try:
                with open(blacklist_file, 'r') as f:
                    for line in f:
                        # Ignore empty lines and comments
                        cleaned_line = line.strip()
                        if cleaned_line and not cleaned_line.startswith('#'):
                            blacklist.append(cleaned_line)
            except Exception as e:
                messagebox.showwarning("Blacklist Warning", f"Could not read blacklist file {blacklist_file}:\n{e}")
        return blacklist

    def analyze_folder(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a codebase folder first.")
            return

        # Get exclusion criteria before starting walk
        exclude_strings_raw = self.exclude_strings_var.get()
        exclude_extensions_raw = self.exclude_extensions_var.get()

        exclude_strings = [s.strip() for s in exclude_strings_raw.split(',') if s.strip()]
        # Normalize extensions: remove leading dot and make lowercase for case-insensitive comparison
        exclude_extensions = [e.strip().lstrip('.').lower() for e in exclude_extensions_raw.split(',') if e.strip()]

        self.clear_file_list_ui()
        self.file_list_data = []
        file_types = set(["*"])
        blacklist = self.load_blacklist()

        # Load previously selected files *before* the loop if we want to preserve selection
        previously_selected_files = set()
        if self.config.get('Paths', 'folder_path', fallback='') == folder:
            selected_files_str = self.config.get('FileSelection', 'selected_files', fallback='')
            previously_selected_files = set(selected_files_str.split(',')) if selected_files_str else set()


        for root, dirs, files in os.walk(folder, topdown=True):
             # --- Directory Exclusion ---
             # Exclude directories based on blacklist
             dirs[:] = [d for d in dirs if not any(blacklisted_path in os.path.join(os.path.relpath(root, folder), d) for blacklisted_path in blacklist)]
             # Exclude directories based on exclude_strings
             dirs[:] = [d for d in dirs if not any(exclude_str in os.path.join(os.path.relpath(root, folder), d) for exclude_str in exclude_strings)]

             for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, folder)
                # Normalize path separators for consistent matching
                relative_path = relative_path.replace('\\', '/')

                # --- File Exclusion Checks ---

                # 1. Blacklist Check
                is_blacklisted = False
                for blacklisted_path in blacklist:
                    if blacklisted_path in relative_path:
                        is_blacklisted = True
                        break
                if is_blacklisted:
                    continue # Skip this file

                # 2. Exclude Strings Check
                is_excluded_by_string = False
                for exclude_str in exclude_strings:
                    if exclude_str in relative_path:
                        is_excluded_by_string = True
                        break
                if is_excluded_by_string:
                    continue # Skip this file

                # 3. Exclude Extensions Check
                _file_name, file_extension = os.path.splitext(file)
                normalized_extension = file_extension.lstrip('.').lower() # Get extension, remove dot, lowercase

                if normalized_extension in exclude_extensions:
                    continue # Skip this file

                # --- If not excluded, add to list ---
                var = tk.IntVar()
                # Restore selection state if it was previously selected
                if relative_path in previously_selected_files:
                    var.set(1)

                self.file_list_data.append({'path': relative_path, 'var': var})

                # Add file type to dropdown options (use normalized extension)
                actual_file_type = normalized_extension if normalized_extension else "no_extension" # Handle files with no extension
                file_types.add(actual_file_type)


        # --- Update UI after walk ---
        for index, file_info in enumerate(self.file_list_data):
            frame = tk.Frame(self.file_list_scrollable_frame)
            frame.pack(fill='x', padx=2, pady=1)
            tk.Checkbutton(
                frame, text=file_info['path'], variable=file_info['var'], anchor="w"
            ).pack(
                side='left', fill='x', expand=True
            )

        def update_scroll_region():
            self.file_list_canvas.update_idletasks() # Ensure layout is calculated
            self.file_list_canvas.configure(scrollregion=self.file_list_canvas.bbox("all"))

        self.master.after(100, update_scroll_region) # Schedule update after UI settles

        # Sort file types, ensure '*' is first if present
        sorted_types = sorted(list(file_types))
        if "*" in sorted_types:
             sorted_types.remove("*")
             sorted_types.insert(0, "*")

        self.update_filetype_dropdown(sorted_types)
        # Try to restore last used filter, fallback to '*'
        last_filter = self.config.get('UI', 'last_filetype_filter', fallback='*')
        if last_filter in sorted_types:
             self.file_type_dropdown_var.set(last_filter)
        elif sorted_types:
             self.file_type_dropdown_var.set(sorted_types[0]) # Default to first available type if last is invalid
        else:
             self.file_type_dropdown_var.set('*') # Should not happen if analyze ran, but safeguard


    def clear_file_list_ui(self):
        for widget in self.file_list_scrollable_frame.winfo_children():
            widget.destroy()
        # Reset scroll region when clearing
        self.file_list_canvas.configure(scrollregion=(0, 0, 0, 0))


    def update_filetype_dropdown(self, filetypes):
        menu = self.filetype_dropdown["menu"]
        menu.delete(0, "end")
        # Ensure '*' is always an option if we started with it
        # Or add it if analyze didn't find any files but we still need options
        if "*" not in filetypes and self.config.get('UI', 'last_filetype_filter', fallback='*') == '*':
             filetypes.insert(0,"*")
        elif not filetypes:
             filetypes = ["*"]


        current_selection = self.file_type_dropdown_var.get() # Store current selection attempt

        for filetype in filetypes:
            menu.add_command(label=filetype, command=tk._setit(self.file_type_dropdown_var, filetype))

        # Try to set the dropdown variable again after populating
        if current_selection in filetypes:
             self.file_type_dropdown_var.set(current_selection)
        elif filetypes:
             self.file_type_dropdown_var.set(filetypes[0]) # Default to first available type
        else:
             # This case should ideally not be reached if we ensure '*' is added above
             self.file_type_dropdown_var.set("*")

    def quick_select(self):
        selected_filetype = self.file_type_dropdown_var.get().lower() # Use lowercase for comparison
        if not self.file_list_data:
            return

        for file_info in self.file_list_data:
            if selected_filetype == "*":
                file_info['var'].set(1)
            else:
                # Use lowercase, normalized extension for matching
                file_extension = os.path.splitext(file_info['path'])[1].lstrip('.').lower()
                if file_extension == selected_filetype or (selected_filetype == "no_extension" and not file_extension):
                    file_info['var'].set(1)
                else:
                    file_info['var'].set(0) # Deselect non-matching files

    def clear_all(self):
        for file_info in self.file_list_data:
            file_info['var'].set(0)

    def browse_output_path(self):
        initial_name = os.path.basename(self.output_path.get() or "exported_code.txt")
        initial_dir = os.path.dirname(self.output_path.get() or self.folder_path.get() or ".") # Suggest output near input

        file_selected = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=initial_dir,
            initialfile=initial_name)
        if file_selected:
            self.output_path.set(file_selected)

    def export_files(self):
        output_file_path = self.output_path.get()
        if not output_file_path:
            messagebox.showerror("Error", "Please select an output file path.")
            return

        selected_files_content = ""
        folder = self.folder_path.get()

        if not folder or not os.path.isdir(folder): # Added check if folder still exists
            messagebox.showerror("Error", "Selected codebase folder is invalid or does not exist.")
            return

        selected_count = 0
        export_errors = []
        for file_info in self.file_list_data:
            if file_info['var'].get() == 1:
                selected_count += 1
                # Reconstruct full path using the base folder path at time of export
                full_file_path = os.path.join(folder, file_info['path'])
                try:
                    # Ensure file still exists before trying to open
                    if not os.path.exists(full_file_path):
                         raise FileNotFoundError(f"File not found: {file_info['path']}")

                    with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as f: # Added errors='ignore' for robustness
                        file_content = f.read()
                    # Use normalized path separator in the header
                    normalized_rel_path = file_info['path'].replace('\\', '/')
                    selected_files_content += f"-- BEGIN FILE: {normalized_rel_path} --\n"
                    selected_files_content += file_content + "\n"
                    selected_files_content += f"-- END FILE: {normalized_rel_path} --\n\n"
                except Exception as e:
                    error_msg = f"Could not read file: {file_info['path']}. Error: {e}"
                    export_errors.append(error_msg)
                    # Continue exporting other files, report errors at the end

        if export_errors:
             messagebox.showwarning("Export Warning", "Some files could not be read:\n\n" + "\n".join(export_errors))
             # Ask user if they want to proceed with partial export
             if not messagebox.askyesno("Continue Export?", "Errors occurred while reading some files. Do you want to export the files that were read successfully?"):
                  return # Abort export


        if selected_count == 0:
            messagebox.showinfo("Info", "No files were selected for export.")
            return
        if not selected_files_content and not export_errors:
             # This case might happen if all selected files failed to read and user chose not to continue
             messagebox.showinfo("Info", "No content to export after encountering read errors.")
             return

        try:
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(selected_files_content)

            success_message = f"Successfully exported {selected_count - len(export_errors)} out of {selected_count} selected files to:\n{output_file_path}"
            if export_errors:
                 success_message += f"\n({len(export_errors)} files failed to read - see previous warning)."
            messagebox.showinfo("Success", success_message)

        except Exception as e:
            messagebox.showerror("Error Writing File", f"Could not write to output file: {output_file_path}. Error: {e}")

        self.save_settings() # Save settings after a successful or partially successful export attempt


if __name__ == '__main__':
    root = tk.Tk()
    app = CodeExporterUI(root)
    root.mainloop()