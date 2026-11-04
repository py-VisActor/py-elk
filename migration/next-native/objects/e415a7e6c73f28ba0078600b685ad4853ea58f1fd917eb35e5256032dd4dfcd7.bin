# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Source: elkjs0.12.1 worker275e6caf,
# JsonImporter.setOption/LayoutOptionData.parseValue. See HOST-11/B
# local-property-import-source-proposal-01.json and Root source review02.
"""Source-local JSON property import; strict API/global parsing is separate.

Current ids and legacy dot suffixes follow the selected metadata service.
Source-erased opaque constructors preserve their actual unavailable-factory error.
No property defaults or target filters are applied by this importer.
"""
import math
import re

from .._errors import OptionValidationError, UnsupportedOptionError
from .diagnostics import number_text
from ..options.generic import RUNTIME_PROPERTY_SPECS
from ..options.element import java_split, _JAVA_TRIM, _JS_WHITESPACE, _ENUMSET_DELIMITERS
from ..options.schema import Padding, Vector2, VectorChainValue

_SKIP = object()
_INTEGER = re.compile(r'[+-]?[0-9]+\Z')
_DOUBLE = re.compile('['+re.escape(_JS_WHITESPACE)+r']*[+-]?(?:NaN|Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?[dDfF]?)['+re.escape(_JS_WHITESPACE)+r']*\Z')


_DEFAULT_METADATA=None


def lookup_option(suffix,metadata=None):
    global _DEFAULT_METADATA
    if metadata is None:
        if _DEFAULT_METADATA is None:
            from .metadata_service import NativeMetadataService
            _DEFAULT_METADATA=NativeMetadataService()
        metadata=_DEFAULT_METADATA
    return metadata.lookup_option(suffix)


def _integer(text):
    if not _INTEGER.fullmatch(text):raise ValueError('Invalid signed32 integer')
    value=int(text)
    if not -(2**31)<=value<2**31:raise ValueError('Invalid signed32 integer')
    return value


def _double(text):
    if not _DOUBLE.fullmatch(text):raise ValueError('Invalid source Double')
    text=text.strip(_JS_WHITESPACE)
    if text.endswith(('d','D','f','F')):text=text[:-1]
    return float(text)


def _enum(spec,text):
    if text in spec.accepted_values:return text
    ordinal=_integer(text)
    if not 0<=ordinal<len(spec.accepted_values):raise ValueError('Invalid enum ordinal')
    return spec.accepted_values[ordinal]


def _string_value(value,path):
    if type(value) is str:return value
    if type(value) is bool:return 'true' if value else 'false'
    if type(value) in (int,float):
        try:value=float(value)
        except OverflowError:value=math.inf if value>0 else -math.inf
        return number_text(value)
    # Source JSONNull/JSONObject/JSONArray do not implement stringVal.
    raise OptionValidationError('LOCAL_PROPERTY_SCALAR_REQUIRED',path,
                                'Severe implementation error in the Json to ElkGraph importer.')


def _parse_text(spec,text,path,metadata=None):
    if text is None or text=='null' or (not text and spec.kind!='enumset'):
        return _SKIP
    kind=spec.kind
    if kind=='opaque':
        # Fixed createDataInstance69652-69661: these eight declared classes
        # have no ElkReflect constructor in the compiled source itself.
        raise RuntimeError("java.lang.IllegalStateException: Couldn't create new instance of property '"+
                           spec.id+"'. Make sure its type is registered with the ElkReflect utility class.")
    try:
        if kind=='string':return text
        if kind=='boolean':
            if text.lower() not in ('true','false'):return _SKIP
            return text.lower()=='true'
        if kind=='integer':return _integer(text)
        if kind=='signed_number':return _double(text)
        if kind=='enum_ordinal':return _enum(spec,text)
        if kind=='enumset':
            return frozenset(_enum(spec,t)for t in java_split(text,_ENUMSET_DELIMITERS)
                             if t.strip(_JAVA_TRIM))
        if kind in ('insets','vector'):
            content=text.lstrip('([{\"\' \t\r\n').rstrip(')]}\"\' \t\r\n')
            if kind=='vector':
                tokens=java_split(content,'[,;\r\n]')
                if len(tokens)!=2:raise ValueError('Invalid vector')
                return Vector2(*(_double(t.strip(_JAVA_TRIM))for t in tokens))
            values=dict.fromkeys(('top','right','bottom','left'),0)
            if content:
                for token in java_split(content,',|;'):
                    pair=java_split(token,'=')
                    if len(pair)!=2:raise ValueError('Invalid Insets')
                    key=pair[0].strip(_JAVA_TRIM);value=_double(pair[1].strip(_JAVA_TRIM))
                    if key in values:values[key]=value
            return Padding(**values)
        if kind=='vector_chain':
            numbers=[_double(t)for t in java_split(text,r'[,;()\[\]{} \t\n]')if t.strip(_JAVA_TRIM)]
            return VectorChainValue(tuple(Vector2(x,y)for x,y in zip(numbers[::2],numbers[1::2])))
        if kind=='individual_spacings':
            result={}
            for token in java_split(text,';,;'):
                pair=java_split(token,':')
                canonical=lookup_option(pair[0],metadata)
                if canonical is None:raise ValueError('Invalid individual option')
                value=_parse_text(RUNTIME_PROPERTY_SPECS[canonical],pair[1] if len(pair)>1 else None,path,metadata)
                if value is _SKIP:raise ValueError('Invalid individual value')
                result[canonical]=value
            return result
    except ValueError:
        # LayoutOptionData catches NumberFormatException/IllegalArgumentException.
        return _SKIP
    raise UnsupportedOptionError('UNMIGRATED_LOCAL_PROPERTY_TYPE',path,kind)


def parse_local_mapping(raw,path='/layoutOptions',*,metadata=None):
    """Import an actual JSONObject, retaining only successful assignments."""
    if type(raw) is not dict:return {}
    result={}
    for spelling,value in raw.items():
        where=path+'/'+str(spelling)
        text=_string_value(value,where)  # Conversion happens even for unknown ids.
        canonical=lookup_option(spelling,metadata)
        if canonical is None:continue
        parsed=_parse_text(RUNTIME_PROPERTY_SPECS[canonical],text,where,metadata)
        if parsed is not _SKIP:result[canonical]=parsed
    return result


def local_options_object(element):
    value=element.get('layoutOptions')
    if type(value)is dict:return value,'layoutOptions'
    value=element.get('properties')
    return (value,'properties')if type(value)is dict else ({},'layoutOptions')
