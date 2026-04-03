def classFactory(iface):
    from .gemini_assistant import GeminiAssistant
    return GeminiAssistant(iface)
