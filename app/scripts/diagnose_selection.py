import ctypes
import math
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_LBUTTON = 0x01
VK_CONTROL = 0x11
KEYEVENTF_KEYUP = 0x0002

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def get_clip():
    if not user32.OpenClipboard(None):
        return "<cannot open clipboard>"
    try:
        h = user32.GetClipboardData(13)
        if not h:
            return "<no unicode text>"
        kernel32.GlobalLock.restype = ctypes.c_wchar_p
        ptr = kernel32.GlobalLock(h)
        text = str(ptr) if ptr else "<empty>"
        kernel32.GlobalUnlock(h)
        return text
    finally:
        user32.CloseClipboard()

def send_copy():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(0x43, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(0x43, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

print("Starting 10-second mouse diagnostic...", flush=True)
print("Initial clipboard:", get_clip()[:40], flush=True)

start_time = time.time()
was_down = False
start_p = (0, 0)

while time.time() - start_time < 10:
    down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    if down and not was_down:
        start_p = get_pos()
        was_down = True
        print(f"Mouse DOWN at {start_p}", flush=True)
    elif not down and was_down:
        end_p = get_pos()
        was_down = False
        dist = math.hypot(end_p[0] - start_p[0], end_p[1] - start_p[1])
        print(f"Mouse UP at {end_p}, dist={dist:.1f}px", flush=True)
        time.sleep(0.08)
        send_copy()
        time.sleep(0.08)
        print("Captured clip after copy:", get_clip()[:60], flush=True)
    time.sleep(0.02)

print("Diagnostic complete.", flush=True)
