import { BeeClient } from "@heossihq/bee";

// biome-ignore lint/suspicious/noUndeclaredEnvVars: runs in the customer's environment, not this repo's Turbo graph runs in the customer's environment, not this repo's Turbo graph
const bee = new BeeClient({ apiKey: process.env.BEE_API_KEY! });
const result = await bee.chat.completions.create({
  model: "bee-cell",
  messages: [{ role: "user", content: "What is Bee?" }],
});

console.log(result.choices[0].message.content);
