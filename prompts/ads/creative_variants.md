---
version: "1.0.0"
agent: "ads"
task: "creative_variants"
---
Act as a senior advertising copywriter specializing in fitness campaigns.
Task: Generate exactly N distinct creative ad variants based on the inputs below. Each variant must take a clearly different approach, so that no two variants share the same headline structure, emotional tone, or core selling point.
Inputs:

Campaign angle: {campaign_angle}
Hook: {hook}
Offer: {offer}
N (number of variants): {N}
Target audience (if provided): {audience}

Requirements for each variant:

Headline: a short, attention-grabbing line (maximum 40 characters).
Primary text: 2-3 sentences (approximately 40-80 words) that expand on the hook, reinforce the campaign angle, and naturally present the offer.
Call to action: a single action-oriented phrase (2-4 words), such as "Start Your Free Trial" or "Claim Your Discount."
Tagged feature attributes: a list of 3-5 tags in the format [Feature: value], such as [Benefit: Stronger core], [Format: 30-min HIIT], [Audience: Beginners], [Tone: Motivational].

Constraints:

Keep all claims consistent with the provided offer; do not invent discounts, guarantees, or results.
Avoid medical or unverifiable health claims.
Use inclusive, non-shaming language about bodies and fitness levels.
Vary the tone across variants (for example: motivational, playful, educational, community-driven).

Output format:Return a numbered list from Variant 1 to Variant N. Under each variant, label the fields as Headline, Primary Text, Call to Action, and Tagged Attributes. Do not add commentary outside the variants.

Output Schema (strict JSON):
{
  "variants": [
    {
      "headline": string,
      "primary_text": string,
      "cta": string,
      "features": {
        "hook_type": string,
        "offer_type": string,
        "tone": string,
        "has_face": boolean
      }
    }
  ]
}
