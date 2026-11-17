"""Text-only MES recipes bound directly to original resource/message hashes.

Recipes carry translated strings, not original message bytes or glyph images.
Command operands, headers, aliases and timing are recovered from the local game.
"""
import hashlib
from mes_codec import Bundle,Message
from mes_legacy import LegacyMessage
from mes_subtitles import TimedMessage
import mes_tokens

def sha(raw):return hashlib.sha256(raw).hexdigest()

def text_positions(message,table):
    for row,line in enumerate(message.lines):
        cursor=0
        while cursor<len(line)-1:
            word=line[cursor]
            if word<len(table.codes):yield row,cursor;cursor+=1
            else:
                if word not in mes_tokens.OPERANDS:raise ValueError('Unknown command while locating glyphs')
                cursor+=1+mes_tokens.OPERANDS[word]

def glyph_choices(message,table):
    first={}
    for index,code in enumerate(table.codes):first.setdefault(code,index)
    return [dict(line=row,position=col,glyph=message.lines[row][col]) for row,col in text_positions(message,table)
            if first[table.codes[message.lines[row][col]]]!=message.lines[row][col]]

def apply_glyph_choices(message,choices,table):
    allowed=set(text_positions(message,table));lines=[list(line) for line in message.lines];seen=set()
    for item in choices:
        pos=item['line'],item['position'];glyph=item['glyph']
        if pos not in allowed or pos in seen or type(glyph) is not int or not 0<=glyph<len(table.codes):raise ValueError('Invalid duplicate-glyph choice')
        seen.add(pos);row,col=pos
        if table.codes[lines[row][col]]!=table.codes[glyph]:raise ValueError('Glyph choice changes translated character')
        lines[row][col]=glyph
    if isinstance(message,LegacyMessage):return LegacyMessage(message.header,tuple(tuple(line) for line in lines),message.padding,table)
    return Message(message.header,tuple(tuple(line) for line in lines),message.padding)

def reflow(source,lines,table):
    if source.header!=(0xffff,len(source.lines)-1,0,0) or not 1<=len(lines)<=65535:raise ValueError('Unmeasured reflow header')
    _,commands=mes_tokens.message_template(source,table)
    tags=[int(match[1]) for text in lines for match in mes_tokens.TAG.finditer(text)]
    if tags!=list(range(len(commands))):raise ValueError('Reflow changes command stream')
    rebuilt=[]
    for index,text in enumerate(lines):
        if '\n' in text or '\r' in text or '<cmd:' in mes_tokens.TAG.sub('',text):raise ValueError('Invalid translated line')
        words=[];cursor=0
        for match in mes_tokens.TAG.finditer(text):
            words.extend(table.encode(text[cursor:match.start()]));words.extend(commands[int(match[1])]);cursor=match.end()
        words.extend(table.encode(text[cursor:]));words.append(0xffff if index==len(lines)-1 else 0xfffe);rebuilt.append(tuple(words))
    target=Message((0xffff,len(lines)-1,0,0),tuple(rebuilt),source.padding)
    if mes_tokens.message_template(target,table)[1]!=commands:raise ValueError('Reflow changes command operands')
    return target

def formatting_commands(source,description,table):
    _,original=mes_tokens.message_template(source,table)
    significant=[i for i,c in enumerate(original) if c[0] not in (0xfffa,0xfff9)]
    used=[];commands=[]
    for entry in description:
        if set(entry)=={'colour'}:
            rgb=entry['colour']
            if len(rgb)!=3 or any(type(v) is not int or not 0<=v<=255 for v in rgb):raise ValueError('Invalid text colour')
            commands.append((0xfffa,*rgb))
        elif entry=={'reset_colour':True}:commands.append((0xfff9,))
        elif set(entry)=={'original_command'}:
            index=entry['original_command']
            if type(index) is not int or index not in significant:raise ValueError('Invalid original text command')
            used.append(index);commands.append(original[index])
        else:raise ValueError('Unknown formatting command')
    if used!=significant:raise ValueError('Non-colour text commands changed')
    return commands

def formatted(source,record,table,resource_id):
    lines=record['lines'];header=source.header
    if header[0] not in (0xff,0xffff) or header[1]!=len(source.lines)-1 or header[2:]!=(0,0):raise ValueError('Unmeasured formatted message header')
    if record.get('normalize_header'):
        if resource_id!=0x410bc or header[0]!=0xff:raise ValueError('Unmeasured text header normalization')
        header=(0xffff,*header[1:])
    commands=formatting_commands(source,record['formatting'],table)
    tags=[int(m[1]) for text in lines for m in mes_tokens.TAG.finditer(text)]
    if not 1<=len(lines)<=65535 or tags!=list(range(len(commands))):raise ValueError('Formatting marker order changed')
    rebuilt=[]
    for index,text in enumerate(lines):
        if '\n' in text or '\r' in text or '<cmd:' in mes_tokens.TAG.sub('',text):raise ValueError('Invalid formatted line')
        words=[];cursor=0
        for match in mes_tokens.TAG.finditer(text):
            words.extend(table.encode(text[cursor:match.start()]));words.extend(commands[int(match[1])]);cursor=match.end()
        words.extend(table.encode(text[cursor:]));words.append(0xffff if index==len(lines)-1 else 0xfffe);rebuilt.append(tuple(words))
    return Message((header[0],len(lines)-1,*header[2:]),tuple(rebuilt),source.padding)

