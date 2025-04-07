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
        # --- Variables ---
        # Load general settings first, potentially including last paths and selections
        self.last_session_folder = ""
        self.last_session_selected_files = set()
        self.load_settings() # This now loads last folder/selections into instance vars

        # UI Variables linked to widgets
        self.folder_path = tk.StringVar(value=self.last_session_folder) # Start with last used folder
        self.output_path = tk.StringVar(value=self.config.get('Paths', 'output_path', fallback=''))
        self.exclude_strings_var = tk.StringVar(value=self.config.get('Exclusions', 'exclude_strings', fallback=''))
        self.exclude_extensions_var = tk.StringVar(value=self.config.get('Exclusions', 'exclude_extensions', fallback=''))
        self.file_type_dropdown_var = tk.StringVar(master, value=self.config.get('UI', 'last_filetype_filter', fallback='*'))

        # Data stores
        self.file_list_data = [] # Stores {'path': relative_path, 'var': tk.IntVar()} - Current runtime state
        self.analyzed_files_cache = [] # Stores just the relative paths from the last analysis for Save State
        self.is_analyzing = False # Flag to prevent race conditions or duplicate analysis


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
        self.file_list_canvas.bind("<Configure>", self._on_canvas_configure) # Use helper
        self.file_list_canvas_window = self.file_list_canvas.create_window((0, 0), window=self.file_list_scrollable_frame, anchor="nw")

        # Row 4: Quick Select and Clear All
        tk.Label(master, text="Quick Select Filetype:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.filetype_dropdown = tk.OptionMenu(master, self.file_type_dropdown_var, "*") # Populated later
        self.filetype_dropdown.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        tk.Button(master, text="Quick Select", command=self.quick_select).grid(row=4, column=2, padx=5, pady=2)
        tk.Button(master, text="Clear All", command=self.clear_all).grid(row=4, column=3, padx=5, pady=2)

        # Row 5: Output Path and Export
        tk.Label(master, text="Output File:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(master, textvariable=self.output_path, width=50, state='readonly').grid(row=5, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        tk.Button(master, text="Browse Output", command=self.browse_output_path).grid(row=5, column=3, padx=5, pady=2)
        tk.Button(master, text="Export", command=self.export_files).grid(row=5, column=4, padx=5, pady=2)

        # Row 6: Save/Load State
        tk.Button(master, text="Save State", command=self.save_state).grid(row=6, column=1, padx=5, pady=5, sticky="e")
        tk.Button(master, text="Load State", command=self.load_state).grid(row=6, column=2, padx=5, pady=5, sticky="w")

        # Configure grid layout
        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(3, weight=1)
        self.file_list_frame.grid_columnconfigure(0, weight=1) # Canvas expands within frame

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Initial setup ---
        # If a folder was loaded from settings, run initial analysis
        if self.folder_path.get() and os.path.isdir(self.folder_path.get()):
             # Schedule the analysis slightly after the main loop starts
             self.master.after(100, self.analyze_folder)
        else:
             # Ensure dropdown is initialized even if no analysis runs
             self.update_filetype_dropdown([])


    def _on_canvas_configure(self, event=None):
        """Callback for canvas configure event to update scroll region."""
        # Update scrollregion to encompass the scrollable frame
        self.file_list_canvas.configure(scrollregion=self.file_list_canvas.bbox("all"))
        # Adjust the width of the frame inside the canvas to match the canvas width
        # This prevents horizontal scrolling and makes items fill the width
        canvas_width = event.width if event else self.file_list_canvas.winfo_width()
        self.file_list_canvas.itemconfig(self.file_list_canvas_window, width=canvas_width)


    def load_settings(self):
        """Loads general app settings from INI, including last folder and selections."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Ensure default sections exist
            if 'Paths' not in self.config: self.config['Paths'] = {}
            if 'UI' not in self.config: self.config['UI'] = {'last_filetype_filter': '*'}
            if 'Exclusions' not in self.config: self.config['Exclusions'] = {}
            if 'FileSelection' not in self.config: self.config['FileSelection'] = {} # Add section back

        # Load last used paths and settings into instance variables for potential use
        self.last_session_folder = self.config.get('Paths', 'last_analyzed_folder', fallback='')
        # Don't set self.folder_path here, do it in __init__ after loading

        selected_files_str = self.config.get('FileSelection', 'selected_files', fallback='')
        self.last_session_selected_files = set(f.strip() for f in selected_files_str.split(',') if f.strip())


    def save_settings(self):
        """Saves the *current* state (paths, selections for current folder) to INI on closing."""
        if 'Paths' not in self.config: self.config['Paths'] = {}
        if 'UI' not in self.config: self.config['UI'] = {}
        if 'Exclusions' not in self.config: self.config['Exclusions'] = {}
        if 'FileSelection' not in self.config: self.config['FileSelection'] = {}

        current_folder = self.folder_path.get()
        self.config['Paths']['folder_path'] = current_folder # Save last folder viewed
        self.config['Paths']['last_analyzed_folder'] = current_folder # Explicitly save for reload logic
        self.config['Paths']['output_path'] = self.output_path.get()

        self.config['UI']['last_filetype_filter'] = self.file_type_dropdown_var.get()

        self.config['Exclusions']['exclude_strings'] = self.exclude_strings_var.get()
        self.config['Exclusions']['exclude_extensions'] = self.exclude_extensions_var.get()

        # Save current selections *for the current folder*
        selected_files = [file_info['path'] for file_info in self.file_list_data if file_info['var'].get() == 1]
        self.config['FileSelection']['selected_files'] = ",".join(selected_files)


        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def on_closing(self):
        self.save_settings() # Save current state to INI
        self.master.destroy()

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.folder_path.get() or ".")
        if folder_selected and folder_selected != self.folder_path.get():
            self.folder_path.set(folder_selected)
            # Clear previous analysis results *and runtime data* when folder changes
            self.clear_file_list_ui()
            self.file_list_data = []
            self.analyzed_files_cache = []
            # self.last_session_selected_files = set() # Don't clear this, INI holds memory per folder
            self.update_filetype_dropdown([])
            # Trigger analysis for the new folder
            self.analyze_folder() # Analyze automatically after browsing

    def load_blacklist(self):
        blacklist_file = "blacklisted_paths.txt"
        blacklist = []
        if os.path.exists(blacklist_file):
            try:
                with open(blacklist_file, 'r', encoding='utf-8') as f: # Added encoding
                    for line in f:
                        cleaned_line = line.strip()
                        if cleaned_line and not cleaned_line.startswith('#'):
                            blacklist.append(cleaned_line.replace('\\', '/')) # Normalize blacklist paths
            except Exception as e:
                messagebox.showwarning("Blacklist Warning", f"Could not read blacklist file {blacklist_file}:\n{e}")
        return blacklist

    def analyze_folder(self):
        if self.is_analyzing: # Prevent re-entry
             print("Analysis already in progress.")
             return
        self.is_analyzing = True

        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder): # Check validity
            messagebox.showerror("Error", "Please select a valid codebase folder.")
            self.is_analyzing = False
            return

        # --- Preserve Selections Logic ---
        # Determine which selections to try and preserve
        selections_to_preserve = set()
        # If the folder being analyzed is the same as the one loaded initially from settings, use those selections
        if folder == self.last_session_folder:
             selections_to_preserve = self.last_session_selected_files
             # Clear the session memory once used for initial load to prioritize runtime selections
             self.last_session_folder = None
             self.last_session_selected_files = set()
        else:
             # Otherwise (re-analyzing the same folder without closing), preserve current runtime selections
             selections_to_preserve = {info['path'] for info in self.file_list_data if info['var'].get() == 1}
        # --- End Preserve Selections Logic ---


        # Get exclusion criteria
        exclude_strings_raw = self.exclude_strings_var.get()
        exclude_extensions_raw = self.exclude_extensions_var.get()
        exclude_strings = [s.strip() for s in exclude_strings_raw.split(',') if s.strip()]
        exclude_extensions = [e.strip().lstrip('.').lower() for e in exclude_extensions_raw.split(',') if e.strip()]

        # Prepare for new analysis
        self.clear_file_list_ui() # Clear UI first
        new_file_list_data = [] # Build new list
        self.analyzed_files_cache = [] # Reset cache
        file_types = set(["*"])
        blacklist = self.load_blacklist()


        try:
            for root, dirs, files in os.walk(folder, topdown=True):
                 # Normalize root path for comparison
                 rel_root = os.path.relpath(root, folder).replace('\\', '/')
                 if rel_root == '.': rel_root = '' # Handle base folder case

                 # --- Directory Exclusion ---
                 dirs[:] = [d for d in dirs if not any(
                     os.path.join(rel_root, d).replace('\\','/') == bp.rstrip('/') or # Exact match
                     os.path.join(rel_root, d).replace('\\','/').startswith(bp.rstrip('/') + '/') # Subdir match
                     for bp in blacklist
                     )]
                 dirs[:] = [d for d in dirs if not any(exclude_str in os.path.join(rel_root, d).replace('\\','/') for exclude_str in exclude_strings)]


                 for file in files:
                    try:
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, folder)
                        relative_path = relative_path.replace('\\', '/') # Normalize
                    except Exception as e:
                         print(f"Skipping file due to path error: {e}")
                         continue

                    # --- File Exclusion Checks ---
                    is_blacklisted = any(relative_path == bp or relative_path.startswith(bp.rstrip('/') + '/') for bp in blacklist if bp) # Check against normalized blacklist paths
                    if is_blacklisted: continue

                    is_excluded_by_string = any(exclude_str in relative_path for exclude_str in exclude_strings)
                    if is_excluded_by_string: continue

                    _file_name, file_extension = os.path.splitext(file)
                    normalized_extension = file_extension.lstrip('.').lower()
                    if normalized_extension in exclude_extensions: continue

                    # --- If not excluded, add to list ---
                    var = tk.IntVar()
                    # Apply preserved selection state
                    if relative_path in selections_to_preserve:
                        var.set(1)

                    new_file_list_data.append({'path': relative_path, 'var': var})
                    self.analyzed_files_cache.append(relative_path)

                    actual_file_type = normalized_extension if normalized_extension else "no_extension"
                    file_types.add(actual_file_type)

        except OSError as e:
             messagebox.showerror("Folder Error", f"Error walking the directory: {e}\nCheck permissions or folder path.")
             self.is_analyzing = False
             return

        # --- Update UI after walk ---
        self.file_list_data = new_file_list_data # Replace old data with new
        self._populate_file_list_ui(self.file_list_data)

        sorted_types = sorted(list(file_types))
        if "*" in sorted_types:
             sorted_types.remove("*")
             sorted_types.insert(0, "*")
        self.update_filetype_dropdown(sorted_types)

        # Restore last used filter from general config (not from saved state)
        last_filter = self.config.get('UI', 'last_filetype_filter', fallback='*')
        if last_filter in sorted_types:
             self.file_type_dropdown_var.set(last_filter)
        elif sorted_types:
             self.file_type_dropdown_var.set(sorted_types[0])
        else:
             self.file_type_dropdown_var.set('*')

        self.is_analyzing = False # Analysis finished


    def _populate_file_list_ui(self, file_data_list):
        """Helper to populate the scrollable frame from file_data_list."""
        self.clear_file_list_ui() # Ensure it's clean before adding
        for file_info in file_data_list:
            frame = tk.Frame(self.file_list_scrollable_frame)
            frame.pack(fill='x', padx=2, pady=1)
            # Make checkbutton text selectable (useful for copying paths)
            cb = tk.Checkbutton(frame, variable=file_info['var'], anchor="w")
            cb.pack(side='left')
            # Use an Entry for the text part to make it selectable/copyable
            path_entry = tk.Entry(frame, relief="flat", bg=frame.cget('bg'), fg='black', readonlybackground=frame.cget('bg'))
            path_entry.insert(0, file_info['path'])
            path_entry.config(state="readonly") # Make it non-editable but selectable
            path_entry.pack(side='left', fill='x', expand=True)


        # Schedule scroll region update and canvas resize
        self.master.after(50, self._on_canvas_configure)


    def clear_file_list_ui(self):
        for widget in self.file_list_scrollable_frame.winfo_children():
            widget.destroy()
        self.file_list_canvas.yview_moveto(0) # Scroll back to top
        # No need to reset scrollregion here, _populate_file_list_ui will handle it


    def update_filetype_dropdown(self, filetypes):
        # Get the actual menu widget
        menu = self.filetype_dropdown.nametowidget(self.filetype_dropdown.cget('menu'))
        menu.delete(0, "end")

        if not filetypes:
             filetypes = ["*"]
        elif "*" not in filetypes:
             filetypes.insert(0,"*")

        current_selection = self.file_type_dropdown_var.get()

        for filetype in filetypes:
            menu.add_command(label=filetype, command=tk._setit(self.file_type_dropdown_var, filetype))

        # If current selection is no longer valid, default to '*' or the first type
        if current_selection not in filetypes:
            if "*" in filetypes:
                self.file_type_dropdown_var.set("*")
            elif filetypes:
                self.file_type_dropdown_var.set(filetypes[0])
            else: # Should not happen if "*" is always added
                 self.file_type_dropdown_var.set("*")
        else:
             # Ensure the variable is explicitly set even if it didn't change,
             # sometimes needed to refresh the display
             self.file_type_dropdown_var.set(current_selection)


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
                # IMPORTANT: Quick Select should *only* select, not deselect others
                if should_select:
                     file_info['var'].set(1)
                # else: keep existing selection state


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
        # Iterate through the current runtime list data
        for file_info in self.file_list_data:
            if file_info['var'].get() == 1:
                selected_count += 1
                full_file_path = os.path.join(folder, file_info['path'])
                try:
                    if not os.path.exists(full_file_path):
                         raise FileNotFoundError(f"File not found (might have been moved/deleted): {file_info['path']}")

                    with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                    normalized_rel_path = file_info['path'].replace('\\', '/')
                    selected_files_content += f"-- BEGIN FILE: {normalized_rel_path} --\n"
                    selected_files_content += file_content + "\n"
                    selected_files_content += f"-- END FILE: {normalized_rel_path} --\n\n"
                    exported_count += 1
                except Exception as e:
                    error_msg = f"Could not read file: {file_info['path']}. Error: {e}"
                    export_errors.append(error_msg)

        # (Error reporting and writing logic remains the same as before)
        if export_errors:
             error_summary = "\n".join(export_errors[:5]) + ("\n..." if len(export_errors) > 5 else "")
             messagebox.showwarning("Export Warning", f"{len(export_errors)} file(s) could not be read:\n\n{error_summary}")
             if exported_count == 0:
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

        try:
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                outfile.write(selected_files_content)

            success_message = f"Successfully exported {exported_count} file(s) to:\n{output_file_path}"
            if export_errors:
                 success_message += f"\n({len(export_errors)} selected file(s) failed to read)."
            messagebox.showinfo("Success", success_message)

        except Exception as e:
            messagebox.showerror("Error Writing File", f"Could not write to output file: {output_file_path}. Error: {e}")


    # --- Save/Load State Methods ---

    def save_state(self):
        """Saves the current UI state (paths, exclusions, selections) to a JSON file."""
        current_folder = self.folder_path.get()
        if not current_folder or not self.analyzed_files_cache: # Check cache which persists even if list is empty
            messagebox.showwarning("Save State", "Please select and successfully analyze a folder before saving state.")
            return

        folder_name = os.path.basename(current_folder.rstrip('/\\')) or "project"
        initial_filename = f"{folder_name}.llmexport"
        # Suggest saving inside the project folder or its parent
        initial_dir = current_folder if os.path.isdir(current_folder) else os.path.dirname(current_folder)

        state_filepath = filedialog.asksaveasfilename(
            title="Save Exporter State",
            initialdir=initial_dir,
            initialfile=initial_filename,
            defaultextension=".llmexport",
            filetypes=[("LLM Exporter State", "*.llmexport"), ("All Files", "*.*")]
        )

        if not state_filepath: return

        # Gather state data from current runtime
        selected_files = [info['path'] for info in self.file_list_data if info['var'].get() == 1]

        state_data = {
            "version": 1,
            "paths": {
                "folder_path": current_folder,
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
                # Save the list of files found during the *last successful analysis* for this folder
                "analyzed_files": self.analyzed_files_cache,
                # Save the list of *currently* selected files
                "selected_files": selected_files
            }
        }

        try:
            with open(state_filepath, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=4)
            messagebox.showinfo("Save State", f"State successfully saved to:\n{state_filepath}")
        except Exception as e:
            messagebox.showerror("Save State Error", f"Failed to save state file: {e}")

    def load_state(self):
        """Loads UI state from a JSON file, overwriting current settings and selections."""
        state_filepath = filedialog.askopenfilename(
            title="Load Exporter State",
            defaultextension=".llmexport",
            filetypes=[("LLM Exporter State", "*.llmexport"), ("All Files", "*.*")]
        )

        if not state_filepath: return

        try:
            with open(state_filepath, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        except Exception as e:
             # Error reading or parsing the file itself
             messagebox.showerror("Load State Error", f"Failed to read or parse state file: {e}")
             return # Exit early if file can't even be read

        # --- Apply Loaded State ---
        try:
            # --- Start Applying State ---
            if state_data.get("version") != 1:
                 messagebox.showwarning("Load State", "State file is from an incompatible version.")

            # Load Paths
            loaded_folder = state_data.get("paths", {}).get("folder_path", "")
            # Check immediately if the crucial folder path is valid
            if not loaded_folder or not os.path.isdir(loaded_folder):
                 messagebox.showwarning("Load State Warning", f"The folder path specified in the state file is invalid or no longer exists:\n{loaded_folder}\n\nOther settings will be loaded, but you'll need to select a valid folder.")
                 # Don't return, allow loading other settings, but set path to the invalid one
                 # so user sees what was loaded. Alternatively, clear it: self.folder_path.set("")

            # Set paths regardless of folder validity for now
            self.folder_path.set(loaded_folder)
            self.output_path.set(state_data.get("paths", {}).get("output_path", ""))

            # Load Exclusions
            self.exclude_strings_var.set(state_data.get("exclusions", {}).get("exclude_strings", ""))
            self.exclude_extensions_var.set(state_data.get("exclusions", {}).get("exclude_extensions", ""))

            # Load UI settings
            loaded_filter = state_data.get("ui", {}).get("last_filetype_filter", "*")

            # Load Analysis Data and Rebuild UI List
            analysis_data = state_data.get("analysis", {})
            loaded_analyzed_files = analysis_data.get("analyzed_files", [])
            loaded_selected_files = set(analysis_data.get("selected_files", []))

            self.analyzed_files_cache = loaded_analyzed_files
            new_file_list_data = []
            file_types = set(["*"])

            if not loaded_analyzed_files:
                 print("Loaded state contains no analyzed file list.")

            for relative_path in loaded_analyzed_files:
                # Basic validation: ensure path is a string (might fail if JSON is malformed)
                if not isinstance(relative_path, str):
                    print(f"Warning: Skipping invalid path entry in loaded state: {relative_path}")
                    continue
                var = tk.IntVar(value=1 if relative_path in loaded_selected_files else 0)
                new_file_list_data.append({'path': relative_path, 'var': var})

                _fname, fext = os.path.splitext(relative_path)
                norm_ext = fext.lstrip('.').lower()
                file_types.add(norm_ext if norm_ext else "no_extension")

            # Update the main data list and UI
            self.file_list_data = new_file_list_data
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

            # Clear session memory after successful load
            self.last_session_folder = None
            self.last_session_selected_files = set()

            messagebox.showinfo("Load State", "State successfully loaded.")
            # --- End Applying State ---

        except Exception as e:
             # --- Error handling specifically for *applying* the state ---
             messagebox.showerror("Load State Error", f"An error occurred while applying the loaded state data: {e}\n\nAttempting to reset UI to default state.")

             # --- Reset UI to Default State ---
             self.folder_path.set("")
             self.output_path.set("")
             self.exclude_strings_var.set("")
             self.exclude_extensions_var.set("")

             self.clear_file_list_ui() # Clear visual list
             self.file_list_data = [] # Clear internal data list
             self.analyzed_files_cache = [] # Clear analyzed file cache

             # Reset dropdown
             self.update_filetype_dropdown([]) # Update options to just "*"
             self.file_type_dropdown_var.set("*") # Set value to "*"

             # Reset session memory too
             self.last_session_folder = None
             self.last_session_selected_files = set()

             print("UI reset due to error applying loaded state.")
             # --- End Reset ---


if __name__ == '__main__':
    root = tk.Tk()
    app = CodeExporterUI(root)
    root.mainloop()
