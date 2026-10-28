import { BeeClient } from "@heossihq/bee";

// biome-ignore lint/suspicious/noUndeclaredEnvVars: runs in the customer's environment, not this repo's Turbo graph runs in the customer's environment, not this repo's Turbo graph
const bee = new BeeClient({ apiKey: process.env.BEE_API_KEY! });
const stream = await bee.chat.completions.create({
  model: "bee-cell",
  messages: [{ role: "user", content: "Write a short haiku about bees." }],
  stream: true,
});

for await (const chunk of stream) {
  const content = chunk.choices[0]?.delta?.content;
  if (content) process.stdout.write(content);
}
process.stdout.write("\n");
