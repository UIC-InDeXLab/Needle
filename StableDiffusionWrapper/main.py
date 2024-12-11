import gc
import os
from io import BytesIO

import torch
# from diffusers import StableDiffusionPipeline
from diffusers import DiffusionPipeline, StableDiffusionPipeline, AutoPipelineForText2Image
from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

load_dotenv()
app = FastAPI()

active_engine = os.getenv("ACTIVE_ENGINE", "RUNWAY_ML")

kwargs = {}


# model_id = "stabilityai/stable-diffusion-2-1-base"

if active_engine == "RUNWAY_ML":
    model_id = "runwayml/stable-diffusion-v1-5"
    scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=scheduler, torch_dtype=torch.float16).to("cuda")

elif active_engine == "SDXL_TURBO":
    pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16,
                                                     variant="fp16").to("cuda")

elif active_engine == "SDXL_LIGHTNING":
    base = "stabilityai/stable-diffusion-xl-base-1.0"
    repo = "ByteDance/SDXL-Lightning"
    ckpt = "sdxl_lightning_2step_unet.safetensors" # Use the correct ckpt for your step setting!

    # Load model.
    unet = UNet2DConditionModel.from_config(base, subfolder="unet").to("cuda", torch.float16)
    unet.load_state_dict(load_file(hf_hub_download(repo, ckpt), device="cuda"))
    pipe = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, torch_dtype=torch.float16, variant="fp16").to("cuda")

    # Ensure sampler uses "trailing" timesteps.
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")

    kwargs["num_inference_steps"] = 2
    kwargs["guidance_scale"] = 0

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
        image = pipe(prompt, width=size, height=size, **kwargs).images[0]
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        buffered.seek(0)

        return StreamingResponse(buffered, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
