import os
import time
from xml.etree import ElementTree

from converters.base import AbstractConverter
from converters.helpers import utils


class OpenLyricsConverter(AbstractConverter):
    def __init__(self, args):
        super().__init__()
        self._from_dir = args.from_dir
        self._out_dir = args.to_dir
        self._openlp = args.openlp

    @staticmethod
    def create_argparser(subparsers):
        parser_openlyrics = subparsers.add_parser("openlyrics", help="Converts to OpenLyrics format.")
        parser_openlyrics.add_argument("--to-dir", required=True, help="directory of target files; will be deleted if exists")
        parser_openlyrics.add_argument("--openlp", action='store_true', help="adds adjustments for easier song management in OpenLP")
        return parser_openlyrics

    def setup(self):
        super()._create_out_dir(self._out_dir)
        ElementTree.register_namespace('', "http://openlyrics.info/namespace/2009/song")

    def convert(self, song_yaml, filepath):
        self._preprocessor.preprocess(song_yaml, soft_line_break_strategy='ignore')

        # Look up primary language
        emm_hu_book = self._get_book_from_yaml(song_yaml, 'emm_hu')
        if emm_hu_book is None:
            return

        # Look up lyrics for primary language
        song_lyrics = self._get_lyrics_from_yaml(song_yaml, emm_hu_book['lang'])

        # Assemble XML
        ol_song = ElementTree.Element('song', attrib={
            'version': '0.8',
            'createdIn': 'Emmet.yaml Converter',
            'modifiedIn': 'Emmet.yaml Converter',
            'modifiedDate': time.strftime("%Y-%m-%dT%H:%M:%S%z")
        })

        ol_properties = ElementTree.SubElement(ol_song, 'properties')
        ol_titles = ElementTree.SubElement(ol_properties, 'titles')
        ol_title = ElementTree.SubElement(ol_titles, 'title')
        if self._openlp:
            ol_title.text = utils.pad_song_number(emm_hu_book['number'])+" "+song_lyrics['title']
        else:
            ol_title.text = song_lyrics['title']
        ol_songbooks = ElementTree.SubElement(ol_properties, 'songbooks')
        ol_songbook = ElementTree.SubElement(ol_songbooks, 'songbook', attrib={
            'name': 'Jézus él!', 'entry': emm_hu_book['number']
        })

        ol_lyrics = ElementTree.SubElement(ol_song, 'lyrics')
        for verse in song_lyrics['verses']:
            verse_parts = self._split_verse_on_hard_breaks(verse['lines'])
            ol_verse = ElementTree.SubElement(ol_lyrics, 'verse', attrib={
                'name': verse['name']
            })

            for i, verse_part in enumerate(verse_parts):
                ol_lines = ElementTree.SubElement(ol_verse, 'lines')
                if i < len(verse_part)-1:
                    ol_lines.set('break', 'optional')
                is_first = True
                if self._openlp and verse['name'].lower().startswith('c'):
                    verse_part[0] = '{it}' + verse_part[0]
                    verse_part[-1] += '{/it}'
                for line in verse_part:
                    if is_first:
                        ol_lines.text = line
                        is_first = False
                    else:
                        ElementTree.SubElement(ol_lines, 'br').tail = "\n"+line

        # Write XML
        ol_tree = ElementTree.ElementTree(ol_song)
        filename = "{song_no}-{lang}-{title}.xml".format(
            song_no=emm_hu_book['number'], lang=emm_hu_book['lang'], title=song_lyrics['title']
        )
        ol_tree.write(os.path.join(self._out_dir, filename), encoding='utf-8')
