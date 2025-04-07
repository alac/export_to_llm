import tkinter as tk
from tkinter import filedialog, messagebox
import os
import configparser
import json

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
        self.file_list_data = [] # Stores {'path': relative_path, 'var': tk.IntVar()}
        self.analyzed_files_cache = [] # Stores just the relative paths from the last analysis
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
        tk.Button(master, text="Quick Select", command=self.quick_select).grid(row=4, column=2, padx=5, pady=2)
        tk.Button(master, text="Clear All", command=self.clear_all).grid(row=4, column=3, padx=5, pady=2)

        # Row 5: Output Path and Export
        tk.Label(master, text="Output File:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(master, textvariable=self.output_path, width=50, state='readonly').grid(row=5, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        tk.Button(master, text="Browse Output", command=self.browse_output_path).grid(row=5, column=3, padx=5, pady=2)
        tk.Button(master, text="Export", command=self.export_files).grid(row=5, column=4, padx=5, pady=2)

        # --- NEW: Row 6: Save/Load State ---
        tk.Button(master, text="Save State", command=self.save_state).grid(row=6, column=1, padx=5, pady=5, sticky="e")
        tk.Button(master, text="Load State", command=self.load_state).grid(row=6, column=2, padx=5, pady=5, sticky="w")
        # --- End New Row ---

        # Configure grid layout to be responsive
        master.grid_columnconfigure(1, weight=1) # Allow the main entry column to expand
        master.grid_rowconfigure(3, weight=1)    # Allow the file list row to expand
        self.file_list_frame.grid_columnconfigure(0, weight=1)

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        """Loads general app settings (last used paths, etc.) from INI."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Ensure default sections exist
            if 'Paths' not in self.config: self.config['Paths'] = {}
            if 'UI' not in self.config: self.config['UI'] = {'last_filetype_filter': '*'}
            # Removed FileSelection load here - it's only relevant for auto-close saving
            if 'Exclusions' not in self.config: self.config['Exclusions'] = {}

    def save_settings(self):
        """Saves the *last used* general settings to INI on closing."""
        if 'Paths' not in self.config: self.config['Paths'] = {}
        if 'UI' not in self.config: self.config['UI'] = {}
        if 'Exclusions' not in self.config: self.config['Exclusions'] = {}

        self.config['Paths']['folder_path'] = self.folder_path.get()
        self.config['Paths']['output_path'] = self.output_path.get()
        self.config['UI']['last_filetype_filter'] = self.file_type_dropdown_var.get()
        self.config['Exclusions']['exclude_strings'] = self.exclude_strings_var.get()
        self.config['Exclusions']['exclude_extensions'] = self.exclude_extensions_var.get()

        # Intentionally NOT saving file selections here anymore.
        # Let explicit Save State handle selections for specific projects.
        # We could optionally save last selections for the last folder, but
        # it complicates things with the new Save/Load State feature.
        # Keeping it simple: INI saves *last used non-selection state*.
        if 'FileSelection' in self.config:
             del self.config['FileSelection'] # Clean up old section if present

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def on_closing(self):
        self.save_settings() # Save general settings
        self.master.destroy()

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.folder_path.get() or ".")
        if folder_selected:
            self.folder_path.set(folder_selected)
            # Clear previous analysis results when folder changes
            self.file_list_data = []
            self.analyzed_files_cache = []
            self.clear_file_list_ui()
            self.update_filetype_dropdown([])
            self.clear_all()

    def load_blacklist(self):
        blacklist_file = "blacklisted_paths.txt"
        blacklist = []
        if os.path.exists(blacklist_file):
            try:
                with open(blacklist_file, 'r') as f:
                    for line in f:
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

        exclude_strings_raw = self.exclude_strings_var.get()
        exclude_extensions_raw = self.exclude_extensions_var.get()
        exclude_strings = [s.strip() for s in exclude_strings_raw.split(',') if s.strip()]
        exclude_extensions = [e.strip().lstrip('.').lower() for e in exclude_extensions_raw.split(',') if e.strip()]

        self.clear_file_list_ui()
        self.file_list_data = []
        self.analyzed_files_cache = [] # Clear cache before analysis
        file_types = set(["*"])
        blacklist = self.load_blacklist()

        # No need to load previous selections from INI anymore
        # previously_selected_files = set()

        try: # Wrap os.walk in try-except for permission errors etc.
            for root, dirs, files in os.walk(folder, topdown=True):
                 # --- Directory Exclusion ---
                 dirs[:] = [d for d in dirs if not any(blacklisted_path in os.path.join(os.path.relpath(root, folder), d).replace('\\', '/') for blacklisted_path in blacklist)]
                 dirs[:] = [d for d in dirs if not any(exclude_str in os.path.join(os.path.relpath(root, folder), d).replace('\\', '/') for exclude_str in exclude_strings)]

                 for file in files:
                    try: # Handle potential errors getting path info
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, folder)
                        relative_path = relative_path.replace('\\', '/') # Normalize
                    except Exception as e:
                         print(f"Skipping file due to path error: {e}") # Log error
                         continue

                    # --- File Exclusion Checks ---
                    is_blacklisted = any(blacklisted_path in relative_path for blacklisted_path in blacklist)
                    if is_blacklisted: continue

                    is_excluded_by_string = any(exclude_str in relative_path for exclude_str in exclude_strings)
                    if is_excluded_by_string: continue

                    _file_name, file_extension = os.path.splitext(file)
                    normalized_extension = file_extension.lstrip('.').lower()
                    if normalized_extension in exclude_extensions: continue

                    # --- If not excluded, add to list ---
                    var = tk.IntVar(value=0) # Default to not selected
                    self.file_list_data.append({'path': relative_path, 'var': var})
                    self.analyzed_files_cache.append(relative_path) # Add path to cache

                    actual_file_type = normalized_extension if normalized_extension else "no_extension"
                    file_types.add(actual_file_type)

        except OSError as e:
             messagebox.showerror("Folder Error", f"Error walking the directory: {e}\nCheck permissions or folder path.")
             return # Stop analysis if walk fails

        # --- Update UI after walk ---
        self._populate_file_list_ui(self.file_list_data) # Use helper method

        # Sort file types, ensure '*' is first
        sorted_types = sorted(list(file_types))
        if "*" in sorted_types:
             sorted_types.remove("*")
             sorted_types.insert(0, "*")
        self.update_filetype_dropdown(sorted_types)

        # Try to restore last used filter from general config
        last_filter = self.config.get('UI', 'last_filetype_filter', fallback='*')
        if last_filter in sorted_types:
             self.file_type_dropdown_var.set(last_filter)
        elif sorted_types:
             self.file_type_dropdown_var.set(sorted_types[0])
        else:
             self.file_type_dropdown_var.set('*')

    def _populate_file_list_ui(self, file_data_list):
        """Helper to populate the scrollable frame from file_data_list."""
        self.clear_file_list_ui()
        for file_info in file_data_list:
            frame = tk.Frame(self.file_list_scrollable_frame)
            frame.pack(fill='x', padx=2, pady=1)
            tk.Checkbutton(
                frame, text=file_info['path'], variable=file_info['var'], anchor="w"
            ).pack(side='left', fill='x', expand=True)

        # Schedule scroll region update
        self.master.after(50, self._update_scroll_region)

    def _update_scroll_region(self):
        """Updates the scrollregion of the file list canvas."""
        self.file_list_canvas.update_idletasks() # Ensure layout is calculated
        self.file_list_canvas.configure(scrollregion=self.file_list_canvas.bbox("all"))


    def clear_file_list_ui(self):
        for widget in self.file_list_scrollable_frame.winfo_children():
            widget.destroy()
        # Reset scroll region when clearing
        self.file_list_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.file_list_canvas.yview_moveto(0) # Scroll back to top

    def update_filetype_dropdown(self, filetypes):
        menu = self.filetype_dropdown["menu"]
        menu.delete(0, "end")

        # Ensure '*' is always an option, especially if list is empty
        if not filetypes:
             filetypes = ["*"]
        elif "*" not in filetypes:
             filetypes.insert(0,"*")

        current_selection = self.file_type_dropdown_var.get()

        for filetype in filetypes:
            # Use lambda to pass the value correctly
            menu.add_command(label=filetype, command=lambda ft=filetype: self.file_type_dropdown_var.set(ft))

        # Try to set the dropdown variable again
        if current_selection in filetypes:
             self.file_type_dropdown_var.set(current_selection)
        elif filetypes:
             self.file_type_dropdown_var.set(filetypes[0])
        else:
             self.file_type_dropdown_var.set("*")


    def quick_select(self):
        selected_filetype = self.file_type_dropdown_var.get().lower()
        if not self.file_list_data:
            return

        for file_info in self.file_list_data:
            if selected_filetype == "*":
                file_info['var'].set(1)
            else:
                file_extension = os.path.splitext(file_info['path'])[1].lstrip('.').lower()
                should_select = (file_extension == selected_filetype or
                                 (selected_filetype == "no_extension" and not file_extension))
                file_info['var'].set(1 if should_select else 0)

    def clear_all(self):
        for file_info in self.file_list_data:
            file_info['var'].set(0)

    def browse_output_path(self):
        initial_name = os.path.basename(self.output_path.get() or "exported_code.txt")
        initial_dir = os.path.dirname(self.output_path.get() or self.folder_path.get() or ".")

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

        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Selected codebase folder is invalid or does not exist.")
            return

        selected_count = 0
        exported_count = 0
        export_errors = []
        for file_info in self.file_list_data:
            if file_info['var'].get() == 1:
                selected_count += 1
                full_file_path = os.path.join(folder, file_info['path'])
                try:
                    if not os.path.exists(full_file_path):
                         raise FileNotFoundError(f"File not found: {file_info['path']}")

                    with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                    normalized_rel_path = file_info['path'].replace('\\', '/')
                    selected_files_content += f"-- BEGIN FILE: {normalized_rel_path} --\n"
                    selected_files_content += file_content + "\n"
                    selected_files_content += f"-- END FILE: {normalized_rel_path} --\n\n"
                    exported_count += 1 # Count successfully added content
                except Exception as e:
                    error_msg = f"Could not read file: {file_info['path']}. Error: {e}"
                    export_errors.append(error_msg)

        if export_errors:
             # Shorten message if many errors
             error_summary = "\n".join(export_errors[:5]) + ("\n..." if len(export_errors) > 5 else "")
             messagebox.showwarning("Export Warning", f"{len(export_errors)} file(s) could not be read:\n\n{error_summary}")
             if exported_count == 0: # All selected files failed
                  messagebox.showerror("Export Failed", "None of the selected files could be read. Aborting export.")
                  return
             if not messagebox.askyesno("Continue Export?", f"Errors occurred. Export the {exported_count} successfully read file(s)?"):
                  return

        if selected_count == 0:
            messagebox.showinfo("Info", "No files were selected for export.")
            return
        if exported_count == 0 and not export_errors:
             messagebox.showinfo("Info", "No files selected or no content to export.")
             return
        if not selected_files_content and exported_count > 0:
             # This might happen if files were empty, which is unlikely but possible
             messagebox.showwarning("Info", "Selected files appear to be empty. Output file will be created but may be empty.")


        try:
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(selected_files_content)

            success_message = f"Successfully exported {exported_count} file(s) to:\n{output_file_path}"
            if export_errors:
                 success_message += f"\n({len(export_errors)} selected file(s) failed to read)."
            messagebox.showinfo("Success", success_message)

        except Exception as e:
            messagebox.showerror("Error Writing File", f"Could not write to output file: {output_file_path}. Error: {e}")

        # We no longer save settings automatically after export. Use Save State explicitly.
        # self.save_settings()

    # --- NEW: Save State Method ---
    def save_state(self):
        """Saves the current UI state (paths, exclusions, selections) to a JSON file."""
        if not self.folder_path.get() or not self.analyzed_files_cache:
            messagebox.showwarning("Save State", "Please select and analyze a folder before saving state.")
            return

        # Suggest filename based on folder name
        folder_name = os.path.basename(self.folder_path.get().rstrip('/\\'))
        initial_filename = f"{folder_name}.llmexport"
        initial_dir = self.folder_path.get() # Suggest saving in the project folder itself

        state_filepath = filedialog.asksaveasfilename(
            title="Save Exporter State",
            initialdir=initial_dir,
            initialfile=initial_filename,
            defaultextension=".llmexport",
            filetypes=[("LLM Exporter State", "*.llmexport"), ("All Files", "*.*")]
        )

        if not state_filepath:
            return # User cancelled

        # Gather state data
        selected_files = [info['path'] for info in self.file_list_data if info['var'].get() == 1]

        state_data = {
            "version": 1, # For future compatibility
            "paths": {
                "folder_path": self.folder_path.get(),
                "output_path": self.output_path.get()
            },
            "exclusions": {
                "exclude_strings": self.exclude_strings_var.get(),
                "exclude_extensions": self.exclude_extensions_var.get()
            },
            "ui": {
                "last_filetype_filter": self.file_type_dropdown_var.get()
            },
            "analysis": {
                # Save the list of files found during the *last* analysis
                "analyzed_files": self.analyzed_files_cache,
                # Save the list of *currently* selected files
                "selected_files": selected_files
            }
        }

        try:
            with open(state_filepath, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=4) # Use indent for readability
            messagebox.showinfo("Save State", f"State successfully saved to:\n{state_filepath}")
        except Exception as e:
            messagebox.showerror("Save State Error", f"Failed to save state file: {e}")

    # --- NEW: Load State Method ---
    def load_state(self):
        """Loads UI state from a previously saved JSON file."""
        state_filepath = filedialog.askopenfilename(
            title="Load Exporter State",
            defaultextension=".llmexport",
            filetypes=[("LLM Exporter State", "*.llmexport"), ("All Files", "*.*")]
        )

        if not state_filepath:
            return # User cancelled

        try:
            with open(state_filepath, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Load State Error", "Selected state file not found.")
            return
        except json.JSONDecodeError:
            messagebox.showerror("Load State Error", "Invalid state file format (not valid JSON).")
            return
        except Exception as e:
             messagebox.showerror("Load State Error", f"Failed to read state file: {e}")
             return

        # --- Validate and Apply Loaded State ---
        try:
            # Check version (optional but good practice)
            if state_data.get("version") != 1:
                 messagebox.showwarning("Load State", "State file is from an incompatible version. Results may be unpredictable.")

            # Load Paths
            self.folder_path.set(state_data.get("paths", {}).get("folder_path", ""))
            self.output_path.set(state_data.get("paths", {}).get("output_path", ""))

            # Load Exclusions
            self.exclude_strings_var.set(state_data.get("exclusions", {}).get("exclude_strings", ""))
            self.exclude_extensions_var.set(state_data.get("exclusions", {}).get("exclude_extensions", ""))

            # Load UI settings
            loaded_filter = state_data.get("ui", {}).get("last_filetype_filter", "*")

            # Load Analysis Data and Rebuild UI List
            analysis_data = state_data.get("analysis", {})
            loaded_analyzed_files = analysis_data.get("analyzed_files", [])
            loaded_selected_files = set(analysis_data.get("selected_files", [])) # Use set for faster lookup

            self.analyzed_files_cache = loaded_analyzed_files # Store the loaded analyzed list
            self.file_list_data = [] # Clear current runtime list data
            file_types = set(["*"])

            if not loaded_analyzed_files:
                 messagebox.showwarning("Load State", "Loaded state has no analyzed file list. The file list will be empty.")
                 self.clear_file_list_ui()
                 self.update_filetype_dropdown([])
                 self.file_type_dropdown_var.set(loaded_filter) # Still set the filter
                 return

            for relative_path in loaded_analyzed_files:
                var = tk.IntVar()
                if relative_path in loaded_selected_files:
                    var.set(1)
                self.file_list_data.append({'path': relative_path, 'var': var})

                # Extract file types for dropdown
                _fname, fext = os.path.splitext(relative_path)
                norm_ext = fext.lstrip('.').lower()
                actual_file_type = norm_ext if norm_ext else "no_extension"
                file_types.add(actual_file_type)

            # Repopulate the UI
            self._populate_file_list_ui(self.file_list_data)

            # Update and set dropdown
            sorted_types = sorted(list(file_types))
            if "*" in sorted_types:
                sorted_types.remove("*")
                sorted_types.insert(0, "*")
            self.update_filetype_dropdown(sorted_types)

            if loaded_filter in sorted_types:
                self.file_type_dropdown_var.set(loaded_filter)
            elif sorted_types:
                self.file_type_dropdown_var.set(sorted_types[0])
            else:
                self.file_type_dropdown_var.set("*")

            messagebox.showinfo("Load State", "State successfully loaded.")

        except Exception as e:
             # Catch potential errors during state application (e.g., unexpected data format)
             messagebox.showerror("Load State Error", f"An error occurred while applying the loaded state: {e}")
             # Optionally, try to reset to a safe default state here
             self.folder_path.set("")
             self.output_path.set("")
             self.clear_file_list_ui()
             self.file_list_data = []
             self.analyzed_files_cache = []


if __name__ == '__main__':
    root = tk.Tk()
    app = CodeExporterUI(root)
    root.mainloop()
