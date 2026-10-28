import { BeeClient } from "@heossihq/bee";

// biome-ignore lint/suspicious/noUndeclaredEnvVars: runs in the customer's environment, not this repo's Turbo graph runs in the customer's environment, not this repo's Turbo graph
const bee = new BeeClient({ apiKey: process.env.BEE_API_KEY! });
const result = await bee.chat.completions.create({
  model: "bee-cell",
  messages: [
    {
      role: "user",
      content: [
        { type: "text", text: "Describe this image in one sentence." },
        {
          type: "image_url",
          image_url: {
            url: "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Honey_bee_%28Apis_mellifera%29.jpg/640px-Honey_bee_%28Apis_mellifera%29.jpg",
          },
        },
      ],
    },
  ],
  max_tokens: 120,
});

console.log(result.choices[0].message.content);
