"""Observation normalization scoped to actual owned input object paths."""
def without_generated_hashes(value,owned_inputs,path=''):
    if type(value)is list:
        return [without_generated_hashes(child,owned_inputs,path+'/'+str(i))for i,child in enumerate(value)]
    if type(value)is not dict:return value
    result={}
    for key,child in value.items():
        if key=='$H'and path in owned_inputs and '$H'not in owned_inputs[path]:
            if type(child)is not int:raise ValueError('Generated owned GWT hash must be an integer')
            continue
        where=path+'/'+key.replace('~','~0').replace('/','~1')
        result[key]=without_generated_hashes(child,owned_inputs,where)
    return result
