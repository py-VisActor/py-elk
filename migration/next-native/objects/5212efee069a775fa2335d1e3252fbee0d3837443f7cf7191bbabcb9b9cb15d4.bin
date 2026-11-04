"""Native enum value-key map over the fixed source bucket/entry protocol.

Only operations used by current algorithm callers are provided. Keys are
retained by reference; mutable set keys are never frozen, copied or rehashed
after insertion. Source EC10-18 / HOST14 B collections source review.
"""
from .enum_identity import enum_identity_hash,enum_set_identity_hash


class EnumKeyMap:
    def __init__(self,domain,order,*,set_keys=False,hash_function=None):
        self.domain=domain;self.order=order;self.set_keys=set_keys
        self.hash_function=hash_function;self.buckets={}
    def _code(self,key):
        if key is None:return 0
        if self.hash_function is not None:return self.hash_function(key)
        return (enum_set_identity_hash(self.domain,key,self.order)if self.set_keys
                else enum_identity_hash(self.domain,key))
    def get(self,key,default=None):
        for stored,value in self.buckets.get(self._code(key),()):
            if key==stored:return value
        return default
    def put(self,key,value):
        code=self._code(key);bucket=self.buckets.setdefault(code,[])
        for entry in bucket:
            if key==entry[0]:
                old=entry[1];entry[1]=value;return old
        bucket.append([key,value]);return None
    def remove(self,key):
        code=self._code(key);bucket=self.buckets.get(code,())
        for i,entry in enumerate(bucket):
            if key==entry[0]:
                old=entry[1];del bucket[i]
                if not bucket:del self.buckets[code]
                return old
        return None
    def items(self):return [(key,value)for bucket in self.buckets.values()for key,value in bucket]
    def keys(self):return [key for key,value in self.items()]
    def values(self):return [value for key,value in self.items()]
    def clear(self):self.buckets.clear()


class EnumSetKeyMap(EnumKeyMap):
    def __init__(self,domain,order,*,hash_function=None):
        super().__init__(domain,order,set_keys=True,hash_function=hash_function)
