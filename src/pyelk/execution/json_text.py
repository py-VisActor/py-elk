# SPDX-License-Identifier: Apache-2.0
# Copyright Google Inc. and others. Adapted JSON text behavior from GWT,
# elkjs0.12.1 worker275e6caf escapeValue/JSONArray/JSONObject/JSONString.
# Source closure: HOST-13/root/global-options-source-proposal-01.json GO05-11.
# Native JSON views only; no GWT runtime is included.
"""Text used by actual global JSON options, distinct from output JSON wire."""
from .diagnostics import number_text


def object_keys(value):
    """ECMAScript own string keys: array indices first, then insertion order."""
    indices=[];others=[]
    for key in value:
        if len(key)<=10 and key.isascii()and key.isdecimal()and str(int(key))==key and int(key)<2**32-1:
            indices.append(key)
        else:others.append(key)
    return sorted(indices,key=int)+others


def quote(value):
    escapes={8:r'\b',9:r'\t',10:r'\n',12:r'\f',13:r'\r',34:r'\"',92:r'\\'}
    result=[]
    for char in value:
        code=ord(char)
        if code in escapes:result.append(escapes[code])
        elif code<32:result.append('\\u'+format(code,'04X'))
        elif (code in(173,1757,1807,6068,6069,65279)
              or 1536<=code<=1539 or 8203<=code<=8207 or 8232<=code<=8238
              or 8288<=code<=8292 or 8298<=code<=8303 or 65529<=code<=65531):
            result.append('\\u'+format(code,'04x'))
        else:result.append(char)
    return '"'+''.join(result)+'"'


def json_value_text(value):
    output=[];active=set();frames=[('value',value)]
    while frames:
        frame=frames.pop()
        if frame[0]=='items':
            _,item,iterator,mapping,first=frame
            try:entry=next(iterator)
            except StopIteration:
                output.append('}'if mapping else']');active.remove(id(item));continue
            if not first:output.append(', 'if mapping else',')
            if mapping:
                key=entry;output.extend((quote(key),':'));child=item[key]
            else:key,child=entry
            frames.append(('items',item,iterator,mapping,False))
            frames.append(('value',child));continue
        item=frame[1]
        if item is None:output.append('null')
        elif type(item)is str:output.append(quote(item))
        elif type(item)is bool:output.append('true'if item else'false')
        elif type(item)in(int,float):
            try:output.append(number_text(item))
            except OverflowError:output.append('-Infinity'if item<0 else'Infinity')
        elif type(item)in(list,dict):
            if id(item)in active:raise ValueError('JSON cannot contain a cycle')
            active.add(id(item));mapping=type(item)is dict
            output.append('{'if mapping else'[')
            iterator=iter(object_keys(item))if mapping else enumerate(item)
            frames.append(('items',item,iterator,mapping,True))
        else:raise TypeError('Expected a native JSON value')
    return ''.join(output)
