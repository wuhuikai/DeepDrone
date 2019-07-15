import threading

from .TelloAPI import Tello


class Subject(object):
    def __init__(self):
        self.observers = {}

    def register_observer(self, key, observer):
        if key not in self.observers:
            self.observers[key] = []
        self.observers[key].append(observer)

    def notify_observes(self, key, value):
        for obsever in self.observers[key]:
            threading.Thread(target=obsever.notify, args=(key, value)).start()


class Observer(object):
    def __init__(self):
        pass

    def notify(self, key, value):
        pass


class TelloFramework(Subject):
    def __init__(self, local_port=9999, command_timeout=0.35, state=True, video=True):
        self.tello = Tello(local_port, command_timeout, state, video)
        if video:
            self.video_thread = threading.Thread(target=self._send_video_frame)
            self.video_thread.daemon = True
            self.video_thread.start()

    def _send_video_frame(self):
        id = -1
        while True:
            id, frame = id + 1, self.tello.read_frame()
            self.notify_observes('frame', (id, frame))

    def state(self):
        return self.tello.state()
