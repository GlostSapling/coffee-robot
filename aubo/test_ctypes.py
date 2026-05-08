import ctypes
import os

# Load the dll
dll_path = r"d:\aubo\serviceinterface-2.5.0-win64.bf52073\lib\serviceinterface2.dll"
# Need to add lib to PATH so dependencies like libgcc_s_seh-1.dll can be found
os.environ["PATH"] += os.pathsep + os.path.dirname(dll_path)

dll = ctypes.CDLL(dll_path)

rs_initialize = dll.rs_initialize
rs_initialize.restype = ctypes.c_int

rs_create_context = dll.rs_create_context
rs_create_context.argtypes = [ctypes.POINTER(ctypes.c_uint16)]
rs_create_context.restype = ctypes.c_int

print("rs_initialize:", rs_initialize())
rshd = ctypes.c_uint16(0)
print("rs_create_context:", rs_create_context(ctypes.byref(rshd)))
print("rshd:", rshd.value)
