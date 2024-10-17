import gc
import os
from io import BytesIO

import torch
# from diffusers import StableDiffusionPipeline
from diffusers import DiffusionPipeline, StableDiffusionPipeline, EulerDiscreteScheduler, AutoPipelineForText2Image
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

load_dotenv()
app = FastAPI()

active_engine = os.getenv("ACTIVE_ENGINE", "RUNWAY_ML")

USE_RUNWAY_ML = True
USE_SDXL_TURBO = False
USE_SDXL_BASE = False

# model_id = "stabilityai/stable-diffusion-2-1-base"

if active_engine == "RUNWAY_ML":
    model_id = "runwayml/stable-diffusion-v1-5"
    scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=scheduler, torch_dtype=torch.float16).to("cuda")

elif active_engine == "SDXL_TURBO":
    pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16,
                                                     variant="fp16").to("cuda")

else:
    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, use_safetensors=True,
                                             variant="fp16").to("cuda")


# pipe.enable_model_cpu_offload()  # save some VRAM by offloading the model to CPU. Remove this if you have enough GPU power


@app.post("/generate")
async def generate_image(prompt: str, size: int = 1024):
    try:
        gc.collect()
        torch.cuda.empty_cache()
        image = pipe(prompt, width=size, height=size).images[0]
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        buffered.seek(0)

        return StreamingResponse(buffered, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
