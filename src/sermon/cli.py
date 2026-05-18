from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label


class SermonApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Sermon — Serial Monitor")
        yield Footer()


def main() -> None:
    app = SermonApp()
    app.run()
