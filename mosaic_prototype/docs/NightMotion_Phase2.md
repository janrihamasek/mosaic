# NightMotion Streaming Proxy – Phase 2

## Endpoint Summary

- **Path:** `/api/stream-proxy`
- **Method:** `GET`
- **Description:** Proxies an RTSP camera feed via FFmpeg and streams MJPEG frames to the client as a multipart response.

## Query Parameters

- `url` (required): RTSP endpoint for the camera, e.g. `rtsp://10.0.1.39:554/stream1`.
- `username` (optional): Username for RTSP authentication.
- `password` (optional): Password for RTSP authentication.

Credentials are embedded into the proxied RTSP URL. When omitted, the proxy will attempt to access the stream anonymously.

## Authentication

The endpoint is protected and requires both:

- A valid Bearer JWT in the `Authorization` header.
- Matching CSRF token in the `X-CSRF-Token` header (for non-GET methods this is mandatory across the API; GET is covered by JWT alone).

## Example Request

```bash
curl -X GET "https://localhost:5000/api/stream-proxy?url=rtsp://10.0.1.39:554/stream1&username=admin&password=pass" \
     -H "Authorization: Bearer <JWT>" \
     -H "X-CSRF-Token: <CSRF>"
```

The response (`Content-Type: multipart/x-mixed-replace; boundary=frame`) yields a continuous sequence of JPEG frames suitable for `<video>` or `<img>` elements that understand MJPEG streams.

## Error Codes

| Status | Code                | Meaning                               |
| ------ | ------------------- | ------------------------------------- |
| 401    | `unauthorized`      | Missing/invalid JWT or camera rejects provided credentials. |
| 429    | `too_many_requests` | Per-user rate limit exceeded (2 calls/minute). |
| 500    | `internal_error`    | FFmpeg startup failure or stream disruption. |

## Operational Notes

- **FFmpeg Dependency:** The backend invokes `ffmpeg` from the system path. Ensure FFmpeg is installed on the deployment host and update PATH if necessary.
- **Performance & Limits:** Each request spawns an FFmpeg process. Concurrent streams are limited by CPU/network capacity; production rollouts should monitor load and consider pooling if usage grows.
- **Disconnect Handling:** When the client closes the connection, the proxy terminates the FFmpeg process to avoid orphaned workloads.
