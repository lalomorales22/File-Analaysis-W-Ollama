import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import json
import os
import random
import base64
import mimetypes
import datetime
from pathlib import Path
import threading
import queue
import requests  # For AI integration
import pygments
from pygments.lexers import get_lexer_for_filename, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name
from tkhtmlview import HTMLLabel  # For displaying syntax-highlighted code
import re
import configparser
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CosmicFileAnalyzer:
    def __init__(self, include_full_content=False):
        self.include_full_content = include_full_content
        self.text_extensions = {
            '.txt', '.md', '.py', '.js', '.html', '.css', '.json',
            '.xml', '.csv', '.java', '.cpp', '.c', '.cs', '.rb', '.go',
            '.php', '.rs', '.swift', '.kt', '.ts'
        }
        
    def get_content(self, file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            language = self.detect_language(file_path)
            if ext in self.text_extensions or 'text' in mime_type:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    if not self.include_full_content:
                        content_preview = content[:1000]
                        truncated = len(content) > 1000
                    else:
                        content_preview = content
                        truncated = False
                    return {
                        'content': content,
                        'preview': content_preview,
                        'truncated': truncated,
                        'language': language
                    }
            else:
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                    if not self.include_full_content:
                        binary_preview = base64.b64encode(binary_content[:100]).decode('utf-8')
                        truncated = len(binary_content) > 100
                    else:
                        binary_preview = base64.b64encode(binary_content).decode('utf-8')
                        truncated = False
                    return {
                        'content': base64.b64encode(binary_content).decode('utf-8'),
                        'preview': binary_preview,
                        'truncated': truncated,
                        'language': None
                    }
        except Exception as e:
            return {
                'content': None,
                'preview': f"Error reading file: {str(e)}",
                'truncated': False,
                'language': None
            }

    def detect_language(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(1000)
            lexer = get_lexer_for_filename(file_path, content)
            return lexer.name
        except:
            return 'Plain Text'

    def analyze_path(self, path, progress_callback=None):
        path_obj = Path(path)
        info = {
            'name': path_obj.name,
            'path': str(path_obj.absolute()),
            'type': 'directory' if path_obj.is_dir() else 'file',
            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
            'created': datetime.datetime.fromtimestamp(os.path.getctime(path)).isoformat(),
        }
        
        if path_obj.is_file():
            size = os.path.getsize(path)
            content_info = self.get_content(path)
            info.update({
                'size': size,
                'size_human': self.humanize_size(size),
                'mime_type': mimetypes.guess_type(path)[0] or 'application/octet-stream',
                'language': content_info.get('language'),
                **content_info
            })
            if progress_callback:
                progress_callback(f"Analyzed file: {path_obj.name}")
        else:
            try:
                contents = []
                total_size = 0
                
                for item in os.scandir(path):
                    item_info = self.analyze_path(item.path, progress_callback)
                    contents.append(item_info)
                    total_size += item_info.get('size', 0)
                
                info.update({
                    'contents': contents,
                    'size': total_size,
                    'size_human': self.humanize_size(total_size),
                    'items_count': len(contents)
                })
                if progress_callback:
                    progress_callback(f"Analyzed directory: {path_obj.name}")
            except PermissionError:
                info['error'] = "Permission denied"
            except Exception as e:
                info['error'] = str(e)
        
        return info

    @staticmethod
    def humanize_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

class GalacticExplorerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Galactic File Structure Analyzer")
        self.root.geometry("1400x900")  # Increase the width and height
        self.root.resizable(True, True)  # Allow window resizing
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize the analyzer
        self.analyzer = None  # Will initialize when analysis starts
        
        # Create a queue for thread communication
        self.queue = queue.Queue()
        
        # Setup the theme
        self.setup_theme()
        
        # Create a stop event for AI tasks
        self.stop_event = threading.Event()
        
        # Create the main container
        self.create_gui_elements()
        
        # Start queue processing
        self.process_queue()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'API' not in config:
            config['API'] = {'ollama_url': 'http://localhost:11434/api/generate'}  # Corrected endpoint
        if 'GUI' not in config:
            config['GUI'] = {'theme': 'clam', 'font_size': '10'}
        return config

    def setup_theme(self):
        # Use a modern theme
        style = ttk.Style()
        available_themes = style.theme_names()
        config_theme = self.config.get('GUI', 'theme')
        
        if config_theme in available_themes:
            style.theme_use(config_theme)
        else:
            # Fallback to a default theme
            fallback_theme = 'clam' if 'clam' in available_themes else available_themes[0]
            style.theme_use(fallback_theme)
            self.config.set('GUI', 'theme', fallback_theme)
            logger.warning(f"Theme '{config_theme}' not found. Using '{fallback_theme}' instead.")
        
        style.configure('Treeview', rowheight=25)

    def create_gui_elements(self):
        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)
        
        # Toolbar frame
        toolbar_frame = ttk.Frame(self.main_frame)
        toolbar_frame.pack(fill='x')
        
        # Path selection
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(toolbar_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side='left', padx=5, pady=5)
        
        browse_btn = ttk.Button(
            toolbar_frame,
            text="Browse",
            command=self.browse_folder
        )
        browse_btn.pack(side='left', padx=5, pady=5)
        
        # Include content checkbox
        self.include_content_var = tk.BooleanVar(value=False)
        content_check = ttk.Checkbutton(
            toolbar_frame,
            text="Include Full File Contents",
            variable=self.include_content_var
        )
        content_check.pack(side='left', padx=5, pady=5)
        
        # Output format options
        format_label = ttk.Label(toolbar_frame, text="Output Format:")
        format_label.pack(side='left', padx=5, pady=5)
        
        self.output_format_var = tk.StringVar(value='json')
        format_json_radio = ttk.Radiobutton(
            toolbar_frame,
            text='JSON',
            variable=self.output_format_var,
            value='json'
        )
        format_json_radio.pack(side='left', padx=5, pady=5)
        
        format_jsonl_radio = ttk.Radiobutton(
            toolbar_frame,
            text='JSONL',
            variable=self.output_format_var,
            value='jsonl'
        )
        format_jsonl_radio.pack(side='left', padx=5, pady=5)
        
        # Analyze button
        self.analyze_btn = ttk.Button(
            toolbar_frame,
            text="Begin Analysis",
            command=self.start_analysis
        )
        self.analyze_btn.pack(side='left', padx=5, pady=5)
        
        # Save button
        self.save_btn = ttk.Button(
            toolbar_frame,
            text="Save Analysis",
            command=self.save_output,
            state='disabled'  # Initially disabled until analysis is complete
        )
        self.save_btn.pack(side='left', padx=5, pady=5)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready to scan...")
        self.progress_label = ttk.Label(
            toolbar_frame,
            textvariable=self.progress_var
        )
        self.progress_label.pack(side='left', padx=5, pady=5)
        
        self.progress_bar = ttk.Progressbar(
            toolbar_frame,
            mode='indeterminate'
        )
        
        # Main PanedWindow
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill='both', expand=True)
        
        # Treeview for file structure
        self.tree_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.tree_frame, weight=1)
        
        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.pack(fill='both', expand=True)
        
        self.tree.heading('#0', text='File Structure', anchor='w')
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(self.tree_frame, orient='vertical', command=self.tree.yview)
        tree_scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Details and AI Analysis Notebook
        self.notebook = ttk.Notebook(self.paned_window)
        self.paned_window.add(self.notebook, weight=1)
        
        # File Details Tab
        self.details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text='File Details')
        
        details_label = ttk.Label(self.details_frame, text="File Details")
        details_label.pack(anchor='nw')
        
        self.details_text = scrolledtext.ScrolledText(
            self.details_frame,
            width=40,
            wrap='word'
        )
        self.details_text.pack(fill='both', expand=True)
        
        # AI Analysis Tab
        self.ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_frame, text='AI Analysis')
        
        # AI Model Selector
        ai_model_label = ttk.Label(self.ai_frame, text="Select AI Model:")
        ai_model_label.pack(anchor='nw', padx=5, pady=5)
        
        self.ai_model_var = tk.StringVar(value='Choose Your Model Below')
        self.ai_model_menu = ttk.Combobox(
            self.ai_frame,
            textvariable=self.ai_model_var,
            state='readonly'
        )
        self.ai_model_menu.pack(anchor='nw', padx=5, pady=5)
        
        self.load_models()  # Load models dynamically
        
        ai_task_frame = ttk.Frame(self.ai_frame)
        ai_task_frame.pack(anchor='nw', padx=5, pady=5)
        
        # Add Stop AI button
        stop_ai_btn = ttk.Button(
            ai_task_frame,
            text="Stop AI",
            command=self.stop_ai_task
        )
        stop_ai_btn.pack(side='left', padx=5, pady=5)
        
        tasks = [
            ("Analyze Code Quality", self.analyze_code_quality),
            ("Suggest Improvements", self.suggest_improvements),
            ("Find Security Issues", self.find_security_issues),
            ("Generate Documentation", self.generate_documentation),
            ("Explain This File", self.explain_file)
        ]
        
        for task_name, task_command in tasks:
            btn = ttk.Button(ai_task_frame, text=task_name, command=task_command)
            btn.pack(side='left', padx=5, pady=5)
        
        # AI Output Text
        self.ai_output_text = scrolledtext.ScrolledText(
            self.ai_frame,
            width=40,
            wrap='word'
        )
        self.ai_output_text.pack(fill='both', expand=True)
        
        # Bind tree selection
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="Select a Folder")
        if folder_path:
            self.path_var.set(folder_path)
    
    def start_analysis(self):
        path = self.path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid folder.")
            return
        
        self.analyze_btn.config(state='disabled')
        self.progress_bar.pack(side='left', padx=5, pady=5)
        self.progress_bar.start(10)
        self.progress_var.set("Scanning...")
        
        # Initialize the analyzer with the user preference
        self.analyzer = CosmicFileAnalyzer(include_full_content=self.include_content_var.get())
        
        # Start analysis in a separate thread
        threading.Thread(target=self.analyze_folder, args=(path,), daemon=True).start()
    
    def analyze_folder(self, path):
        try:
            result = self.analyzer.analyze_path(path, self.update_progress)
            
            # Put results in queue
            self.queue.put(("success", result))
        except Exception as e:
            self.queue.put(("error", str(e)))
    
    def update_progress(self, message):
        self.queue.put(("progress", message))
    
    def process_queue(self):
        try:
            while True:
                msg_type, msg = self.queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(msg)
                
                elif msg_type == "success":
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
                    self.analyze_btn.config(state='normal')
                    self.progress_var.set("Analysis complete!")
                    
                    # Display results in treeview
                    self.populate_treeview(msg)
                    
                    # Enable the save button
                    self.save_btn.config(state='normal')
                    
                elif msg_type == "error":
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
                    self.analyze_btn.config(state='normal')
                    self.progress_var.set("Error occurred!")
                    messagebox.showerror("Error", f"Error: {msg}")
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
    
    def populate_treeview(self, data, parent=''):
        # Clear existing tree
        self.tree.delete(*self.tree.get_children())
        
        self.item_paths = {}  # To keep track of item paths

        def add_items(parent_id, item_data):
            node_id = self.tree.insert(parent_id, 'end', text=item_data['name'], open=False)
            self.item_paths[node_id] = item_data['path']
            if item_data['type'] == 'directory':
                for child in item_data.get('contents', []):
                    add_items(node_id, child)
        
        add_items(parent, data)
        self.analysis_result = data  # Store the analysis result for later use
    
    def on_tree_select(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            item_path = self.item_paths.get(selected_item[0])
            if item_path:
                item_data = self.find_item_data(self.analysis_result, item_path)
                if item_data:
                    self.display_item_details(item_data)
    
    def find_item_data(self, data, target_path):
        # Traverse data to find item matching the target path
        if data['path'] == target_path:
            return data
        if data['type'] == 'directory':
            for child in data.get('contents', []):
                found = self.find_item_data(child, target_path)
                if found:
                    return found
        return None
    
    def display_item_details(self, item_data):
        self.details_text.delete('1.0', tk.END)
        details = f"Name: {item_data['name']}\n"
        details += f"Path: {item_data['path']}\n"
        details += f"Type: {item_data['type']}\n"
        details += f"Size: {item_data.get('size_human', '')}\n"
        details += f"Modified: {item_data['modified']}\n"
        details += f"Created: {item_data['created']}\n"
        if item_data['type'] == 'file':
            details += f"MIME Type: {item_data.get('mime_type', '')}\n"
            details += f"Language: {item_data.get('language', '')}\n"
            if self.include_content_var.get():
                content = item_data.get('content', '')
                highlighted_content = self.syntax_highlight(content, item_data.get('language'))
                self.details_text.insert(tk.END, details)
                self.details_text.insert(tk.END, "\nContent:\n")
                self.details_text.insert(tk.END, highlighted_content)
            else:
                preview = item_data.get('preview', '')
                highlighted_preview = self.syntax_highlight(preview, item_data.get('language'))
                self.details_text.insert(tk.END, details)
                self.details_text.insert(tk.END, "\nPreview:\n")
                self.details_text.insert(tk.END, highlighted_preview)
        else:
            self.details_text.insert(tk.END, details)
    
    def syntax_highlight(self, code, language):
        try:
            if language:
                lexer = get_lexer_for_filename(f".{language.lower()}")
            else:
                lexer = guess_lexer(code)
            formatter = HtmlFormatter(style='default')
            highlighted_code = pygments.highlight(code, lexer, formatter)
            return highlighted_code
        except:
            return code
    
    def save_output(self):
        if not hasattr(self, 'analysis_result'):
            messagebox.showerror("Error", "No analysis result to save.")
            return
        
        filetypes = [('JSON files', '*.json'), ('JSONL files', '*.jsonl')]
        output_path = filedialog.asksaveasfilename(
            title="Save Analysis Output",
            defaultextension='.json',
            filetypes=filetypes
        )
        if output_path:
            try:
                output_format = self.output_format_var.get()
                if output_format == 'json':
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(self.analysis_result, f, indent=2, ensure_ascii=False)
                elif output_format == 'jsonl':
                    # Flatten the data and write each item as a JSON object per line
                    with open(output_path, 'w', encoding='utf-8') as f:
                        for item in self.flatten_data(self.analysis_result):
                            json.dump(item, f, ensure_ascii=False)
                            f.write('\n')
                messagebox.showinfo("Success", f"Analysis saved to {output_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def flatten_data(self, data):
        # Flatten the nested directory structure for JSONL output
        items = []
        def flatten(item):
            item_copy = item.copy()
            contents = item_copy.pop('contents', [])
            items.append(item_copy)
            for child in contents:
                flatten(child)
        flatten(data)
        return items
    
    # AI Task Implementations
    def get_selected_file_content(self):
        selected_item = self.tree.selection()
        if selected_item:
            item_path = self.item_paths.get(selected_item[0])
            if item_path:
                item_data = self.find_item_data(self.analysis_result, item_path)
                if item_data and item_data['type'] == 'file':
                    return item_data.get('content', ''), item_data.get('language', 'Plain Text')
        messagebox.showwarning("Warning", "Please select a file to analyze.")
        return None, None
    
    def call_ai_model(self, prompt):
        model = self.ai_model_var.get()
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            'model': model,
            'prompt': prompt,
            'stream': True,  # Enable streaming
            'max_tokens': 2048  # Adjust token size if supported by the API
        }
        try:
            response = requests.post(self.config.get('API', 'ollama_url'), headers=headers, json=data, stream=True)
            response.raise_for_status()  # Raise an error for bad responses

            full_response = ""
            for line in response.iter_lines():
                if self.stop_event.is_set():
                    break  # Stop processing if the stop event is set
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get('response', '')
                        full_response += chunk
                        self.ai_output_text.insert(tk.END, chunk)
                        self.ai_output_text.see(tk.END)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {str(e)}")
                        self.ai_output_text.insert(tk.END, f"\nError decoding response: {str(e)}")
                        break

            return full_response
        except requests.RequestException as e:
            logger.error(f"Error in API request: {str(e)}", exc_info=True)
            return f"Error communicating with AI model: {str(e)}"
    
    def analyze_code_quality(self):
        content, language = self.get_selected_file_content()
        if content:
            prompt = f"Analyze the code quality of the following {language} code:\n\n{content}"
            self.ai_output_text.delete('1.0', tk.END)
            self.ai_output_text.insert(tk.END, "Analyzing code quality...\n")
            threading.Thread(target=self.run_ai_task, args=(prompt,), daemon=True).start()
    
    def suggest_improvements(self):
        content, language = self.get_selected_file_content()
        if content:
            prompt = f"Suggest improvements for the following {language} code:\n\n{content}"
            self.ai_output_text.delete('1.0', tk.END)
            self.ai_output_text.insert(tk.END, "Suggesting improvements...\n")
            threading.Thread(target=self.run_ai_task, args=(prompt,), daemon=True).start()
    
    def find_security_issues(self):
        content, language = self.get_selected_file_content()
        if content:
            prompt = f"Find any security issues in the following {language} code:\n\n{content}"
            self.ai_output_text.delete('1.0', tk.END)
            self.ai_output_text.insert(tk.END, "Finding security issues...\n")
            threading.Thread(target=self.run_ai_task, args=(prompt,), daemon=True).start()
    
    def generate_documentation(self):
        content, language = self.get_selected_file_content()
        if content:
            prompt = f"Generate documentation for the following {language} code:\n\n{content}"
            self.ai_output_text.delete('1.0', tk.END)
            self.ai_output_text.insert(tk.END, "Generating documentation...\n")
            threading.Thread(target=self.run_ai_task, args=(prompt,), daemon=True).start()
    
    def explain_file(self):
        content, language = self.get_selected_file_content()
        if content:
            prompt = f"Explain what the following {language} code does:\n\n{content}"
            self.ai_output_text.delete('1.0', tk.END)
            self.ai_output_text.insert(tk.END, "Explaining the file...\n")
            threading.Thread(target=self.run_ai_task, args=(prompt,), daemon=True).start()
    
    def run_ai_task(self, prompt):
        self.stop_event.clear()  # Clear the stop event before starting
        result = self.call_ai_model(prompt)
        if not self.stop_event.is_set():
            self.ai_output_text.insert(tk.END, f"\n{result}")

    def load_models(self):
        try:
            response = requests.get('http://localhost:11434/api/tags')
            response.raise_for_status()
            models_data = response.json()
            models = models_data.get('models', [])
            # Extract model names and filter out unwanted ones
            filtered_models = [model['name'] for model in models if not model['name'].startswith('hf.co')]
            
            if filtered_models:
                self.ai_model_menu['values'] = filtered_models
                # Set default value to first model
                self.ai_model_var.set(filtered_models[0])
            else:
                self.ai_model_menu['values'] = ['No models available']
                self.ai_model_var.set('No models available')
                
        except requests.RequestException as e:
            logger.error(f"Error fetching models: {str(e)}")
            self.ai_model_menu['values'] = ['Error loading models']
            self.ai_model_var.set('Error loading models')
            messagebox.showerror("Error", "Failed to load models from server.")

    def stop_ai_task(self):
        self.stop_event.set()  # Set the stop event to signal the thread to stop
        self.ai_output_text.insert(tk.END, "\nAI task stopped by user.\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = GalacticExplorerGUI(root)
    root.mainloop()
