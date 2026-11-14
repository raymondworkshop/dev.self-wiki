"""CLI asks the running Trace service instead of loading weights."""

from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from cli_cmd_trace import TraceRemoteError, _use_local_trace, fetch_trace


class _Args:
    def __init__(self, force_index: bool = False) -> None:
        self.force_index = force_index


class FetchTraceTests(unittest.TestCase):
    def test_local_flag_skips_server(self) -> None:
        with mock.patch.dict("os.environ", {"TRACE_LOCAL": "1"}):
            self.assertTrue(_use_local_trace(_Args()))
        self.assertTrue(_use_local_trace(_Args(force_index=True)))

    def test_down_server_returns_none(self) -> None:
        with mock.patch("cli_cmd_trace.socket.create_connection", side_effect=ConnectionRefusedError):
            self.assertIsNone(fetch_trace("q", scope=None, debug=False, save=False))

    def test_running_server_returns_json(self) -> None:
        payload = {"answer": "### note\n\n> line\n", "output_path": None}
        response = mock.Mock()
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        with mock.patch("cli_cmd_trace.socket.create_connection", return_value=mock.MagicMock()):
            with mock.patch("cli_cmd_trace.urllib.request.urlopen", return_value=response) as opened:
                got = fetch_trace("values", scope="a-free-man", debug=False, save=False)
        self.assertEqual(got["answer"], payload["answer"])
        sent = json.loads(opened.call_args.args[0].data.decode())
        self.assertEqual(sent["q"], "values")
        self.assertEqual(sent["scope"], "a-free-man")
        self.assertFalse(sent["save"])

    def test_http_error_does_not_look_like_a_down_server(self) -> None:
        err = urllib.error.HTTPError(
            url="http://127.0.0.1:8791/ask",
            code=500,
            msg="err",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"boom"}'),
        )
        with mock.patch("cli_cmd_trace.socket.create_connection", return_value=mock.MagicMock()):
            with mock.patch("cli_cmd_trace.urllib.request.urlopen", side_effect=err):
                with self.assertRaises(TraceRemoteError):
                    fetch_trace("q", scope=None, debug=False, save=True)


if __name__ == "__main__":
    unittest.main()
