# Gemini QGIS Assistant

The Gemini QGIS Assistant is a specialized plugin for QGIS designed to integrate the Gemini CLI directly into the geographic information system environment. It enables users to utilize large language models for spatial analysis automation, layer management, and project-wide geoprocessing tasks using natural language inputs.

## Technical Features

- **Integrated Chat Interface**: A native QGIS dock widget providing a streamlined interface for model interaction.
- **Dedicated Execution Logging**: Separation of conversational history from technical logs, ensuring clear oversight of geoprocessing outputs and system events.
- **Automated Script Execution**: Implementation of the # QGIS_RUN directive, allowing the assistant to generate and execute PyQGIS code blocks directly within the active session.
- **Authentication Support**: Compatibility with both standalone Google API Keys and OAuth-based browser authentication.
- **Cross-Platform Deployment**: Engineered for consistent performance across Windows and Linux environments.

## Full AI Development Experiment

This project was developed as a comprehensive experiment in autonomous software engineering. The architectural design, source code, user interface logic, and graphical assets (including the SVG resources) were conceived and implemented entirely by artificial intelligence agents.

## Installation

### Prerequisites
The Gemini CLI must be globally available on the host system:
```bash
npm install -g @google/gemini-cli
```

### Plugin Deployment
Extract or clone this repository into the appropriate QGIS plugin directory for your environment:
- **Linux**: `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/`
- **Windows**: `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\`

## Configuration

Upon enabling the plugin in the QGIS Plugin Manager, utilize the Settings interface to:
1. Configure the path to the Gemini CLI executable.
2. Provide a valid Google API Key (generated via Google AI Studio).
3. Alternatively, initiate the OAuth authentication process.

## License

This project is licensed under the GNU General Public License v2 or any later version, consistent with QGIS community standards.
