#!/usr/bin/env python3
"""chan_queue - Go-style channels with select, buffered/unbuffered modes."""
import sys, json, threading, time

class Chan:
    def __init__(self, capacity=1):
        self._buf = []
        self._cap = max(capacity, 1)
        self._lock = threading.Lock()
        self._not_full = threading.Condition(self._lock)
        self._not_empty = threading.Condition(self._lock)
        self._closed = False
        self.stats = {"sends": 0, "recvs": 0}

    def send(self, val, timeout=5):
        with self._lock:
            if self._closed: raise RuntimeError("send on closed channel")
            while len(self._buf) >= self._cap:
                if not self._not_full.wait(timeout=timeout): return False
            self._buf.append(val)
            self.stats["sends"] += 1
            self._not_empty.notify()
            return True

    def recv(self, timeout=5):
        with self._lock:
            while not self._buf:
                if self._closed: return None
                if not self._not_empty.wait(timeout=timeout): return None
            val = self._buf.pop(0)
            self.stats["recvs"] += 1
            self._not_full.notify()
            return val

    def close(self):
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()

    def __iter__(self):
        while True:
            v = self.recv()
            if v is None: break
            yield v

def select(*cases, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for ch, op in cases:
            if op == "recv":
                with ch._lock:
                    if ch._buf:
                        val = ch._buf.pop(0)
                        ch.stats["recvs"] += 1
                        ch._not_full.notify()
                        return val
                    if ch._closed: return None
        time.sleep(0.001)
    return None

def main():
    print("Go-style channels demo\n")
    ch = Chan(capacity=3)
    results = []
    def producer():
        for i in range(6):
            ch.send(i); time.sleep(0.01)
        ch.close()
    def consumer():
        for v in ch:
            results.append(v)
    t1 = threading.Thread(target=producer)
    t2 = threading.Thread(target=consumer)
    t1.start(); t2.start(); t1.join(); t2.join()
    print(f"Received: {results}")
    print(f"Stats: {json.dumps(ch.stats, indent=2)}")
    ch1, ch2 = Chan(2), Chan(2)
    ch1.send(10); ch2.send(20)
    v = select((ch1, "recv"), (ch2, "recv"))
    print(f"Select got: {v}")

if __name__ == "__main__":
    main()
