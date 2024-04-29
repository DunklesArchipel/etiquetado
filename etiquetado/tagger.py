import time
import yaml
import re
import glob
import os

from ipywidgets import widgets, HBox, VBox, Layout
from IPython.display import clear_output

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path


def extract_number(input_string):
    # A helper function to `create_metadata`
    # extract a number from a line of the MPT header
    pattern = r'\b(\d+(,\d+)*(\.\d+)?)\b'
    matches = re.findall(pattern, input_string)
    if matches:
        match = matches[0][0]
        if ',' in match:
            return float(matches[0][0].replace(',', '.'))
        return match
    else:
        return None


class TaggedFiles():

    def __init__(self, outdir='files/data_exported'):

        self.outdir = outdir

        self.tagged_files = widgets.SelectMultiple(
            options=self.get_tagged_files(),
            #rows=10,
            description='Tagged Files',
            disabled=False,
            style={'description_width' : 'initial'},
            layout=Layout(width='600px', height='180px', flex='flex-grow')
        )

        self.button_convert_files = widgets.Button(description='Convert selected files')
        self.button_convert_files.on_click(self.on_convert_files)

    def add_tagged_files(self, option):
        new_options = [_ for _ in self.tagged_files.options]
        new_options.append(option)
        self.tagged_files.options = new_options
        self.write_tagged_files(new_options)

    def write_tagged_files(self, options):
        tagged = {'tagged files': options}
        with open('tagged_files.yaml', 'w') as f:
            yaml.dump(tagged, f)

    def remove_tagged_files(self):
        new_options = [_ for _ in self.tagged_files.options if not _ in self.tagged_files.value]
        self.tagged_files.options = new_options
        self.write_tagged_files(new_options)

    def get_tagged_files(self):
        with open('tagged_files.yaml', 'rb') as f:
            tagged_files_saved = yaml.load(f, Loader=yaml.SafeLoader)
        return tagged_files_saved['tagged files']

    def convert_file(self, filename):
        from converter import BilogicPeisMPT
        loaded = BilogicPeisMPT(filename)
        loaded.convert(outdir=self.outdir)

    def on_convert_files(self, *args):
        for filename in self.tagged_files.value:
            self.convert_file(filename=filename)
        self.remove_tagged_files()

    def layout(self):
        return VBox(children=[self.tagged_files, self.button_convert_files])


class BasicTagger(FileSystemEventHandler):

    def __init__(self, *file_processing_methods, suffix='csv'):
        self.suffix = suffix
        self.file_processing_methods = file_processing_methods

    def on_created(self, event):
        # print the name of the newly created file
        if event.is_directory:
            print(f"Directory with name {event.src_path} was created. No further actions were taken.")
        if Path(event.src_path).suffix == self.suffix:
            # print(event.src_path, ' ' , Path(event.src_path).suffix)
            filename = event.src_path
            # When a new file is created we catch the filename and parse it to a method
            # that generates output yaml files and markdown files for additional notes
            for method in self.file_processing_methods:
                method(filename)

