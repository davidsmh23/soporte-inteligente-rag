function parseEventBlock(block) {
  const lines = block
    .split("\n")
    .map((line) => line.replace(/\r$/, ""));

  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (!dataLines.length) {
    return null;
  }

  const payload = dataLines.join("\n").trim();
  if (!payload) {
    return null;
  }

  return JSON.parse(payload);
}

export async function streamJsonEvents(response, onEvent) {
  if (!response.body) {
    throw new Error("La respuesta de streaming no incluye cuerpo.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer = buffer.replace(/\r\n/g, "\n");

    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const rawEvent = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);

      if (rawEvent) {
        const parsed = parseEventBlock(rawEvent);
        if (parsed) {
          onEvent(parsed);
        }
      }

      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }

  const trailing = buffer.trim();
  if (trailing) {
    const parsed = parseEventBlock(trailing);
    if (parsed) {
      onEvent(parsed);
    }
  }
}
