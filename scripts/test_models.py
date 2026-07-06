from google import genai

# Initialize the client with your key
client = genai.Client(api_key="GOOGLE_API_KEY")

# Fetch and print models
models = client.models.list()
for model in models:
    print(model.name)
