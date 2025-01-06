FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV DEBIAN_FRONTEND=noninteractive
ENV TORCH_HOME=/root/.cache/torch
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=$HF_HOME


WORKDIR /app

COPY requirements.txt /app/


RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]
