from google import genai

client = genai.Client(api_key="")

# interaction = client.interactions.create(
#     model="gemini-embedding-001",
#     input="whatss today world cup schedule?",
# )
# print(interaction.output_text)
result = client.models.embed_content(
        model="gemini-embedding-2",
        contents="What is the meaning of life?"
)
print(result.embeddings)

