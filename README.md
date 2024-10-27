File Structure Analyzer

File Structure Analyzer is a GUI application built with Python's Tkinter library. It allows users to analyze file structures, view file details, and perform AI-based analysis on code files using models from an AI server.

## Features

- Analyze file and directory structures.
- View detailed information about files, including size, type, and content preview.
- Perform AI-based tasks such as code quality analysis, improvement suggestions, security issue detection, documentation generation, and file explanation.
- Save analysis results in JSON or JSONL format.
- Modern GUI with resizable window and theme support.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/lalomorales22/File-Analaysis-W-Ollama.git
   cd File-Analaysis-W-Ollama
   ```

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Ensure you have a running AI server that supports the required API endpoints.

## Usage

1. Run the application:

   ```bash
   python app.py
   ```

2. Use the GUI to select a folder for analysis.

3. Choose whether to include full file contents in the analysis.

4. Select the desired output format (JSON or JSONL).

5. Click "Begin Analysis" to start analyzing the selected folder.

6. Use the AI Analysis tab to perform various AI-based tasks on selected files.

## Configuration

- The application reads configuration from `config.ini`. Ensure the API endpoint and GUI settings are correctly configured.

## Requirements

- Python 3.6 or higher
- A running AI server with the required API endpoints

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.