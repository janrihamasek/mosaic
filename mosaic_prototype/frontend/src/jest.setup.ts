import { TextDecoder, TextEncoder } from "util";
import "./setupTests";

if (typeof global.TextEncoder === "undefined") {
  (global as unknown as { TextEncoder: typeof TextEncoder }).TextEncoder = TextEncoder;
}

if (typeof global.TextDecoder === "undefined") {
  (global as unknown as { TextDecoder: typeof TextDecoder }).TextDecoder = TextDecoder as unknown as typeof global.TextDecoder;
}
