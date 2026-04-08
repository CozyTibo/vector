/** Enforces a minimum wait so "Vector is typing" feels human, even when the API is fast. */
export function minTypingDelay(minMs = 400, maxMs = 900): Promise<void> {
  const ms = minMs + Math.random() * (maxMs - minMs);
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
