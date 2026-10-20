"""Forward a fixed public port on an open bore relay to 127.0.0.1 only.

bore v0.6.0 protocol (github.com/ekzhang/bore src/shared.rs, src/client.rs). The relay
sees only TLS ciphertext; the server's pinned key authenticates it to clients."""
import argparse
import json
import logging
import socket
import threading
import time
import uuid

CONTROL_PORT = 7835  # shared.rs CONTROL_PORT
MAX_FRAME = 256      # shared.rs MAX_FRAME_LENGTH
TIMEOUT = 3          # shared.rs NETWORK_TIMEOUT, seconds
IDLE = 30            # the relay heartbeats every <=0.5 s; this much silence is a dead link
RETRY = 10
LOOPBACK = '127.0.0.1'  # the only local host this tunnel ever dials
LOCAL_PORT = 38443
# The publisher serves 32 requests at once and queues the rest. A Connection beyond this many active
# forwards waits up to SLOT_WAIT for one to finish; the relay keeps an unaccepted connection for 10 s
# (server.rs). Waiting in the control loop keeps the thread count bounded, but frames behind it queue in
# the socket (FIFO) and their waits add up: a Connection queued behind others that each waited can reach
# its own wait (and the 3 s dial) after the relay has already dropped it. Under sustained overload some
# connections are skipped or fail; each skip is logged.
SLOTS = threading.BoundedSemaphore(32)
SLOT_WAIT = 6


class Frames:
    def __init__(self, sock):
        self.sock, self.buf = sock, b''

    def send(self, msg):
        self.sock.sendall(json.dumps(msg, separators=(',', ':')).encode() + b'\0')

    def recv(self):
        while b'\0' not in self.buf:
            if len(self.buf) > MAX_FRAME:
                raise ValueError('relay frame too long')
            chunk = self.sock.recv(4096)
            if not chunk:
                raise EOFError('relay closed the control channel')
            self.buf += chunk
        frame, _, self.buf = self.buf.partition(b'\0')
        if len(frame) > MAX_FRAME:
            raise ValueError('relay frame too long')
        msg = json.loads(frame)
        if msg == 'Heartbeat':
            return 'Heartbeat', None
        if isinstance(msg, dict) and len(msg) == 1:
            return next(iter(msg.items()))
        raise ValueError('unexpected relay message')


def close(*socks):
    for sock in socks:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()


def pump(src, dst):
    try:
        while data := src.recv(65536):
            dst.sendall(data)
        dst.shutdown(socket.SHUT_WR)  # pass this side's FIN on; the other direction may still be sending
    except OSError:
        close(src, dst)  # a reset or failed send ends both directions


def forward(relay, conn_id, local_port, slots):
    """Runs holding one slot of `slots`, released on return."""
    try:
        try:
            remote = socket.create_connection(relay, timeout=TIMEOUT)
        except OSError as exc:
            return logging.warning('relay data connection failed: %s', exc)
        try:
            Frames(remote).send({'Accept': conn_id})
            local = socket.create_connection((LOOPBACK, local_port), timeout=TIMEOUT)
        except OSError as exc:
            close(remote)
            return logging.warning('forward %s failed: %s', conn_id, exc)
        # Nothing was read from `remote`, so no bytes past the Accept frame are buffered here.
        remote.settimeout(None)
        local.settimeout(None)
        inbound = threading.Thread(target=pump, args=(remote, local), daemon=True)
        inbound.start()
        pump(local, remote)  # ends when the publisher closes, which its own deadlines bound
        inbound.join(TIMEOUT)  # the response is out; the client gets a moment to finish its side
        close(remote, local)
    finally:
        slots.release()


def session(relay, port, local_port=LOCAL_PORT):
    with socket.create_connection(relay, timeout=TIMEOUT) as control:
        frames = Frames(control)
        frames.send({'Hello': port})
        kind, value = frames.recv()
        if kind != 'Hello' or type(value) is not int or value != port:
            raise RuntimeError(f'relay refused port {port}: {kind} {value!r}')
        logging.info('connected: %s:%d -> %s:%d', relay[0], port, LOOPBACK, local_port)
        control.settimeout(IDLE)
        slots = SLOTS  # one semaphore for this session's acquires and releases
        while True:
            kind, value = frames.recv()
            if kind == 'Connection':
                conn_id = str(uuid.UUID(value))  # canonical form; anything else drops the session
                if not slots.acquire(timeout=SLOT_WAIT):
                    logging.warning('forward %s skipped: no slot freed within %s s', conn_id, SLOT_WAIT)
                    continue
                try:
                    threading.Thread(target=forward, args=(relay, conn_id, local_port, slots), daemon=True).start()
                except RuntimeError:  # the thread never ran, so forward() will not release its slot
                    slots.release()
                    raise
            elif kind == 'Error':
                raise RuntimeError(f'relay error: {value}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--relay', default='bore.pub')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--log', required=True)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error('--port must be 1024-65535')
    logging.basicConfig(filename=args.log, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    while True:
        try:
            session((args.relay, CONTROL_PORT), args.port)
        except Exception as exc:  # any failure: log one line, back off, reconnect
            logging.warning('control channel down: %s: %s', type(exc).__name__, exc)
        time.sleep(RETRY)


if __name__ == '__main__':
    main()
