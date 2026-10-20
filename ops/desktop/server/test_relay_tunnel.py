"""The bore relay client forwards only to loopback and refuses a reassigned port."""
import json
import socket
import threading
import uuid

import pytest

import relay_tunnel


def listener():
    server = socket.create_server(('127.0.0.1', 0))
    server.settimeout(5)
    return server, ('127.0.0.1', server.getsockname()[1])


def read_frame(sock):
    data = b''
    while not data.endswith(b'\0'):
        data += sock.recv(1)
    return json.loads(data[:-1])


def echo_server():
    server, address = listener()

    def serve():
        conn, _ = server.accept()
        with conn:
            while data := conn.recv(4096):
                conn.sendall(data)
    threading.Thread(target=serve, daemon=True).start()
    return address


def test_connection_round_trips_bytes_to_the_loopback_target(monkeypatch):
    relay, relay_address = listener()
    echo_address = echo_server()
    dialed, real_connect = [], socket.create_connection

    def recording_connect(address, *args, **kwargs):
        dialed.append(address)
        return real_connect(address, *args, **kwargs)
    monkeypatch.setattr(relay_tunnel.socket, 'create_connection', recording_connect)
    failures = []

    def run():
        try:
            relay_tunnel.session(relay_address, 45678, echo_address[1])
        except Exception as exc:
            failures.append(exc)
    threading.Thread(target=run, daemon=True).start()
    control, _ = relay.accept()
    assert read_frame(control) == {'Hello': 45678}
    conn_id = str(uuid.uuid4())
    # Several frames in one segment: the client must keep bytes read past each NUL.
    control.sendall(b'{"Hello":45678}\0"Heartbeat"\0"Heartbeat"\0' + json.dumps({'Connection': conn_id}).encode() + b'\0')
    data, _ = relay.accept()
    assert read_frame(data) == {'Accept': conn_id}
    data.sendall(b'ping over the tunnel')
    received = b''
    while len(received) < 20:
        received += data.recv(64)
    assert received == b'ping over the tunnel'
    data.close()
    control.close()
    assert dialed == [relay_address, relay_address, ('127.0.0.1', echo_address[1])]
    relay.close()


@pytest.mark.parametrize('reply', [b'{"Hello":45679}\0', b'{"Hello":0}\0', b'{"Error":"port already in use"}\0',
                                   b'{"Challenge":"' + str(uuid.uuid4()).encode() + b'"}\0'])
def test_relay_that_does_not_grant_the_requested_port_is_refused(reply):
    relay, relay_address = listener()

    def fake():
        conn, _ = relay.accept()
        with conn:
            read_frame(conn)
            conn.sendall(reply)
    threading.Thread(target=fake, daemon=True).start()
    with pytest.raises(RuntimeError, match='relay refused port 45678'):
        relay_tunnel.session(relay_address, 45678)
    relay.close()


def test_oversized_frame_is_refused():
    left, right = socket.socketpair()
    with left, right:
        right.sendall(b'"' + b'x' * 300)
        with pytest.raises(ValueError, match='too long'):
            relay_tunnel.Frames(left).recv()


def test_local_target_cannot_be_configured_off_loopback():
    assert relay_tunnel.LOOPBACK == '127.0.0.1'
    for flag in ('--local-host', '--local', '--to', '--host'):
        with pytest.raises(SystemExit):
            relay_tunnel.main(['--port', '45678', '--log', 'unused.log', flag, '10.0.0.5'])
