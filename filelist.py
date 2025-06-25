from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import ListProperty
import os

class FileList(BoxLayout):
    files = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.label = Label(text="Selected files:", size_hint_y=None, height=24)
        self.add_widget(self.label)
        self.file_labels = []
        self.update_files()
        self.bind(files=lambda *a: self.update_files())

    def update_files(self, *args):
        for lbl in self.file_labels:
            self.remove_widget(lbl)
        self.file_labels = []
        for f in self.files:
            lbl = Label(text=os.path.basename(f), size_hint_y=None, height=24)
            self.add_widget(lbl)
            self.file_labels.append(lbl)
