"""Trusted inert text/CSV parser. Separate process; no Django, credentials or macros.
Resource limits are not a general sandbox for PDF/Office or untrusted programs.
"""
import csv
import io
import json
import resource
import sys

MAX_BYTES=10_000_000
MAX_TEXT=2_000_000
MAX_FRAGMENTS=10_000

def parse(raw,kind):
    if len(raw)>MAX_BYTES:raise ValueError('input_limit')
    text=raw.decode('utf-8-sig')
    if any(ord(c)<32 and c not in '\n\r\t' for c in text):raise ValueError('binary_content')
    if not text.strip():raise ValueError('empty_document')
    if len(text)>MAX_TEXT:raise ValueError('text_limit')
    result=[]
    if kind=='txt':
        for number,line in enumerate(text.splitlines(),1):
            if line.strip():result.append({'ordinal':len(result)+1,'locator':f'Línea {number}','text':line,'cells':None})
            if len(result)>MAX_FRAGMENTS:raise ValueError('fragment_limit')
    elif kind=='csv':
        # Explicit comma separator, quoted multiline fields. Never evaluate formulas.
        csv.field_size_limit(200_000)
        reader=csv.reader(io.StringIO(text,newline=''),delimiter=',',strict=True)
        previous=0
        for number,cells in enumerate(reader,1):
            start=previous+1;previous=reader.line_num
            if len(cells)>200:raise ValueError('column_limit')
            if any(c.strip() for c in cells):
                result.append({'ordinal':len(result)+1,'locator':f'Fila {number}, líneas {start}–{previous}','text':' | '.join(cells),'cells':cells})
            if len(result)>MAX_FRAGMENTS:raise ValueError('fragment_limit')
    else:raise ValueError('unsupported_format')
    if not result:raise ValueError('empty_document')
    return result

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(4,4))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(16,16))
    try:
        source=open(sys.argv[2],'rb') if len(sys.argv)>2 else sys.stdin.buffer
        result={'fragments':parse(source.read(MAX_BYTES+1),sys.argv[1])}
    except UnicodeDecodeError:result={'error':'invalid_utf8'}
    except csv.Error:result={'error':'invalid_csv'}
    except ValueError as error:result={'error':str(error)}
    except MemoryError:result={'error':'memory_limit'}
    sys.stdout.write(json.dumps(result,ensure_ascii=True))
