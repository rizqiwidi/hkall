def mod_hello():
    print("hello from plugin! use: hkall -m hello")
PLUGIN = {"hello": ("Hello plugin (sample)", mod_hello, True)}
