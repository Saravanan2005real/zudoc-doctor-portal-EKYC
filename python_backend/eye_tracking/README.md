# ZuDoc Eye Tracking (FGI-Net)

Custom eye-tracking module:

- Face can be **anywhere in the frame**
- Tracks pupils + plots **only when both eyes face the camera**
- Direction: **top / bottom / left / right / center**
- Live **(x, y)** graph for left & right eye

## Run

```powershell
cd "c:\Users\DINESH\Desktop\eKYC\eye tracking"
.\.venv\Scripts\activate
pip install -r requirements.txt
python demo.py
```

- Green overlay = both eyes facing → tracking + plotting  
- Red/wait message = turn to camera / show both eyes (graph pauses)  
- Esc to quit  

## API

```python
from fgi_eye_tracker import EyeTracker

tracker = EyeTracker()
r = tracker.estimate(frame_bgr)
if r.both_eyes_facing:
    print(r.direction, r.left_xy, r.right_xy)
```
