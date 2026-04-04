# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets, QtCore, QtGui
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsSettings
import os
import subprocess
import html
import re
import tempfile
import json
import webbrowser

# Import variable for PyQt version detection
from qgis.PyQt.QtCore import PYQT_VERSION_STR

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini Assistant Settings")
        self.resize(450, 300)
        self.settings = QgsSettings()
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # API Key Section
        api_group = QtWidgets.QGroupBox("Direct API Settings (Recommended)")
        api_layout = QtWidgets.QVBoxLayout(api_group)
        
        api_layout.addWidget(QtWidgets.QLabel("<b>Google API Key:</b>"))
        self.api_key_input = QtWidgets.QLineEdit()
        if hasattr(QtWidgets.QLineEdit, 'EchoMode') and hasattr(QtWidgets.QLineEdit.EchoMode, 'Password'):
            self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        elif hasattr(QtWidgets.QLineEdit, 'Password'):
            self.api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_key_input.setText(self.settings.value("gemini_assistant/api_key", ""))
        api_layout.addWidget(self.api_key_input)
        
        test_layout = QtWidgets.QHBoxLayout()
        link_lbl = QtWidgets.QLabel("<a href='https://aistudio.google.com/app/apikey'>Get API Key from Google AI Studio</a>")
        link_lbl.setOpenExternalLinks(True)
        test_layout.addWidget(link_lbl)
        
        self.test_btn = QtWidgets.QPushButton("Test Key")
        self.test_btn.setFixedWidth(100)
        self.test_btn.clicked.connect(self.test_api_key)
        test_layout.addWidget(self.test_btn)
        api_layout.addLayout(test_layout)
        
        layout.addWidget(api_group)
        
        # CLI Section
        cli_group = QtWidgets.QGroupBox("Gemini CLI Settings (Optional fallback)")
        cli_layout = QtWidgets.QVBoxLayout(cli_group)
        
        cli_layout.addWidget(QtWidgets.QLabel("<b>Gemini CLI Path:</b>"))
        path_layout = QtWidgets.QHBoxLayout()
        self.path_input = QtWidgets.QLineEdit()
        default_path = "/usr/bin/gemini" if os.name != 'nt' else "gemini.exe"
        self.path_input.setText(self.settings.value("gemini_assistant/cli_path", default_path))
        path_layout.addWidget(self.path_input)
        
        self.browse_btn = QtWidgets.QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.clicked.connect(self.browse_cli)
        path_layout.addWidget(self.browse_btn)
        cli_layout.addLayout(path_layout)
        
        # OAuth Button (only if CLI is used)
        self.oauth_btn = QtWidgets.QPushButton("🔑 Login via Gemini CLI (Requires CLI installed)")
        self.oauth_btn.clicked.connect(self.run_oauth)
        cli_layout.addWidget(self.oauth_btn)
        
        layout.addWidget(cli_group)
        layout.addStretch()
        
        # Bottom Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def test_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            QtWidgets.QMessageBox.warning(self, "Test", "Please enter an API Key first.")
            return
            
        try:
            import requests
            # Use v1beta gemini-flash-latest
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}"
            data = {"contents": [{"parts": [{"text": "Hello"}]}]}
            res = requests.post(url, json=data, timeout=15)
            if res.status_code == 200:
                QtWidgets.QMessageBox.information(self, "Test Successful", "Connection successful! Gemini is ready.")
            elif res.status_code == 503:
                QtWidgets.QMessageBox.warning(self, "Warning", "Service Busy (503). Your key is valid, but Google's server is busy. Try again later.")
            else:
                error_msg = f"Status {res.status_code}: {res.text}"
                QtWidgets.QMessageBox.critical(self, "Test Failed", f"Could not connect:\n{error_msg}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Connection error: {str(e)}")

    def browse_cli(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Gemini CLI executable", "", "Executable (*.exe);;All files (*)")
        if filename:
            self.path_input.setText(filename)

    def run_oauth(self):
        cli = self.path_input.text()
        if not cli or not os.path.exists(cli):
            # Try to find it in PATH
            import shutil
            if not shutil.which(cli):
                QtWidgets.QMessageBox.warning(self, "Error", "Gemini CLI not found. Please provide a valid path or use an API Key above.")
                return

        try:
            if os.name == 'nt':
                # Use 'start' with cmd /c to let Windows handle it properly
                subprocess.Popen(['cmd', '/c', 'start', cli, 'login'], shell=True)
            else:
                # Try common Linux terminal emulators
                terminals = ['konsole', 'gnome-terminal', 'xfce4-terminal', 'lxterminal', 'xterm']
                success = False
                for term in terminals:
                    if subprocess.run(['which', term], capture_output=True).returncode == 0:
                        if term == 'gnome-terminal':
                            subprocess.Popen([term, '--', cli, 'login'])
                        else:
                            subprocess.Popen([term, '-e', f'{cli} login'])
                        success = True
                        break
                
                if not success:
                    subprocess.Popen([cli, 'login'])
            
            QtWidgets.QMessageBox.information(self, "OAuth", "Login process started in a separate window. Follow the instructions.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not launch login: {str(e)}")

    def save(self):
        self.settings.setValue("gemini_assistant/api_key", self.api_key_input.text())
        self.settings.setValue("gemini_assistant/cli_path", self.path_input.text())
        self.accept()

class GeminiWorker(QtCore.QThread):
    finished = QtCore.pyqtSignal(str, str) # response, error

    def __init__(self, api_key, prompt):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt

    def run(self):
        try:
            import requests
            # Usando v1beta e gemini-flash-latest para maior compatibilidade
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={self.api_key}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": self.prompt}]}]
            }
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 503:
                self.finished.emit("", "O serviço do Gemini está instável no momento (Erro 503). Tente novamente em alguns segundos.")
                return
                
            response.raise_for_status()
            res_json = response.json()
            
            if 'candidates' in res_json and len(res_json['candidates']) > 0:
                text = res_json['candidates'][0]['content']['parts'][0]['text']
                self.finished.emit(text, "")
            else:
                self.finished.emit("", f"Error: No candidates in response. {json.dumps(res_json)}")
        except ImportError:
            self.finished.emit("", "The 'requests' library is not available in your Python environment. Please install it or use the Gemini CLI fallback.")
        except Exception as e:
            self.finished.emit("", str(e))

