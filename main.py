# Set KIVY_GL_BACKEND to sdl2 for Linux, angle_sdl2 for Windows
import os
import sys

#add stylesheet to to builds
if not sys.stderr:
    os.environ['KIVY_NO_CONSOLELOG'] = '1'

if getattr(sys, 'frozen', False):
    # Only use the bundled ffmpeg, do not prepend to PATH if not found
    ffmpeg_dirs = [
        os.path.join(sys._MEIPASS, "ffmpeg-n7.1.1-22-g0f1fe3d153-linux64-gpl-7.1", "bin"),  # Linux
        os.path.join(sys._MEIPASS, "ffmpeg_bin", "ffmpeg-n7.1.1-22-g0f1fe3d153-winarm64-gpl-7.1", "bin"),  # Windows
        os.path.join(sys._MEIPASS, "ffmpeg_bin"),  # macOS
    ]
    for d in ffmpeg_dirs:
        if os.path.exists(os.path.join(d, "ffmpeg")) or os.path.exists(os.path.join(d, "ffmpeg.exe")):
            os.environ["PATH"] = d
            break
    # Add PyInstaller temp path for resource loading (style.kv, etc.)
    from kivy.resources import resource_add_path
    resource_add_path(sys._MEIPASS)

import threading
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
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.checkbox import CheckBox

from filelist import FileList
from conversion import get_downloads_folder, convert_files
from config import SUPPORTED_EXTS

class AudioConverterApp(App):
    selected_files = ListProperty([])
    status_text = StringProperty("Ready")
    progress = NumericProperty(0)
    resize_cover = True
    search_subfolders = True
    convert_in_place = True
    delete_original = False

    def build(self):
        # Load Kivy style file
        Builder.load_file("style.kv")
        self.title = "iLoveOPUS"
        root = Factory.RootWidget()

        # Generate glob patterns from SUPPORTED_EXTS
        file_patterns = [f'*{ext}' for ext in SUPPORTED_EXTS]

        # File chooser popup for selecting audio files
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

            # Add selected files to the list
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

        # Main file list widget
        self.file_list = FileList()
        root.add_widget(self.file_list)

        # Option checkboxes (fit to screen like buttons)
        options_layout = Factory.ButtonRow()
        from kivy.uix.label import Label
        self.resize_checkbox = CheckBox(active=True)
        self.subfolder_checkbox = CheckBox(active=True)
        resize_label = Label(text="Resize Cover Art to 1000x1000 JPG", size_hint_y=None, height=40)
        subfolder_label = Label(text="Search Subfolders When Selecting Folder", size_hint_y=None, height=40)
        options_layout.add_widget(self.resize_checkbox)
        options_layout.add_widget(resize_label)
        options_layout.add_widget(self.subfolder_checkbox)
        options_layout.add_widget(subfolder_label)
        root.add_widget(options_layout)

        # New row for additional options
        extra_options_layout = Factory.ButtonRow()
        self.convert_in_place_checkbox = CheckBox(active=True)
        self.delete_original_checkbox = CheckBox(active=False)
        convert_in_place_label = Label(text="Convert File In Place", size_hint_y=None, height=40)
        delete_original_label = Label(text="Delete Original File", size_hint_y=None, height=40)
        extra_options_layout.add_widget(self.convert_in_place_checkbox)
        extra_options_layout.add_widget(convert_in_place_label)
        extra_options_layout.add_widget(self.delete_original_checkbox)
        extra_options_layout.add_widget(delete_original_label)
        root.add_widget(extra_options_layout)

        # Main control buttons
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

        # Progress bar and status label
        self.progress_bar = ProgressBar()
        root.add_widget(self.progress_bar)
        self.status_label = Label(text=self.status_text)
        root.add_widget(self.status_label)

        # Bind status/progress updates to widgets
        self.bind(status_text=lambda *a: setattr(self.status_label, 'text', self.status_text))
        self.bind(progress=lambda *a: setattr(self.progress_bar, 'value', self.progress))

        # Bind checkboxes to update options
        self.resize_checkbox.bind(active=self.on_resize_checkbox)
        self.subfolder_checkbox.bind(active=self.on_subfolder_checkbox)
        self.convert_in_place_checkbox.bind(active=self.on_convert_in_place_checkbox)
        self.delete_original_checkbox.bind(active=self.on_delete_original_checkbox)

        return root

    def on_resize_checkbox(self, instance, value):
        self.resize_cover = value

    def on_subfolder_checkbox(self, instance, value):
        self.search_subfolders = value

    def on_convert_in_place_checkbox(self, instance, value):
        self.convert_in_place = value

    def on_delete_original_checkbox(self, instance, value):
        self.delete_original = value

    # Clear the selected files list
    def clear_selected_files(self):
        self.selected_files = []
        self.file_list.files = []

    # Folder chooser popup for selecting all audio files in a folder
    def open_folder_chooser(self):
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

        # Add all supported files from selected folder
        def do_select_folder(*a):
            folder = file_chooser.selection[0] if file_chooser.selection else file_chooser.path
            if not os.path.isdir(folder):
                self.status_text = "Please select a folder."
                return
            if self.search_subfolders:
                files_in_folder = []
                for rootdir, _, files in os.walk(folder):
                    files_in_folder.extend([
                        os.path.join(rootdir, f)
                        for f in files
                        if os.path.isfile(os.path.join(rootdir, f)) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
                    ])
            else:
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

    # Start conversion in a background thread
    def start_conversion(self, instance):
        if not self.selected_files:
            self.status_text = "No files selected."
            return
        threading.Thread(target=self._convert_files_thread, daemon=True).start()

    # Threaded conversion logic
    def _convert_files_thread(self):
        def status_callback(text):
            self.status_text = text
        def progress_callback(val):
            self.progress = val
        # Pass new options to convert_files
        convert_files(
            self.selected_files,
            status_callback,
            progress_callback,
            resize_cover=self.resize_cover,
            convert_in_place=self.convert_in_place,
            delete_original=self.delete_original
        )

if __name__ == "__main__":
    AudioConverterApp().run()
