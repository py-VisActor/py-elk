"""Full native ELK runtime shared by successive jobs in one worker.

Implementation-first migration: public wiring is implemented here; its complete
runtime/resource/algorithm validation is deferred to the unified acceptance.
"""
from collections.abc import Mapping

from .._errors import OptionValidationError
from .._json import clone_json
from .diagnostics import BasicProgressMonitor
from .json_transfer import JsonLayoutSession
from .metadata_service import NativeMetadataService
from .recursive import RecursiveLayoutEngine


class NativeRuntime:
    def __init__(self, constructor=None):
        self.constructor=clone_json({}if constructor is None else constructor,
                                    path='/constructor',error_type=OptionValidationError)
        self.metadata=NativeMetadataService(self.constructor.get('algorithms'))
        self.engine=RecursiveLayoutEngine(metadata=self.metadata)

    def layout(self, graph, arguments=None):
        arguments={}if arguments is None else arguments
        if not isinstance(arguments,Mapping):
            raise OptionValidationError('INVALID_OPTION_CONTAINER','/layoutArguments','Expected an argument mapping')
        selected=(arguments['layoutOptions']if'layoutOptions'in arguments
                  else self.constructor.get('defaultLayoutOptions',{}))
        if not isinstance(selected,Mapping):
            raise OptionValidationError('INVALID_OPTION_CONTAINER','/layoutArguments/layoutOptions',
                                        'Expected a layout-option mapping')
        logging=arguments.get('logging',False)
        timing=arguments.get('measureExecutionTime',False)
        for name,value in(('logging',logging),('measureExecutionTime',timing)):
            if type(value)is not bool:
                raise OptionValidationError('INVALID_OPTION_VALUE','/layoutArguments/'+name,'Expected a Boolean')
        state=JsonLayoutSession(graph,options=selected,metadata=self.metadata)
        monitor=BasicProgressMonitor(logging,timing)
        self.engine.layout(state,monitor=monitor)
        result=state.export()
        result.pop('logging',None)
        if logging or timing:result['logging']=monitor.collect()
        return result
