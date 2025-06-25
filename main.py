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
from kivy.factory import Factory

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
        root = Factory.RootWidget()

        # Generate glob patterns from SUPPORTED_EXTS
        file_patterns = [f'*{ext}' for ext in SUPPORTED_EXTS]

        def open_file_chooser(instance):
            file_chooser = FileChooserListView(
                path=get_downloads_folder(),
                filters=file_patterns,
                multiselect=True,
                show_hidden=False,
                dirselect=False
            )

            popup_layout = BoxLayout(orientation='vertical')
            popup_layout.add_widget(file_chooser)

            btn_layout = Factory.ButtonRow()
            select_btn = Button(text="Select file(s)")
            cancel_btn = Button(text="Cancel")
            btn_layout.add_widget(select_btn)
            btn_layout.add_widget(cancel_btn)
            popup_layout.add_widget(btn_layout)

            popup = Popup(title="Select Audio Files",
                          content=popup_layout,
                          size_hint=(0.95, 0.95))

            def do_select(*a):
                if self.selected_files is None:
                    self.selected_files = []
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

        btn_layout = Factory.ButtonRow()
        select_btn = Button(text="Select Audio Files")
        select_folder_btn = Button(text="Select Folder")
        clear_btn = Button(text="Clear List")
        convert_btn = Button(text="Convert to 320kbps OPUS")
        select_btn.bind(on_release=open_file_chooser)
        select_folder_btn.bind(on_release=lambda x: self.open_folder_chooser())
        clear_btn.bind(on_release=lambda x: self.clear_selected_files())
        convert_btn.bind(on_release=self.start_conversion)
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(select_folder_btn)
        btn_layout.add_widget(clear_btn)
        btn_layout.add_widget(convert_btn)
        root.add_widget(btn_layout)

        self.progress_bar = ProgressBar()
        root.add_widget(self.progress_bar)
        self.status_label = Label(text=self.status_text)
        root.add_widget(self.status_label)

        self.bind(status_text=lambda *a: setattr(self.status_label, 'text', self.status_text))
        self.bind(progress=lambda *a: setattr(self.progress_bar, 'value', self.progress))

        return root

    def clear_selected_files(self):
        self.selected_files = []
        self.file_list.files = []

    def open_folder_chooser(self):
        # Open a FileChooser in folder selection mode
        file_chooser = FileChooserListView(
            path=get_downloads_folder(),
            filters=[],  # Must be a list, not None
            multiselect=False,
            dirselect=True,
            show_hidden=False
        )

        popup_layout = BoxLayout(orientation='vertical')
        popup_layout.add_widget(file_chooser)

        btn_layout = Factory.ButtonRow()
        select_btn = Button(text="Select Folder")
        cancel_btn = Button(text="Cancel")
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        popup_layout.add_widget(btn_layout)

        popup = Popup(title="Select Folder",
                      content=popup_layout,
                      size_hint=(0.95, 0.95))

        def do_select_folder(*a):
            folder = file_chooser.selection[0] if file_chooser.selection else file_chooser.path
            if not os.path.isdir(folder):
                self.status_text = "Please select a folder."
                return
            files_in_folder = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if os.path.isfile(os.path.join(folder, f)) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
            ]
            self.selected_files = list(set(self.selected_files + files_in_folder))
            self.file_list.files = self.selected_files
            popup.dismiss()

        def do_cancel(*a):
            popup.dismiss()

        select_btn.bind(on_release=do_select_folder)
        cancel_btn.bind(on_release=do_cancel)
        file_chooser.bind(on_submit=lambda *a: do_select_folder())

        popup.open()

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