def reconstruct_message(raw,record,table,resource_id):
    if sha(raw)!=record['source_sha256']:raise ValueError('Original message hash differs')
    kind=record['kind'];lines=record.get('lines')
    if kind=='normal':
        source=Message.parse(raw)
        target=mes_tokens.replace_message(source,lines,table)
    elif kind=='reflow':target=reflow(Message.parse(raw),lines,table)
    elif kind=='formatted':target=formatted(Message.parse(raw),record,table,resource_id)
    elif kind=='item-layout':
        if resource_id not in (0x410e8,0x40d77):raise ValueError('Unmeasured item layout resource')
        from item_description_layout import replace
        target=replace(Message.parse(raw),lines,table,preserve_words=False)
    elif kind=='legacy':
        if resource_id!=0x40008:raise ValueError('Unmeasured legacy resource')
        source=LegacyMessage.parse(raw,table)
        if len(lines)!=len(source.lines):raise ValueError('Legacy line count changed')
        target=source
        for index,text in enumerate(lines):target=target.replace_line(index,text,table)
    elif kind=='timed':
        source=TimedMessage.parse(raw);target=source
        if len(record['cues'])!=len(source.cues):raise ValueError('Timed cue count changed')
        for index,cue_lines in enumerate(record['cues']):target=target.replace_cue(index,cue_lines,table)
    else:raise ValueError('Unknown message recipe kind')
    if kind!='timed':target=apply_glyph_choices(target,record.get('glyph_choices',[]),table)
    padding=record.get('padding_words',len(target.padding))
    if type(padding) is not int or not 0<=padding<=max(len(target.padding),8):raise ValueError('Invalid zero padding')
    if isinstance(target,LegacyMessage):target=LegacyMessage(target.header,target.lines,(0,)*padding,table)
    elif isinstance(target,TimedMessage):target=TimedMessage(target.header,target.cues,(0,)*padding)
    else:target=Message(target.header,target.lines,(0,)*padding)
    rebuilt=target.build()
    if sha(rebuilt)!=record['target_sha256']:raise ValueError('Text-only message recipe does not reproduce target')
    return target

def export_message(before,after,table,resource_id):
    record=dict(source_sha256=sha(before),target_sha256=sha(after))
    errors=[]
    for kind in ('normal','item-layout','reflow','formatted','legacy','timed'):
        try:
            entry=dict(record,kind=kind)
            if kind in ('normal','item-layout','reflow','formatted'):
                target=Message.parse(after);entry['lines']=mes_tokens.message_template(target,table)[0];entry['glyph_choices']=glyph_choices(target,table)
                if kind=='formatted':
                    source=Message.parse(before);original=mes_tokens.message_template(source,table)[1]
                    significant=[i for i,c in enumerate(original) if c[0] not in (0xfffa,0xfff9)];cursor=0;description=[]
                    for command in mes_tokens.message_template(target,table)[1]:
                        if command[0]==0xfffa:description.append(dict(colour=list(command[1:])))
                        elif command[0]==0xfff9:description.append(dict(reset_colour=True))
                        else:
                            if cursor>=len(significant) or original[significant[cursor]]!=command:raise ValueError('Non-colour text command changed')
                            description.append(dict(original_command=significant[cursor]));cursor+=1
                    entry.update(formatting=description,normalize_header=target.header[0]!=source.header[0])
            elif kind=='legacy':
                target=LegacyMessage.parse(after,table);entry['lines']=[table.decode(line[:-1]) for line in target.lines];entry['glyph_choices']=glyph_choices(target,table)
            else:
                target=TimedMessage.parse(after);entry['cues']=[mes_tokens.message_template(cue.message(),table)[0] for cue in target.cues]
            entry['padding_words']=len(target.padding)
            reconstruct_message(before,entry,table,resource_id)
            return entry
        except (ValueError,UnicodeError) as error:errors.append(kind+': '+str(error))
    raise ValueError('; '.join(errors))

def reconstruct_bundle(source,recipe,table):
    if sha(source)!=recipe['source_sha256']:raise ValueError('Original bundle hash differs')
    bundle=Bundle.parse(source);replacements={}
    for entry in recipe['entries']:
        block=entry['block_index']
        if type(block) is not int or not 0<=block<len(bundle.blocks) or block in replacements:raise ValueError('Invalid or duplicate message block')
        replacements[block]=reconstruct_message(bundle.blocks[block],entry,table,int(recipe['resource_id'],16))
    rebuilt=bundle.build(replacements)
    if sha(rebuilt)!=recipe['target_sha256']:raise ValueError('Bundle recipe does not reproduce target')
    return rebuilt

def export_bundle(source,target,table,resource_id):
    before,after=Bundle.parse(source),Bundle.parse(target)
    if (before.version,before.offsets,before.prefix_gap)!=(after.version,after.offsets,after.prefix_gap) or len(before.blocks)!=len(after.blocks):raise ValueError('Message directory or aliases changed')
    entries=[]
    for index,(a,b) in enumerate(zip(before.blocks,after.blocks)):
        if a!=b:entries.append(dict(block_index=index,**export_message(a,b,table,resource_id)))
    recipe=dict(resource_id=f'{resource_id:08x}',source_sha256=sha(source),target_sha256=sha(target),entries=entries)
    reconstruct_bundle(source,recipe,table)
    return recipe
