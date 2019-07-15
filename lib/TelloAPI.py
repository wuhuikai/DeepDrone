import cv2
import time
import socket
import threading


class Response(object):
    def __init__(self):
        pass

    def recv(self, data):
        pass

    def pop(self):
        pass

    def empty(self):
        pass


class Command(Response):
    def __init__(self):
        super(Command, self).__init__()
        self.response = None
        self.lock = threading.RLock()

    def recv(self, data):
        with self.lock:
            self.response = data.decode('utf-8')

    def pop(self):
        with self.lock:
            response, self.response = self.response, None
        return response

    def empty(self):
        with self.lock:
            return self.response is None


class State(Response):
    def __init__(self):
        super(State, self).__init__()
        self.response = {}
        self.lock = threading.RLock()

    def recv(self, data):
        with self.lock:
            self.response = {item.split(':')[0]:float(item.split(':')[1]) for item in data.decode('utf-8').split(';') if ':' in item}

    def pop(self):
        return self.response

    def empty(self):
        return False


class Client(object):
    def __init__(self, local_port, buffer_size, daemon, response):
        self.response = response
        self.buffer_size = buffer_size

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', local_port))

        self.receive_thread = threading.Thread(target=self._receive_thread)
        self.receive_thread.daemon = daemon
        self.receive_thread.start()

    def __del__(self):
        """Closes the local socket."""
        self.socket.close()

    def _receive_thread(self):
        """Listens for responses from the Tello.

        Runs as a thread, sets self.response to whatever the Tello last returned.
        """
        while True:
            try:
                self.response.recv(self.socket.recv(self.buffer_size))
            except Exception as e:
                print(e)
                break

    def empty(self):
        return self.response.empty()

    def pop(self):
        return self.response.pop()


class Video(object):
    def __init__(self, daemon=True):
        self.video = cv2.VideoCapture('udp://@0.0.0.0:11111')
        if not self.video.isOpened():
            raise RuntimeError('Failed to connect to Tello')
        self.frame = None
        self.lock = threading.RLock()
        self.thread = threading.Thread(target=self._update_thread)
        self.thread.daemon = daemon
        self.thread.start()

    def __del__(self):
        self.video.release()

    def _update_thread(self):
        while True:
            ok, frame = self.video.read()
            if ok:
                with self.lock:
                    self.frame = frame

    def empty(self):
        with self.lock:
            return self.frame is None

    def pop(self):
        with self.lock:
            frame, self.frame = self.frame, None
        return frame


