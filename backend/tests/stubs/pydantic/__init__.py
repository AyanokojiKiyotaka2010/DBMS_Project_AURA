def Field(default=None, **k): return k.get("default_factory", lambda: default)() if "default_factory" in k else default
class BaseModel:
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)
EmailStr = str
