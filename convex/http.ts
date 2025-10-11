import { httpAction } from "./_generated/server";
import { anyApi } from "convex/server";
import { httpRouter } from "convex/server";

export const ingestNdjson = httpAction(async (ctx, request) => {
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  const contentType = request.headers.get("content-type") || "";
  if (
    !contentType.includes("application/x-ndjson") &&
    !contentType.includes("application/jsonl")
  ) {
    return new Response("Unsupported Media Type", { status: 415 });
  }

  const text = await request.text();
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);

  let inserted = 0;
  let skipped = 0;
  for (const line of lines) {
    try {
      const obj = JSON.parse(line);
      // Route by object shape.
      // If it looks like an alias object (from alias batch), upsert aliases.
      if (
        obj &&
        typeof obj === "object" &&
        obj.title &&
        typeof obj.title === "string" &&
        Array.isArray(obj.aliases)
      ) {
        const res = await ctx.runMutation(anyApi.ingest.upsertAliases, {
          title: obj.title,
          aliases: obj.aliases,
          notes: obj.notes ?? undefined,
        });
        if (res && (res as any).upserted > 0) inserted += 1;
        else skipped += 1;
        continue;
      }
      // Otherwise treat as a full game object
      const res = await ctx.runMutation(anyApi.ingest.addGame, obj);
      if (res && (res as any).inserted) inserted += 1;
      else skipped += 1;
    } catch (e) {
      // Continue on error
    }
  }

  return new Response(JSON.stringify({ inserted, skipped }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
});

const http = httpRouter();
http.route({ path: "/ingestNdjson", method: "POST", handler: ingestNdjson });
export default http;