class Tello(object):
    def __init__(self, local_port=9999, command_timeout=0.35, state=True, video=True):
        """Connects to Tello in command mode.

        Args:
            local_port (int): port of local machine for receiving command response.
            command_timeout (float): seconds to wait for a response of command.
            state (bool): receive state from Tello?
            video (bool): receive video from Tello?

        Raises:
            RuntimeError: If the Tello rejects the attempt to enter command mode or open the video stream.
        """
        self.command_timeout = command_timeout

        self.response_client = Client(local_port, 1024, True, Command())
        self.state_client = Client(8890, 1024, True, State()) if state else None

        self.tello_address = ('192.168.10.1', 8889)
        self.enter_command_mode()
        self.video_client = None
        if video:
            self.open_video_stream()
            self.video_client = Video(True)

    def send_command(self, command, with_return=True):
        """Sends a command to the Tello and waits for a response.

        If self.command_timeout is exceeded before a response is received,
        a RuntimeError exception is raised.

        Args:
            command (str): Command to send.

        Returns:
            str: Response from Tello.

        Raises:
            RuntimeError: If no response is received within self.timeout seconds.
        """
        self.response_client.socket.sendto(command.encode('utf-8'), self.tello_address)

        if not with_return:
            return

        st = time.time()
        while self.response_client.empty():
            if time.time() - st >= self.command_timeout:
                raise RuntimeError('No response to command')
        return self.response_client.pop()

    def state(self):
        return self.state_client.pop() if self.state_client else None

    def read_frame(self):
        if self.video_client is None:
            raise RuntimeError('Video is not available')
        while self.video_client.empty():
            pass
        return self.video_client.pop()

    def enter_command_mode(self):
        if self.send_command('command') != 'ok':
            raise RuntimeError('Tello rejected the attempt to enter command mode')

    def take_off(self):
        """
        return: 'ok' or 'error'
        """
        return self.send_command('takeoff')

    def land(self):
        """
        return: 'ok' or 'error'
        """
        return self.send_command('land')

    def open_video_stream(self):
        if self.send_command('streamon') != 'ok':
            raise RuntimeError('Tello rejected to open the video stream')

    def close_video_stream(self):
        """
        return: 'ok' or 'error'
        """
        return self.send_command('streamoff')

    def emergency_shutdown(self):
        """
        return: 'ok' or 'error'
        """
        return self.send_command('emergency')

    def move_up(self, x, with_return=False):
        """
        param x: int, [20, 500]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('up {}'.format(x), with_return)

    def move_down(self, x, with_return=False):
        """
        param x: int, [20, 500]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('down {}'.format(x), with_return)

    def move_left(self, x, with_return=False):
        """
        param x: int, [20, 500]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('left {}'.format(x), with_return)

    def move_right(self, x, with_return=False):
        """
        param x: int, [20, 500]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('right {}'.format(x), with_return)

    def move_forward(self, x, with_return=False):
        """
        param x: int, [20, 500]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('forward {}'.format(x), with_return)

    def move_backward(self, x, with_return=False):
        """
        param x: int, [20, 500]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('back {}'.format(x), with_return)

    def rotate_clockwise(self, x, with_return=False):
        """
        param x: int, [1, 3600]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('cw {}'.format(x), with_return)

    def rotate_counter_clockwise(self, x, with_return=False):
        """
        param x: int, [1, 3600]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('ccw {}'.format(x), with_return)

    def flip_left(self, with_return=False):
        """
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('flip l', with_return)

    def flip_right(self, with_return=False):
        """
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('flip r', with_return)

    def flip_forward(self, with_return=False):
        """
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('flip f', with_return)

    def flip_backward(self, with_return=False):
        """
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('flip b', with_return)

    def goto(self, x, y, z, speed, with_return=False):
        """
        param x: int, [20, 500]
        param y: int, [20, 500]
        param z: int, [20, 500]
        param speed: int, [10-100]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('go {} {} {} {}'.format(x, y, z, speed), with_return)

    def goto_curve(self, x1, y1, z1, x2, y2, z2, speed, with_return=False):
        """fly a curve defined by (0, 0, 0), (x1, y1, z1), (x2, y2, z2) with speed
        param x1, x2: int, [-500, 500]
        param y1, y2: int, [-500, 500]
        param z1, z2: int, [-500, 500]
        param speed: int, [10-60]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('curve {} {} {} {} {} {} {}'.format(x1, y1, z1, x2, y2, z2, speed), with_return)

    def set_speed(self, speed, with_return=False):
        """
        param speed: int, [10-100]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('speed {}'.format(speed), with_return)

    def set_remote_controller_command(self, left_right_velocity, forward_backward_velocity, up_down_velocity, rotate_velocity, with_return=False):
        """
        param left_right_velocity: int, [-100, 100]
        param forward_backward_velocity: int, [-100, 100]
        param up_down_velocity: int, [-100, 100]
        param rotate_velocity: int, [-100, 100]
        param with_return: bool
        return: 'ok' or 'error'
        """
        return self.send_command('rc {} {} {} {}'.format(left_right_velocity, forward_backward_velocity, up_down_velocity, rotate_velocity), with_return)

    def get(self, command, split=False):
        """
        param command
        param split: bool, multiple values?
        return: int or list(int)
        """
        result = self.send_command(command)
        if split:
            return [int(x) for x in result.split(' ')]
        else:
            return int(result)

    def get_speed(self):
        """
        return: int, [10, 100]
        """
        return self.get('speed?')

    def get_battery(self):
        """
        return: int, [0, 100]
        """
        return self.get('battery?')

    def get_flight_time(self):
        """
        return: int
        """
        return self.get('time?')

    def get_relative_height(self):
        """
        return: int, [10, 3000]
        """
        return self.get('height?')

    def get_temperature(self):
        """
        return: int, [0, 90]
        """
        return self.get('temp?')

    def get_imu_pose(self):
        """[pitch, roll, yaw]
        return: list(int), [[-89, 89], [-179, 179], [-179, 179]]
        """
        return self.get('attitude?', split=True)

    def get_absolute_height(self):
        """
        return: int
        """
        return self.get('baro?')

    def get_imu_acceleration(self):
        """
        return: list(int)
        """
        return self.get('acceleration?', split=True)

    def get_tof_height(self):
        """
        return: int, [10, 400]; 6553: out of bounds
        """
        return self.get('tof?')
