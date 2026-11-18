"""Ephemeral, bounded workflow milestones; never identity data or a release authority."""
import time,threading
_entries={};_lock=threading.Lock()
def update(user_id,sid,job,percent,stage):
    if not job:return
    now=time.monotonic()
    with _lock:
        for key in list(_entries):
            if now-_entries[key][0]>600:del _entries[key]
        if len(_entries)>=512:_entries.pop(next(iter(_entries)))
        _entries[(user_id,sid,job)]=(now,{'percent':percent,'stage':stage})
def read(user_id,sid,job):
    with _lock:
        item=_entries.get((user_id,sid,job))
        return item[1] if item and time.monotonic()-item[0]<600 else {'percent':0,'stage':'Waiting for photo upload / progress unavailable'}