class TaggerGui(TaggedFiles):

    def __init__(self,
                 folder_path="files/data/",
                 file_suffix = ".csv",
                 folder_yaml_templates= 'files/yaml_templates/',
                 default_yaml_template='template_metadata.yaml', # a file in the folder_yaml_templates
                 outdir='files/data_exported'):

        TaggedFiles.__init__(self, outdir=outdir)

        self.folder_path = folder_path
        self.file_suffix = file_suffix
        self.folder_yaml_templates = folder_yaml_templates
        self.yaml_template = default_yaml_template
        self.outdir = outdir

        # Updated when a watchdog task is created
        self.observer = None
        self.watched_folder = None
        self.current_suffix = None

        # Widgets
        # Input widgets
        self.text_box_folder_path = widgets.Text(description='folder path', value=self.folder_path)
        self.text_box_file_suffix = widgets.Text(description='file suffix', value=self.file_suffix)

        self.yaml_templates = glob.glob(os.path.join(self.folder_yaml_templates, '**.yaml'))
        self.dropdown_yaml= widgets.Dropdown(description='Yaml templates', options=self.yaml_templates)

        ## Top row
        self.button_start = widgets.Button(description='Start watching')
        self.button_stop = widgets.Button(description='Stop watching')
        self.button_clear_output = widgets.Button(description='Clear output')

        ## second row
        self.indicator = widgets.Button(description='Offline')
        self.indicator.style.button_color = 'red'
        self.indicator.style.text_color = 'black'
        self.status = widgets.Valid(value=False, description='Measuring',)

        ## output
        self.textoutput = widgets.Output()
        self.gui = widgets.Output()

        ## Widget interactions
        self.button_start.on_click(self.on_start)
        self.button_stop.on_click(self.on_stop)

    def process_tagged_file(self, filename):
        return print(filename)

    def create_observer(self):
        observer = Observer()
        self.watched_folder = self.text_box_folder_path.value
        self.current_suffix = self.text_box_file_suffix.value
        observer.schedule(BasicTagger(self.add_tagged_files,
                                      self.process_tagged_file,
                                      suffix=self.current_suffix),
                                      self.watched_folder, recursive=False)
        self.observer = observer

    def start(self):
        if self.observer:
            if self.observer.is_alive():
                with self.textoutput:
                    # clear_output(wait=True)
                    print("Stop observer before restarting.")
                    print(f"Currently observing files with suffix '{self.current_suffix}' in folder '{self.watched_folder}'.")
                return None
        self.create_observer()
        self.observer.start()
        self.indicator.style.button_color = 'lightgreen'
        self.indicator.description = 'Watching'
        self.status.value = True
        with self.textoutput:
            # clear_output(wait=True)  # uncomment to clear the output widget
            print(f"start watching files with suffix '{self.current_suffix}' in folder '{self.watched_folder}")

    def stop(self):
        self.observer.stop()
        self.indicator.style.button_color = 'red'
        self.indicator.description = 'Offline'
        self.status.value = False
        with self.textoutput:
            #clear_output(wait=True)  # uncomment to clear the output widget
            print('Stop watching')

    def on_stop(self, *args):
        self.stop()

    def on_start(self, *args):
        self.start()

    def layout(self):
        r"""Layout of the GUI"""
        input_boxes = VBox(children=[self.text_box_folder_path, self.text_box_file_suffix, self.dropdown_yaml])
        buttons = HBox(children=[self.button_start, self.button_stop])
        buttons_2 = HBox(children=[self.indicator, self.status])
        outputs = HBox(children=[self.textoutput])
        left_panel = VBox(children=[input_boxes, buttons, buttons_2])
        right_panel = VBox(children=[self.tagged_files, self.button_convert_files])
        top = HBox(children=[left_panel, right_panel])
        out = VBox(children=[top, outputs])
        with self.gui:
            return out


class TagPeisGui(TaggerGui):

    def process_tagged_file(self, filename):
        # wait a second to ensure that the file is created
        # otherwise a file permission error will be raised
        time.sleep(1)

        # extract the applied voltage from file metadata
        with open(filename, 'rb') as f:
            data = [line.decode('ANSI') for line in f.readlines()]

        E_appl = [line for line in data if 'E (V)' in line][0]

        # load the metadata from a yaml template
        with open(self.dropdown_yaml.value, 'rb') as f:
            metadata = yaml.load(f, Loader=yaml.SafeLoader)

        # Update and or add new metadata extracted from the created file
        metadata.setdefault('E applied', {'value': extract_number(E_appl), 'unit':'V'})
        # Update metadata
        metadata.setdefault('sample', 'demo sample')
        metadata['system']['type'] = 'some other system'
        # for electrode in metadata['system']['electrodes']:
        # if electrode['name'] == 'WE':
        #     electrode['components'][0]['name'] = sample_name

        outyaml = Path(filename).with_suffix('.mpt.yaml')
        with open(outyaml, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f)

        markdown_content = markdown_content = """=Measurement Notes=

For filename: `{}`

No remarks.
""".format(filename)

        # write an empty markdown file to annotate the data later on
        md_filename = outyaml = Path(filename).with_suffix('.wikimd')
        with open(md_filename, "w", encoding='utf-8') as f:
            f.write(markdown_content)
