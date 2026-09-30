"""Bounded parsing of image headers and OCR TSV; native decoders run in the sandbox."""
import csv
import io
import struct

def image_size(data,kind):
    if kind=='png':
        if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR':raise ValueError('invalid_image')
        w,h=struct.unpack('>II',data[16:24])
    else:
        if not data.startswith(b'\xff\xd8'):raise ValueError('invalid_image')
        i=2;w=h=0
        while i<len(data):
            if data[i]!=255:raise ValueError('invalid_image')
            while i<len(data) and data[i]==255:i+=1
            if i+3>len(data):raise ValueError('invalid_image')
            marker=data[i];i+=1
            if marker in {0xD9,0xDA}:break
            length=struct.unpack('>H',data[i:i+2])[0]
            if length<2 or i+length>len(data):raise ValueError('invalid_image')
            if marker in {0xC0,0xC1,0xC2}:
                if length<7:raise ValueError('invalid_image')
                h,w=struct.unpack('>HH',data[i+3:i+7]);break
            i+=length
    if not 1<=w<=10000 or not 1<=h<=10000 or w*h>16_000_000:raise ValueError('image_limit')

def parse_tsv(output,number):
    if len(output)>8_000_000:raise ValueError("text_limit")
    groups={};conf=[]
    for row in csv.DictReader(io.StringIO(output.decode('utf-8')),delimiter='\t'):
        if row.get('level')!='5' or not row.get('text','').strip():continue
        key=(row['block_num'],row['par_num'],row['line_num'])
        groups.setdefault(key,[]).append(row['text']);conf.append(float(row['conf']))
    text='\n'.join(' '.join(words) for words in groups.values())
    if not text.strip():raise ValueError('ocr_no_text')
    return {'ordinal':number,'locator':f'Página {number} · OCR','text':text,'cells':None,'method':'ocr','confidence':round(sum(conf)/len(conf),2)}
