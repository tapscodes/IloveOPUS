from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import ListProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import os

class FileList(BoxLayout):
    files = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.label = Label(text="Selected files:")
        self.add_widget(self.label)
        # Use a GridLayout inside a ScrollView for scrolling and alignment
        self.scrollview = ScrollView(do_scroll_x=True, do_scroll_y=True, bar_width=12)
        self.grid = GridLayout(cols=1, size_hint_y=None, size_hint_x=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.grid.bind(minimum_width=self.grid.setter('width'))
        self.scrollview.add_widget(self.grid)
        self.add_widget(self.scrollview)
        self.file_labels = []
        self.update_files()
        self.bind(files=lambda *a: self.update_files())

    def update_files(self, *args):
        for lbl in self.file_labels:
            self.grid.remove_widget(lbl)
        self.file_labels = []
        for f in self.files:
            lbl = Label(
                text=f,
                halign='right',
                valign='middle',
                size_hint_x=None,
                size_hint_y=None,
                height=24,
                width=1000  # Large enough to show long paths, adjust as needed
            )
            lbl.text_size = (lbl.width, lbl.height)
            self.grid.add_widget(lbl)
            self.file_labels.append(lbl)
        # Scroll to the far right to show the filename by default
        self.scrollview.scroll_x = 1.0