class GeminiDockWidget(QtWidgets.QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("Gemini Assistant", parent)
        self.iface = iface
        self.setObjectName("GeminiAssistantDockWidget")
        self.settings = QgsSettings()
        
        # Create a safe temp directory for the agent to work in
        self.safe_dir = tempfile.mkdtemp(prefix="qgis_gemini_")
        
        # --- UI Setup ---
        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.widget)
        
        if hasattr(QtCore.Qt, 'Orientation') and hasattr(QtCore.Qt.Orientation, 'Vertical'):
            orientation = QtCore.Qt.Orientation.Vertical
        else:
            orientation = QtCore.Qt.Vertical
            
        self.splitter = QtWidgets.QSplitter(orientation)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #313244; height: 1px; }")
        
        # Chat History
        self.chat_history = QtWidgets.QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: sans-serif;
                font-size: 10pt;
                border: none;
            }
        """)
        self.splitter.addWidget(self.chat_history)
        
        # Log View
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit {
                background-color: #11111b; 
                color: #a6e3a1; 
                font-family: monospace; 
                font-size: 9pt; 
                border: none;
            }
        """)
        self.splitter.addWidget(self.log_view)
        
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)
        self.layout.addWidget(self.splitter)
        
        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("Ask Gemini to do something in QGIS...")
        self.input_field.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 6px; border-radius: 4px;")
        self.input_field.returnPressed.connect(self.send_command)
        self.layout.addWidget(self.input_field)
        
        self.button_layout = QtWidgets.QHBoxLayout()
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        
        self.settings_btn = QtWidgets.QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #f38ba8; color: #1e1e2e; font-weight: bold;")
        self.cancel_btn.clicked.connect(self.cancel_command)
        self.cancel_btn.hide()
        
        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.setStyleSheet("background-color: #89b4fa; color: #1e1e2e; font-weight: bold;")
        self.send_btn.clicked.connect(self.send_command)
        
        self.button_layout.addWidget(self.clear_btn)
        self.button_layout.addWidget(self.settings_btn)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.cancel_btn)
        self.button_layout.addWidget(self.send_btn)
        self.layout.addLayout(self.button_layout)
        
        self.setWidget(self.widget)
        
        # --- QProcess & Context ---
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.SeparateChannels if hasattr(QtCore.QProcess, 'ProcessChannelMode') else 0)
        self.process.readyReadStandardOutput.connect(self.on_stdout_ready)
        self.process.readyReadStandardError.connect(self.on_stderr_ready)
        self.process.finished.connect(self.on_process_finished)

        self.full_response = ""
        self.last_response_pos = 0
        self.chat_context = []
        self.worker = None # For direct API calls
        
        self.append_chat("Gemini Assistant initialized. Direct API and QGIS 4 support enabled. How can I help?", is_system=True)

    def get_end_cursor(self):
        cursor = self.chat_history.textCursor()
        if hasattr(QtGui.QTextCursor, 'MoveOperation') and hasattr(QtGui.QTextCursor.MoveOperation, 'End'):
            op = QtGui.QTextCursor.MoveOperation.End
        elif hasattr(QtGui.QTextCursor, 'End'):
            op = QtGui.QTextCursor.End
        else:
            op = 11
        cursor.movePosition(op)
        return cursor

    def append_chat(self, text, is_user=False, is_system=False):
        cursor = self.get_end_cursor()
        self.chat_history.setTextCursor(cursor)

        if is_user:
            html_text = f"<p style='margin-bottom: 8px;'><b style='color: #a6e3a1;'>You:</b><br><span style='color: #cdd6f4;'>{html.escape(text)}</span></p>"
            self.chat_history.append(html_text)
        elif is_system:
            html_text = f"<p style='margin-bottom: 8px;'><i style='color: #f9e2af;'>{text}</i></p>"
            self.chat_history.append(html_text)
        else: # Gemini header
            html_header = f"<p style='margin-bottom: 4px;'><b style='color: #89b4fa;'>Gemini:</b></p>"
            self.chat_history.append(html_header)
            
            cursor = self.get_end_cursor()
            cursor.insertHtml("<span></span>")
            self.last_response_pos = cursor.position()
            cursor.insertHtml("<i id='thinking' style='color: #f9e2af;'>Thinking...</i>")
            
        self.chat_history.ensureCursorVisible()

    def format_markdown(self, text):
        parts = text.split("```")
        html_out = ""
        for i, part in enumerate(parts):
            if i % 2 == 1: # Code block
                lines = part.split("\n", 1)
                code = lines[1] if len(lines) > 1 else ""
                code_esc = html.escape(code).replace("\n", "<br>").replace(" ", "&nbsp;")
                html_out += f'<div style="background-color: #24273a; font-family: monospace; border: 1px solid #494d64; padding: 10px; margin: 8px 0; color: #a6e3a1; border-radius: 4px;">{code_esc}</div>'
            else:
                text_esc = html.escape(part).replace("\n", "<br>")
                html_out += f'<span style="color: #cdd6f4; font-family: sans-serif;">{text_esc}</span>'
        return html_out

    def render_gemini_response(self, text):
        cursor = self.chat_history.textCursor()
        cursor.setPosition(self.last_response_pos)
        
        if hasattr(QtGui.QTextCursor, 'MoveOperation') and hasattr(QtGui.QTextCursor.MoveOperation, 'End'):
            op_end = QtGui.QTextCursor.MoveOperation.End
        else:
            op_end = 11
            
        if hasattr(QtGui.QTextCursor, 'MoveMode') and hasattr(QtGui.QTextCursor.MoveMode, 'KeepAnchor'):
            mode = QtGui.QTextCursor.MoveMode.KeepAnchor
        else:
            mode = 1
            
        cursor.movePosition(op_end, mode)
        cursor.removeSelectedText()
        
        noise_patterns = [r"YOLO mode", r"Loaded cached", r"API_KEY are set", r"Using GOOGLE_API_KEY"]
        lines = text.splitlines()
        clean_lines = [l for l in lines if not any(re.search(p, l) for p in noise_patterns)]
        clean_text = "\n".join(clean_lines)
        
        formatted_html = self.format_markdown(clean_text)
        cursor.insertHtml(formatted_html)
        self.chat_history.ensureCursorVisible()

    def append_log(self, text, is_error=False):
        if not text.strip(): return
        color = "#f38ba8" if is_error else "#cba6f7"
        clean_text = text.replace("[33m", "").replace("[39m", "").replace("[0m", "")
        self.log_view.append(f"<span style='color: {color};'>[{QtCore.QDateTime.currentDateTime().toString('hh:mm:ss')}]</span> {clean_text}")
        self.log_view.ensureCursorVisible()

    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def get_execution_context(self):
        """Builds a robust execution context by mirroring qgis.core and qgis.gui."""
        import qgis.core
        import qgis.gui
        
        context = {}
        
        # Populate context from core and gui automatically
        for module in [qgis.core, qgis.gui]:
            for name in dir(module):
                if not name.startswith('_'):
                    context[name] = getattr(module, name)
            
        # Add key convenience objects
        context['iface'] = self.iface
        context['QgsProject'] = qgis.core.QgsProject.instance()
            
        return context

    def send_command(self):
        cli_path = self.settings.value("gemini_assistant/cli_path", "gemini")
        api_key = self.settings.value("gemini_assistant/api_key", "")

        cmd = self.input_field.text().strip()
        if not cmd: return
        
        self.append_chat(cmd, is_user=True)
        self.input_field.clear()
        self.set_running_state(True)
        
        self.append_chat("") 
        self.full_response = ""

        qgis_version = Qgis.QGIS_VERSION.split('-')[0]
        pyqt_major = PYQT_VERSION_STR.split('.')[0]
        pyqt_label = f"PyQt{pyqt_major}"
        
        layers = [l.name() for l in QgsProject.instance().mapLayers().values()]
        layers_str = ", ".join(layers) if layers else "No layers loaded"
        
        system_prompt = (
            f"You are an attentive and expert QGIS Automation Assistant. Your goal is to help users manipulate QGIS using PyQGIS.\n"
            f"Environment: QGIS {qgis_version}, {pyqt_label}. Loaded Layers: [{layers_str}].\n\n"
            "Guidelines:\n"
            "1. Always wrap your PyQGIS code in a single ```python block.\n"
            "2. The FIRST LINE of the code block MUST be: # QGIS_RUN\n"
            "3. Provide a brief and helpful explanation of the generated code.\n"
            "4. Be polite, professional, and proactive in your responses.\n"
            "5. Focus strictly on the QGIS API. Do not apologize for limitations; instead, provide the best possible code solution."
        )
        
        full_prompt = system_prompt + "\n\n"
        for msg in self.chat_context[-10:]:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            full_prompt += f"{role}: {msg['content']}\n"
        full_prompt += f"USER: {cmd}"
        
        self.chat_context.append({"role": "user", "content": cmd})
        
        # Use direct API if key is present
        if api_key:
            self.worker = GeminiWorker(api_key, full_prompt)
            self.worker.finished.connect(self.on_worker_finished)
            self.worker.start()
        else:
            # Fallback to CLI
            env = QtCore.QProcessEnvironment.systemEnvironment()
            env.insert("PAGER", "cat")
            if api_key:
                env.insert("GOOGLE_API_KEY", api_key)
                env.insert("GEMINI_API_KEY", api_key)
            
            self.process.setProcessEnvironment(env)
            self.process.setWorkingDirectory(self.safe_dir)
            self.process.start(cli_path, ['-p', full_prompt, '--yolo'])

    def on_worker_finished(self, response, error):
        self.set_running_state(False)
        if error:
            self.append_log(f"API Error: {error}", is_error=True)
            self.render_gemini_response(f"Sorry, an error occurred: {error}")
        else:
            self.full_response = response
            self.render_gemini_response(response)
            self.chat_context.append({"role": "assistant", "content": response})
            self.check_for_execution(response)

    def on_stdout_ready(self):
        try:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            self.full_response += data
            if self.full_response.strip():
                self.render_gemini_response(self.full_response)
        except Exception as e:
            self.append_log(f"Stdout error: {str(e)}")

    def on_stderr_ready(self):
        data = self.process.readAllStandardError().data().decode()
        self.append_log(data)

    def on_process_finished(self):
        self.set_running_state(False)
        if not self.full_response.strip():
            self.render_gemini_response("(No response or error)")
        else:
            self.chat_context.append({"role": "assistant", "content": self.full_response})
        self.check_for_execution(self.full_response)

    def cancel_command(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.append_chat("API call cancelled.", is_system=True)
            self.set_running_state(False)
            
        if self.process.state() != 0:
            self.process.kill()
            self.append_chat("Cancelled.", is_system=True)

    def clear_all(self):
        self.chat_history.clear()
        self.log_view.clear()
        self.chat_context = []
        self.append_chat("History cleared.", is_system=True)

    def set_running_state(self, running):
        self.input_field.setEnabled(not running)
        self.send_btn.setHidden(running)
        self.clear_btn.setHidden(running)
        self.settings_btn.setHidden(running)
        self.cancel_btn.setVisible(running)

    def check_for_execution(self, response):
        if "```python" in response and "# QGIS_RUN" in response:
            try:
                code_blocks = re.findall(r"```python\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
                code = ""
                for b in code_blocks:
                    if "# QGIS_RUN" in b:
                        code = b.strip()
                        break
                
                if not code and "# QGIS_RUN" in response:
                    code = response.split("# QGIS_RUN")[1].split("```")[0].strip()
                    code = "# QGIS_RUN\n" + code

                if not code: return

                self.append_log("Executing generated script...")
                context = self.get_execution_context()
                exec(code, context)
                self.append_log("Execution successful.")
            except Exception as e:
                self.append_log(f"Execution error: {str(e)}", is_error=True)

    def closeEvent(self, event):
        self.cancel_command()
        try:
            import shutil
            shutil.rmtree(self.safe_dir)
        except:
            pass
        super().closeEvent(event)
