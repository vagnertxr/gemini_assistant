# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets, QtCore, QtGui
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsSettings
import os
import subprocess

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini Assistant Settings")
        self.resize(400, 250)
        self.settings = QgsSettings()
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # API Key
        layout.addWidget(QtWidgets.QLabel("<b>Google API Key:</b> (Optional if using OAuth)"))
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.settings.value("gemini_assistant/api_key", ""))
        layout.addWidget(self.api_key_input)
        
        link_lbl = QtWidgets.QLabel("<a href='https://aistudio.google.com/app/apikey'>Get API Key from Google AI Studio</a>")
        link_lbl.setOpenExternalLinks(True)
        layout.addWidget(link_lbl)
        
        layout.addSpacing(10)
        
        # Gemini CLI Path
        layout.addWidget(QtWidgets.QLabel("<b>Gemini CLI Path:</b>"))
        path_layout = QtWidgets.QHBoxLayout()
        self.path_input = QtWidgets.QLineEdit()
        default_path = "/usr/bin/gemini" if os.name != 'nt' else "gemini.exe"
        self.path_input.setText(self.settings.value("gemini_assistant/cli_path", default_path))
        path_layout.addWidget(self.path_input)
        
        self.browse_btn = QtWidgets.QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.clicked.connect(self.browse_cli)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)
        
        layout.addSpacing(10)
        
        # OAuth Button
        self.oauth_btn = QtWidgets.QPushButton("🔑 Login via Google OAuth (Browser)")
        self.oauth_btn.clicked.connect(self.run_oauth)
        layout.addWidget(self.oauth_btn)
        
        layout.addStretch()
        
        # Bottom Buttons
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def browse_cli(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Gemini CLI executable", "", "Executable (*.exe);;All files (*)")
        if filename:
            self.path_input.setText(filename)

    def run_oauth(self):
        cli = self.path_input.text()
        try:
            if os.name == 'nt':
                subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', f'"{cli}" login'], shell=True)
            else:
                # Try common Linux terminal emulators
                terminals = ['konsole', 'gnome-terminal', 'xfce4-terminal', 'lxterminal', 'xterm']
                success = False
                for term in terminals:
                    # Check if terminal exists
                    if subprocess.run(['which', term], capture_output=True).returncode == 0:
                        if term == 'gnome-terminal':
                            subprocess.Popen([term, '--', cli, 'login'])
                        else:
                            subprocess.Popen([term, '-e', f'{cli} login'])
                        success = True
                        break
                
                if not success:
                    # Fallback: try to run directly, might work if it just opens a browser
                    subprocess.Popen([cli, 'login'])
            
            QtWidgets.QMessageBox.information(self, "OAuth", "Login process started. Follow the instructions in your browser or terminal.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not launch login: {str(e)}")

    def save(self):
        self.settings.setValue("gemini_assistant/api_key", self.api_key_input.text())
        self.settings.setValue("gemini_assistant/cli_path", self.path_input.text())
        self.accept()

class GeminiDockWidget(QtWidgets.QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("Gemini Assistant", parent)
        self.iface = iface
        self.setObjectName("GeminiAssistantDockWidget")
        self.settings = QgsSettings()
        
        # --- UI Setup ---
        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.widget)
        
        self.tabs = QtWidgets.QTabWidget()
        self.chat_history = QtWidgets.QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; font-family: monospace; font-size: 10pt;")
        self.tabs.addTab(self.chat_history, "💬 Chat")
        
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #11111b; color: #a6e3a1; font-family: monospace; font-size: 9pt;")
        self.tabs.addTab(self.log_view, "📜 Log")
        
        self.layout.addWidget(self.tabs)
        
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
        
        # --- QProcess Setup ---
        self.process = QtCore.QProcess(self)
        # Separate channels to filter system logs from chat
        self.process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.SeparateChannels if hasattr(QtCore.QProcess, 'ProcessChannelMode') else 0)
        
        self.process.readyReadStandardOutput.connect(self.on_stdout_ready)
        self.process.readyReadStandardError.connect(self.on_stderr_ready)
        self.process.finished.connect(self.on_process_finished)

        self.full_response = ""
        self.append_chat("Gemini Assistant initialized. How can I help you map today?", is_system=True)

    def append_chat(self, text, is_user=False, is_system=False, stream=False):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End if hasattr(QtGui.QTextCursor, 'MoveOperation') else 11)
        self.chat_history.setTextCursor(cursor)

        if stream:
            # Filter out common CLI noise that might still leak into stdout
            noise = ["YOLO mode", "Loaded cached", "API_KEY are set", "Using GOOGLE_API_KEY"]
            clean_text = text
            for n in noise:
                if n in clean_text:
                    # Redirect noise to log instead of chat
                    self.append_log(clean_text.strip())
                    return

            self.chat_history.insertHtml(clean_text.replace(chr(10), '<br>'))
        else:
            if is_user:
                html = f"<p style='margin-bottom: 8px;'><b style='color: #a6e3a1;'>You:</b><br>{text}</p>"
            elif is_system:
                html = f"<p style='margin-bottom: 8px;'><i style='color: #f9e2af;'>{text}</i></p>"
            else: # Gemini header
                html = f"<p style='margin-bottom: 8px;'><b style='color: #89b4fa;'>Gemini:</b><br>"
            self.chat_history.append(html)
        self.chat_history.ensureCursorVisible()

    def append_log(self, text, is_error=False):
        if not text.strip(): return
        color = "#f38ba8" if is_error else "#cba6f7"
        # Clean terminal escape codes if any
        clean_text = text.replace("[33m", "").replace("[39m", "").replace("[0m", "")
        self.log_view.append(f"<span style='color: {color};'>[{QtCore.QDateTime.currentDateTime().toString('hh:mm:ss')}]</span> {clean_text}")
        self.log_view.ensureCursorVisible()

    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def send_command(self):
        cli_path = self.settings.value("gemini_assistant/cli_path", "gemini")
        api_key = self.settings.value("gemini_assistant/api_key", "")

        cmd = self.input_field.text().strip()
        if not cmd: return
        
        self.append_chat(cmd, is_user=True)
        self.input_field.clear()
        self.set_running_state(True)
        self.tabs.setCurrentIndex(0)
        
        self.append_chat("") 
        self.full_response = ""

        system_prompt = (
            "You are an expert QGIS assistant. If asked to perform an action, provide python code "
            "wrapped in ```python blocks with # QGIS_RUN as the first line. The `iface` and `QgsProject` "
            "objects are available. Output only the explanation and the code block."
        )
        full_prompt = system_prompt + chr(10) + chr(10) + "User request: " + cmd
        
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert("PAGER", "cat")
        if api_key:
            env.insert("GOOGLE_API_KEY", api_key)
            env.insert("GEMINI_API_KEY", api_key)
        
        self.process.setProcessEnvironment(env)
        self.process.start(cli_path, ['-p', full_prompt, '--yolo'])

    def on_stdout_ready(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.full_response += data
        self.append_chat(data, stream=True)

    def on_stderr_ready(self):
        data = self.process.readAllStandardError().data().decode()
        self.append_log(data)

    def on_process_finished(self):
        self.set_running_state(False)
        self.check_for_execution(self.full_response)

    def cancel_command(self):
        if self.process.state() != 0:
            self.process.kill()
            self.append_chat("Cancelled.", is_system=True)

    def clear_all(self):
        self.chat_history.clear()
        self.log_view.clear()
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
                code = response.split("# QGIS_RUN")[1].split("```")[0].strip()
                self.append_log("Executing generated script...")
                self.tabs.setCurrentIndex(1)
                
                local_vars = {'iface': self.iface, 'QgsProject': QgsProject.instance(), 'Qgis': Qgis}
                exec("from qgis.core import *; from qgis.gui import *", globals(), local_vars)
                exec(code, globals(), local_vars)
                self.append_log("Execution successful.")
            except Exception as e:
                self.append_log(f"Execution error: {str(e)}", is_error=True)

    def closeEvent(self, event):
        self.cancel_command()
        super().closeEvent(event)
