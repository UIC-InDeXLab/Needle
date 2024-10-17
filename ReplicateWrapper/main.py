import replicate
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI()


@app.post("/generate")
async def generate_images(prompt: str, k : int = 1):
    input_params = {
        "prompt": prompt,
        "num_outputs": k,
        "output_format": "png",
        "go_fast": False
    }

    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input=input_params
    )
    print(output)

    return {"urls": output}
