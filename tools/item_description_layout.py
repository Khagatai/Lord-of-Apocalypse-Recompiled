"""Measured item-panel MES layout; keep the game's font and command operands.

The shared 000410e8 description table uses FFFF / (line count - 1) headers.
The narrow item panel admits 150 source pixels and five 12-pixel text rows.
Budget 144 advances, reserving six pixels for the final glyph's overhang.
ASCII advances are conservatively budgeted at six pixels; full-width glyphs
and rating stars use twelve. Unknown commands are rejected, never zero-sized.
"""
import re
import unicodedata
from mes_codec import Message
from mes_tokens import TAG,message_template

WIDTH=144
LINES=5
def width(text):
    if '<cmd:' in TAG.sub('',text):raise ValueError('Malformed command marker')
    return sum(6 if 32<=ord(c)<127 else 12 for c in TAG.sub('',text))

def wrap(lines):
    """Reflow whole words, retaining all visible text and the command stream."""
    text=' '.join(lines)
    # Invisible colour commands must not create extra visual word spaces.
    # Keep one existing separator between visible words and every command byte.
    text=re.sub(r'(<cmd:\d+>)\s+(?=<cmd:)',r'\1',text)
    text=re.sub(r'(?<=\s)((?:<cmd:\d+>)+)\s+',r'\1',text)
    text=re.sub(r'^((?:<cmd:\d+>)+)\s+',r'\1',text)
    words=text.split();output=[];line=''
    for word in words:
        if width(word)>WIDTH:raise ValueError('Unbreakable item word exceeds panel width: '+ascii(word))
        candidate=(line+' '+word).lstrip()
        if width(candidate)>WIDTH:
            output.append(line);line=word
        else:line=candidate
    if line:output.append(line)
    return output or ['']

def replace(message,lines,table,*,preserve_words=True):
    original,commands=message_template(message,table)
    if message.header!=(0xffff,len(message.lines)-1,0,0):raise ValueError('Unmeasured item message header')
    if any(c[0] not in (0xfffa,0xfff9) for c in commands):raise ValueError('Item panel has an unmeasured command width')
    if not 1<=len(lines)<=LINES or any('\n' in s or '\r' in s or width(s)>WIDTH for s in lines):raise ValueError('Item text exceeds measured panel')
    if [m.group(0) for s in lines for m in TAG.finditer(s)]!=[f'<cmd:{i}>' for i in range(len(commands))]:raise ValueError('Item command order changed')
    before=' '.join(TAG.sub('',s) for s in original);after=' '.join(TAG.sub('',s) for s in lines)
    if re.findall('[\u2605\u2606]',before)!=re.findall('[\u2605\u2606]',after):raise ValueError('Item upgrade rating changed')
    # A full-width Japanese digit and its ASCII English form carry the same
    # value. Compare normalized digits, still rejecting lost/reordered values.
    if re.findall(r'\d+',unicodedata.normalize('NFKC',before))!=re.findall(r'\d+',unicodedata.normalize('NFKC',after)):raise ValueError('Item numeric quantities changed')
    if preserve_words and ' '.join(TAG.sub('',s) for s in original).split()!=' '.join(TAG.sub('',s) for s in lines).split():raise ValueError('Item reflow dropped or changed visible words')
    result=[]
    for i,text in enumerate(lines):
        words=[];cursor=0
        for match in TAG.finditer(text):
            words.extend(table.encode(text[cursor:match.start()]));words.extend(commands[int(match[1])]);cursor=match.end()
        words.extend(table.encode(text[cursor:]));words.append(0xffff if i==len(lines)-1 else 0xfffe);result.append(tuple(words))
    target=Message((0xffff,len(lines)-1,0,0),tuple(result),message.padding)
    if message_template(target,table)[1]!=commands:raise ValueError('Item command operands changed')
    if Message.parse(target.build())!=target:raise ValueError('Item layout failed round trip')
    return target
