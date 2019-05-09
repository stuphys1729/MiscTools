"""Synthesizes speech from the input string of text or ssml.

Note: ssml must be well-formed according to:
    https://www.w3.org/TR/speech-synthesis/
"""
from google.cloud import texttospeech
import PyPDF2
import os
import sys
import time
import re
import string
from google.api_core.exceptions import InvalidArgument

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO

class PdfConverter:

    def __init__(self, file_path):
       self.file_path = file_path

    # convert pdf file to a string which has space among words 
    def convert_pdf_to_txt(self, minpage=None, maxpage=None):
        start = time.time()
        rsrcmgr = PDFResourceManager()
        retstr = StringIO()
        codec = 'utf-8'  # 'utf16','utf-8'
        laparams = LAParams()
        device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
        fp = open(self.file_path, 'rb')
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        password = ""
        maxpages = 0
        caching = True
        pagenos = set(); curpageno = 0
        for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
            curpageno += 1
            if minpage:
                if curpageno < minpage:
                    continue
            if maxpage:
                if curpageno > maxpage:
                    continue
                # If we get this far, we should decode the page
            interpreter.process_page(page)
            if curpageno != maxpage:
                retstr.write("PAGEBREAKER")

        fp.close()
        fullstr = retstr.getvalue()
        device.close()
        retstr.close()

        print("Processed pdf in {:.2f}s".format(time.time() - start))
        return fullstr.split("PAGEBREAKER")

# convert pdf file text to string and save as a text_pdf.txt file
    def save_convert_pdf_to_txt(self):
        content = self.convert_pdf_to_txt()
        txt_pdf = open('text_pdf.txt', 'wb')
        txt_pdf.write(content.encode('utf-8'))
        txt_pdf.close()

def main(file_name=None, start_page=None, end_page=None):
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    if not file_name:
        file_name = 'RLbook2018.pdf'

    directory = file_name.rstrip(".pdf")
    if not os.path.exists(directory):
        os.makedirs(directory)

    pdfConverter = PdfConverter(file_name)
    if start_page and end_page:
        pages = pdfConverter.convert_pdf_to_txt(int(start_page), int(end_page))
    else:
        pages = pdfConverter.convert_pdf_to_txt()

    start = time.time()
    for p, page in enumerate(pages):

        ## DEBUG ##
        page_content = "".join(i for i in page[:-1] if i in '\n' + string.printable.replace('\x0b','').replace('\x0c',''))

        if len(page_content) > 5000:
            page_content = page_content[:5000]
        # Set the text input to be synthesized
        synthesis_input = texttospeech.types.SynthesisInput(text=page_content)

        voice = texttospeech.types.VoiceSelectionParams(
            language_code='en-US',
            # ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL,
            name="en-US-Wavenet-A")

        # Select the type of audio file you want returned
        audio_config = texttospeech.types.AudioConfig(
            audio_encoding=texttospeech.enums.AudioEncoding.MP3,
            speaking_rate=1)

        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        try:
            response = client.synthesize_speech(synthesis_input, voice, audio_config)
        except InvalidArgument as e:
            print(repr(page_content))
            print("Section is {} characters long".format(len(page_content)))
            raise(e)

        # The response's audio_content is binary.
        if start_page:
            new_file = directory + '/page' + str(int(start_page) + p) + '.mp3'
        else:
            new_file = directory + '/page' + str(p+1) + ".mp3"
        with open(new_file, 'wb') as out:
            # Write the response to the output file.
            out.write(response.audio_content)
            print('Audio content written to file "' + new_file + '"')

        new_file = new_file.rstrip(".mp3") + "_script.txt"
        with open(new_file, 'wb') as out:
            out.write(page_content.encode('utf-8'))
    
    print("Produced Audio in {:.2f}s".format(time.time() - start))

if __name__ == "__main__":
    main(*sys.argv[1:])