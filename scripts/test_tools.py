from google import genai

client = genai.Client(api_key="")

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="whatss today world cup schedule?",
    tools=[{"type": "google_search"}]
)

print(interaction.output_text)