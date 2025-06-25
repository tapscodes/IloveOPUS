import threading
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, NumericProperty
from kivy.lang import Builder

from filelist import FileList
from conversion import get_downloads_folder, convert_files
from config import SUPPORTED_EXTS

class AudioConverterApp(App):
    selected_files = ListProperty([])
    status_text = StringProperty("Ready")
    progress = NumericProperty(0)

    def build(self):
        Builder.load_file("style.kv")
        self.title = "iLoveOPUS"
        # Use RootWidget for .kv styling
        root = BoxLayout(orientation='vertical', spacing=10)
        root.__class__.__name__ = "RootWidget"

        # Generate glob patterns from SUPPORTED_EXTS
        file_patterns = [f'*{ext}' for ext in SUPPORTED_EXTS]

        def open_file_chooser(instance):
            # Create a NEW file chooser each time to avoid WidgetException
            file_chooser = FileChooserListView(
                path=get_downloads_folder(),
                filters=file_patterns,
                multiselect=True
            )
            popup_layout = BoxLayout(orientation='vertical', spacing=10)
            popup_layout.add_widget(file_chooser)

            btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
            select_btn = Button(text="Select file(s)")
            cancel_btn = Button(text="Cancel")
            btn_layout.add_widget(select_btn)
            btn_layout.add_widget(cancel_btn)
            popup_layout.add_widget(btn_layout)

            popup = Popup(title="Select Audio Files",
                          content=popup_layout,
                          size_hint=(0.9, 0.9))

            def do_select(*a):
                # Ensure self.selected_files is always a list (never None)
                if self.selected_files is None:
                    self.selected_files = []
                # Add new selections to the existing list, avoiding duplicates
                new_files = [f for f in file_chooser.selection if f not in self.selected_files]
                self.selected_files = list(self.selected_files) + new_files
                self.file_list.files = self.selected_files
                popup.dismiss()

            def do_cancel(*a):
                popup.dismiss()

            select_btn.bind(on_release=do_select)
            cancel_btn.bind(on_release=do_cancel)
            file_chooser.bind(on_submit=lambda *a: do_select())

            popup.open()

        self.file_list = FileList()
        root.add_widget(self.file_list)

        # Place select and convert buttons side by side under the file selector
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        select_btn = Button(text="Select Audio Files")
        convert_btn = Button(text="Convert to 320kbps OPUS")
        select_btn.bind(on_release=open_file_chooser)
        convert_btn.bind(on_release=self.start_conversion)
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(convert_btn)
        root.add_widget(btn_layout)

        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=20)
        root.add_widget(self.progress_bar)
        self.status_label = Label(text=self.status_text, size_hint_y=None, height=30)
        root.add_widget(self.status_label)

        self.bind(status_text=lambda *a: setattr(self.status_label, 'text', self.status_text))
        self.bind(progress=lambda *a: setattr(self.progress_bar, 'value', self.progress))

        return root

    def start_conversion(self, instance):
        if not self.selected_files:
            self.status_text = "No files selected."
            return
        threading.Thread(target=self._convert_files_thread, daemon=True).start()

    def _convert_files_thread(self):
        def status_callback(text):
            self.status_text = text
        def progress_callback(val):
            self.progress = val
        convert_files(self.selected_files, status_callback, progress_callback)

if __name__ == "__main__":
    AudioConverterApp().run()
